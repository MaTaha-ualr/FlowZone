"""Tests for rate limiting and concurrency control."""
import pytest
import asyncio
from app.middleware.rate_limit import RateLimiter, ConcurrencyGuard


class TestRateLimiter:
    def test_allows_first(self):
        lim = RateLimiter(max_requests=5, window_seconds=60)
        assert lim.is_allowed("u1") is True

    def test_allows_up_to_limit(self):
        lim = RateLimiter(max_requests=3, window_seconds=60)
        assert all(lim.is_allowed("u1") for _ in range(3))

    def test_blocks_after_limit(self):
        lim = RateLimiter(max_requests=2, window_seconds=60)
        lim.is_allowed("u1"); lim.is_allowed("u1")
        assert lim.is_allowed("u1") is False

    def test_users_independent(self):
        lim = RateLimiter(max_requests=1, window_seconds=60)
        assert lim.is_allowed("u1") is True
        assert lim.is_allowed("u2") is True
        assert lim.is_allowed("u1") is False

    def test_remaining(self):
        lim = RateLimiter(max_requests=5, window_seconds=60)
        assert lim.remaining("u1") == 5
        lim.is_allowed("u1")
        assert lim.remaining("u1") == 4


class TestConcurrencyGuard:
    @pytest.mark.asyncio
    async def test_allows_under_limit(self):
        g = ConcurrencyGuard(max_concurrent=3)
        assert await g.check_in("u1") is True
        assert await g.check_in("u2") is True
        assert await g.check_in("u3") is True

    @pytest.mark.asyncio
    async def test_blocks_at_limit(self):
        g = ConcurrencyGuard(max_concurrent=2)
        await g.check_in("u1"); await g.check_in("u2")
        assert await g.check_in("u3") is False

    @pytest.mark.asyncio
    async def test_same_user_no_double_count(self):
        g = ConcurrencyGuard(max_concurrent=2)
        await g.check_in("u1"); await g.check_in("u1")
        assert await g.check_in("u2") is True

    @pytest.mark.asyncio
    async def test_release_frees_slot(self):
        g = ConcurrencyGuard(max_concurrent=1)
        await g.check_in("u1")
        assert await g.check_in("u2") is False
        await g.release("u1")
        assert await g.check_in("u2") is True

    @pytest.mark.asyncio
    async def test_active_count(self):
        g = ConcurrencyGuard(max_concurrent=5)
        await g.check_in("u1"); await g.check_in("u2")
        assert g.active_count == 2

    @pytest.mark.asyncio
    async def test_expired_cleaned(self):
        g = ConcurrencyGuard(max_concurrent=1)
        g.ACTIVITY_TIMEOUT = 0
        await g.check_in("u1")
        await asyncio.sleep(0.01)
        assert await g.check_in("u2") is True
