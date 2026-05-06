"""
FlowZone Structured Logging
============================
JSON-formatted logs for production observability (Railway, Datadog, etc.).
"""

import logging
import sys
import json
from datetime import datetime, timezone
from typing import Any

class JSONFormatter(logging.Formatter):
    """Emit log records as single-line JSON."""

    def format(self, record: logging.LogRecord) -> str:
        log_obj = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        # Include extra fields if present
        if hasattr(record, "request_id"):
            log_obj["request_id"] = record.request_id
        if hasattr(record, "user_id"):
            log_obj["user_id"] = record.user_id
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_obj, default=str)

def setup_logging(level: int = logging.INFO):
    """Configure root logger for structured output."""
    root = logging.getLogger()
    root.setLevel(level)

    # Remove existing handlers to avoid duplicates on reload
    for handler in root.handlers[:]:
        root.removeHandler(handler)

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter())
    root.addHandler(handler)

    # Reduce noise from third-party libs
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("chromadb").setLevel(logging.WARNING)
