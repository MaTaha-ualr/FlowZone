"""
Request ID Middleware
======================
Injects a unique X-Request-ID into every request for distributed tracing.
Also attaches request_id to the logging context.
"""

import uuid
import logging
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

class RequestIDMiddleware(BaseHTTPMiddleware):
    """Add X-Request-ID header to every request/response."""

    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.state.request_id = request_id

        # Attach to logging context for this request
        old_factory = logging.getLogRecordFactory()
        def record_factory(*args, **kwargs):
            record = old_factory(*args, **kwargs)
            record.request_id = request_id
            return record
        logging.setLogRecordFactory(record_factory)

        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response

def get_request_id(request: Request) -> str:
    """Helper to get request_id in routes."""
    return getattr(request.state, "request_id", "unknown")
