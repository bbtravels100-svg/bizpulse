import os
import re
import logging
from enum import Enum
from typing import Optional
from fastapi import Request

from .database import log_security_audit_event, get_security_audit_logs

logger = logging.getLogger("bizpulse.security.audit")


class SecurityEventType(str, Enum):
    """Enumeration of monitored security events."""
    LOGIN_SUCCESS = "LOGIN_SUCCESS"
    LOGIN_FAILED = "LOGIN_FAILED"
    USER_LOGOUT = "USER_LOGOUT"
    REVOKED_TOKEN_REJECTED = "REVOKED_TOKEN_REJECTED"
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
    AUTH_401_DENIED = "AUTH_401_DENIED"
    AUTH_403_DENIED = "AUTH_403_DENIED"
    PROVISIONING_RESTRICTED = "PROVISIONING_RESTRICTED"
    AI_PAYLOAD_LIMIT_EXCEEDED = "AI_PAYLOAD_LIMIT_EXCEEDED"
    CSRF_VALIDATION_FAILED = "CSRF_VALIDATION_FAILED"
    UNTRUSTED_ORIGIN_BLOCKED = "UNTRUSTED_ORIGIN_BLOCKED"


# Patterns to strip from any logged detail string
_SENSITIVE_PATTERNS = [
    re.compile(r"password['\"]?\s*[:=]\s*['\"]?[^'\",\s]+", re.IGNORECASE),
    re.compile(r"bearer\s+[a-zA-Z0-9_\-\.]+", re.IGNORECASE),
    re.compile(r"key['\"]?\s*[:=]\s*['\"]?[^'\",\s]+", re.IGNORECASE),
    re.compile(r"token['\"]?\s*[:=]\s*['\"]?[^'\",\s]+", re.IGNORECASE),
]


def sanitize_security_detail(detail: Optional[str]) -> str:
    """Sanitize any potentially sensitive token or credential data before logging."""
    if not detail:
        return ""
    sanitized = detail
    for pattern in _SENSITIVE_PATTERNS:
        sanitized = pattern.sub("[REDACTED]", sanitized)
    return sanitized


def get_client_ip(request: Optional[Request]) -> str:
    """
    Safely resolve client IP address without blindly trusting proxy headers.
    Only inspects X-Forwarded-For if TRUST_PROXY_HEADERS is explicitly enabled
    and the direct peer is in the TRUSTED_PROXIES list.
    """
    if not request:
        return "unknown"

    direct_ip = request.client.host if request.client else "unknown"

    trust_proxies = os.getenv("TRUST_PROXY_HEADERS", "false").lower() in ("true", "1", "yes")
    if not trust_proxies:
        return direct_ip

    trusted_proxies_raw = os.getenv("TRUSTED_PROXIES", "127.0.0.1,::1,localhost")
    trusted_set = {p.strip() for p in trusted_proxies_raw.split(",") if p.strip()}

    if direct_ip in trusted_set:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            # First IP in X-Forwarded-For is client
            parts = [p.strip() for p in forwarded.split(",") if p.strip()]
            if parts:
                return parts[0]

    return direct_ip


def record_security_event(
    event_type: SecurityEventType,
    request: Optional[Request] = None,
    user_id: Optional[str] = None,
    endpoint: Optional[str] = None,
    detail: Optional[str] = None,
    db_path: Optional[str] = None,
) -> str:
    """
    Record a structured security event in SQLite and logger.
    Guarantees no raw passwords, bearer tokens, or private keys are persisted.
    """
    ip_address = get_client_ip(request)
    req_endpoint = endpoint
    if not req_endpoint and request:
        req_endpoint = f"{request.method} {request.url.path}"
    req_endpoint = req_endpoint or "unknown"

    safe_detail = sanitize_security_detail(detail)

    # Persist to SQLite
    log_id = log_security_audit_event(
        event_type=event_type.value,
        user_id=user_id,
        ip_address=ip_address,
        endpoint=req_endpoint,
        detail=safe_detail,
        db_path=db_path,
    )

    # Log to Python structured security logger
    logger.info(
        f"[SECURITY_EVENT] id={log_id} type={event_type.value} user={user_id or 'anon'} "
        f"ip={ip_address} endpoint={req_endpoint} detail={safe_detail}"
    )

    return log_id
