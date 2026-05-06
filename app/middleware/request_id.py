"""
Request ID Middleware
======================
Injects a unique X-Request-ID into every request for distributed tracing.
Also attaches request_id to the logging context.
"""

import uuid
import contextvars
from typing import Optional

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar(
    "request_id",
    default="unknown",
)

class RequestIDMiddleware(BaseHTTPMiddleware):
    """Add X-Request-ID header to every request/response."""

    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        token = request_id_var.set(request_id)
        request.state.request_id = request_id

        try:
            response = await call_next(request)
            response.headers["X-Request-ID"] = request_id
            return response
        finally:
            request_id_var.reset(token)

def get_request_id(request: Optional[Request] = None) -> str:
    """Helper to get request_id in routes."""
    if request is not None:
        return getattr(request.state, "request_id", request_id_var.get())
    return request_id_var.get()
