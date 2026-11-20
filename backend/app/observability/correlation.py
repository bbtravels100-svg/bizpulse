import re
import uuid
from contextvars import ContextVar
from typing import Optional

# Regular expression validating incoming correlation IDs: 8-64 chars, alphanumeric, hyphens, underscores
CORRELATION_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_\-]{8,64}$")

# Thread-safe and async-safe context variable for request correlation
correlation_id_ctx: ContextVar[str] = ContextVar("correlation_id", default="corr-init")


def generate_correlation_id() -> str:
    """Generate a unique, cryptographically random request correlation ID."""
    return f"corr-{uuid.uuid4().hex[:16]}"


def validate_correlation_id(raw_id: Optional[str]) -> Optional[str]:
    """
    Validate an incoming X-Correlation-ID header value.
    Rejects malformed strings, command injections, or oversized values.
    Returns cleaned string if valid, None if invalid.
    """
    if not raw_id or not isinstance(raw_id, str):
        return None
    cleaned = raw_id.strip()
    if CORRELATION_ID_PATTERN.match(cleaned):
        return cleaned
    return None


def get_correlation_id() -> str:
    """Retrieve the correlation ID of the current request execution context."""
    return correlation_id_ctx.get()


def set_correlation_id(cid: str) -> None:
    """Set the correlation ID for the current request execution context."""
    correlation_id_ctx.set(cid)
