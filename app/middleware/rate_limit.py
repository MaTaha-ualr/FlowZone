"""
Middleware: Rate Limiting & Concurrency Control
=================================================
Two critical middleware layers:

1. Concurrency Guard — ensures no more than MAX_CONCURRENT_USERS
   have active sessions at once (per our 5-user constraint)

2. Rate Limiter — per-user message rate limiting to prevent
   API credit burn from spamming

Architecture Note:
    For the MVP, these use in-memory tracking (no Redis needed).
    At 30 users / 5 concurrent, this is fine. For AWS production,
    swap to Redis-backed counters.
"""

import time
import asyncio
import threading
from collections import defaultdict
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.config import settings


class ConcurrencyGuard:
    """
    Tracks active sessions. Rejects new sessions when limit is reached.
    An "active session" = a user who has sent a message in the last 5 minutes.
    """

    def __init__(self, max_concurrent: int = 5):
        self.max_concurrent = max_concurrent
        self._active_users: dict[str, float] = {}  # user_id -> last_active_timestamp
        self._lock = asyncio.Lock()
        self.ACTIVITY_TIMEOUT = 300  # 5 minutes of inactivity = slot freed

    async def check_in(self, user_id: str) -> bool:
        """
        Register user activity. Returns True if allowed, False if at capacity.
        """
        async with self._lock:
            now = time.time()
            # Clean up expired slots
            expired = [
                uid for uid, ts in self._active_users.items()
                if now - ts > self.ACTIVITY_TIMEOUT
            ]
            for uid in expired:
                del self._active_users[uid]

            # If user already active, just update timestamp
            if user_id in self._active_users:
                self._active_users[user_id] = now
                return True

            # Check capacity
            if len(self._active_users) >= self.max_concurrent:
                return False

            # Register new active user
            self._active_users[user_id] = now
            return True

    async def release(self, user_id: str):
        """Explicitly release a user's slot (on session end)."""
        async with self._lock:
            self._active_users.pop(user_id, None)

    @property
    def active_count(self) -> int:
        now = time.time()
        return sum(
            1 for ts in self._active_users.values()
            if now - ts <= self.ACTIVITY_TIMEOUT
        )


class RateLimiter:
    """
    Per-user rate limiting using a sliding window.
    Prevents a single user from burning through API credits.
    """

    def __init__(self, max_requests: int = 10, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: dict[str, list[float]] = defaultdict(list)
        self._lock = threading.RLock()

    def is_allowed(self, user_id: str) -> bool:
        """Check if user is within rate limit. Cleans old entries."""
        with self._lock:
            now = time.time()
            window_start = now - self.window_seconds

            # Clean old entries
            self._requests[user_id] = [
                ts for ts in self._requests[user_id] if ts > window_start
            ]

            # Check limit
            if len(self._requests[user_id]) >= self.max_requests:
                return False

            # Record this request
            self._requests[user_id].append(now)
            return True

    def remaining(self, user_id: str) -> int:
        """How many requests the user has left in the current window."""
        with self._lock:
            now = time.time()
            window_start = now - self.window_seconds
            recent = [ts for ts in self._requests[user_id] if ts > window_start]
            return max(0, self.max_requests - len(recent))


# ---- Singleton instances ----
concurrency_guard = ConcurrencyGuard(max_concurrent=settings.max_concurrent_users)
rate_limiter = RateLimiter(
    max_requests=settings.user_rate_limit_per_minute,
    window_seconds=60
)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    FastAPI middleware that applies rate limiting to chat endpoints.
    Non-chat endpoints (health, admin) are not rate limited.
    """

    async def dispatch(self, request: Request, call_next):
        # Only rate-limit chat-related endpoints
        if "/chat" in request.url.path or "/voice" in request.url.path:
            # Extract user_id from path or header
            user_id = request.headers.get("X-User-ID", "anonymous")
            if not rate_limiter.is_allowed(user_id):
                raise HTTPException(
                    status_code=429,
                    detail={
                        "error": "Rate limit exceeded",
                        "message": "You're sending messages too fast. Take a breath.",
                        "retry_after_seconds": 60,
                    }
                )
        response = await call_next(request)
        return response
