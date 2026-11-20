import os
import time
import threading
from typing import Dict, List, Tuple, Optional, Callable
from fastapi import Request, HTTPException, status

from .audit import get_client_ip, record_security_event, SecurityEventType


class SlidingWindowRateLimiter:
    """
    Thread-safe in-memory sliding window rate limiter.
    Stores timestamps of requests per key (IP + endpoint).
    """

    def __init__(self):
        self._lock = threading.Lock()
        # Map of key -> List[float (epoch timestamps)]
        self._requests: Dict[str, List[float]] = {}

    def _parse_limit(self, limit_expr: str) -> Tuple[int, int]:
        """
        Parse expressions like '5/minute', '10/second', '100/hour', '1000/day'.
        Returns (max_requests, window_seconds).
        """
        expr = limit_expr.strip().lower()
        parts = expr.split("/")
        if len(parts) != 2:
            return 60, 60

        count = int(parts[0].strip())
        unit = parts[1].strip()

        if unit in ("s", "sec", "second", "seconds"):
            window = 1
        elif unit in ("m", "min", "minute", "minutes"):
            window = 60
        elif unit in ("h", "hr", "hour", "hours"):
            window = 3600
        elif unit in ("d", "day", "days"):
            window = 86400
        else:
            window = 60

        return count, window

    def is_allowed(self, key: str, limit_expr: str) -> Tuple[bool, int]:
        """
        Check if a request under `key` is allowed by `limit_expr`.
        Returns (allowed: bool, retry_after_seconds: int).
        """
        max_requests, window_seconds = self._parse_limit(limit_expr)
        now = time.time()
        window_start = now - window_seconds

        with self._lock:
            history = self._requests.get(key, [])
            # Evict timestamps outside current sliding window
            history = [ts for ts in history if ts > window_start]

            if len(history) >= max_requests:
                # Compute seconds until oldest request in window expires
                oldest = history[0]
                retry_after = max(1, int(oldest + window_seconds - now))
                self._requests[key] = history
                return False, retry_after

            history.append(now)
            self._requests[key] = history
            return True, 0

    def reset(self):
        """Reset rate limiter state (useful for tests)."""
        with self._lock:
            self._requests.clear()


# Default singleton instance
default_rate_limiter = SlidingWindowRateLimiter()


def rate_limit(
    limit_default: str = "60/minute",
    env_var_name: Optional[str] = None,
    key_prefix: Optional[str] = None,
) -> Callable:
    """
    FastAPI dependency factory enforcing rate limits.
    Returns HTTP 429 Too Many Requests with Retry-After header on breach.
    """
    def dependency(request: Request):
        # Allow disabling rate limiting globally (e.g. for certain load testing or development)
        enabled = os.getenv("RATE_LIMIT_ENABLED", "true").lower() in ("true", "1", "yes")
        if not enabled:
            return

        # Determine limit expression
        limit_expr = limit_default
        if env_var_name:
            configured = os.getenv(env_var_name)
            if configured:
                limit_expr = configured.strip()

        ip = get_client_ip(request)
        prefix = key_prefix or request.url.path
        rate_key = f"{prefix}:{ip}"

        allowed, retry_after = default_rate_limiter.is_allowed(rate_key, limit_expr)
        if not allowed:
            record_security_event(
                event_type=SecurityEventType.RATE_LIMIT_EXCEEDED,
                request=request,
                detail=f"Rate limit exceeded: {limit_expr} on {prefix}. Retry after {retry_after}s.",
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded: Please try again in {retry_after} seconds.",
                headers={"Retry-After": str(retry_after)},
            )

    return dependency
