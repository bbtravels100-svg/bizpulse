import re
import json
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any

from .correlation import get_correlation_id

# Sensitive data redaction regex patterns
_REDACTION_PATTERNS = [
    (re.compile(r"password['\"]?\s*[:=]\s*['\"]?[^'\",\s]+", re.IGNORECASE), "password=[REDACTED]"),
    (re.compile(r"bearer\s+[a-zA-Z0-9_\-\.]+", re.IGNORECASE), "Bearer [REDACTED]"),
    (re.compile(r"(api[_-]?key|secret|token|provisioning[_-]?key)['\"]?\s*[:=]\s*['\"]?[^'\",\s]+", re.IGNORECASE), r"\1=[REDACTED]"),
    (re.compile(r"ey[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_-]{10,}", re.IGNORECASE), "[REDACTED_JWT]"),
    (re.compile(r"access_token=[^;\s]+", re.IGNORECASE), "access_token=[REDACTED]"),
]


def redact_sensitive_string(text: str) -> str:
    """Sanitize strings by redacting secrets, JWTs, passwords, and tokens."""
    if not text:
        return ""
    sanitized = str(text)
    for pattern, replacement in _REDACTION_PATTERNS:
        sanitized = pattern.sub(replacement, sanitized)
    return sanitized


class JsonLogFormatter(logging.Formatter):
    """
    Structured JSON log formatter for production observability.
    Emits single-line JSON records containing ISO 8601 timestamps,
    log levels, logger names, request correlation IDs, and sanitized messages.
    """

    def format(self, record: logging.LogRecord) -> str:
        try:
            # 1. Base structured fields
            payload: Dict[str, Any] = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "level": record.levelname,
                "logger": record.name,
                "message": redact_sensitive_string(record.getMessage()),
                "correlation_id": getattr(record, "correlation_id", None) or get_correlation_id(),
            }

            # 2. Add optional HTTP request context if present
            if hasattr(record, "method"):
                payload["method"] = getattr(record, "method")
            if hasattr(record, "endpoint"):
                payload["endpoint"] = getattr(record, "endpoint")
            if hasattr(record, "status_code"):
                payload["status_code"] = getattr(record, "status_code")
            if hasattr(record, "duration_ms"):
                payload["duration_ms"] = getattr(record, "duration_ms")
            if hasattr(record, "user_id"):
                payload["user_id"] = getattr(record, "user_id")

            # 3. Add server-side exception traceback if present
            if record.exc_info:
                payload["exception"] = redact_sensitive_string(self.formatException(record.exc_info))

            return json.dumps(payload, default=str)
        except Exception as e:
            # Fallback to plain string if JSON serialization fails
            return f"{record.levelname}: {record.getMessage()} (JSON logging fallback: {e})"


def configure_logging(level_name: str = "INFO", enable_json: bool = True) -> None:
    """Configure application logging with structured JSON formatting."""
    log_level = getattr(logging, level_name.upper(), logging.INFO)
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Avoid duplicate handlers
    if not root_logger.handlers:
        handler = logging.StreamHandler()
        if enable_json:
            handler.setFormatter(JsonLogFormatter())
        else:
            handler.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)s %(name)s: %(message)s"))
        root_logger.addHandler(handler)
    else:
        for handler in root_logger.handlers:
            if enable_json:
                handler.setFormatter(JsonLogFormatter())
