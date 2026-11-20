import os
import secrets
import logging
from urllib.parse import urlsplit
from typing import Optional, List, Callable
from starlette.types import ASGIApp, Scope, Receive, Send
from starlette.requests import Request
from starlette.responses import JSONResponse

from .audit import record_security_event, SecurityEventType
from ..observability.correlation import get_correlation_id

logger = logging.getLogger("bizpulse.security.csrf")

SAFE_METHODS = {"GET", "HEAD", "OPTIONS", "TRACE"}
AUTH_EXEMPT_PATHS = {
    "/api/auth/login",
    "/api/auth/logout",
    "/api/auth/provision",
}


def generate_csrf_token() -> str:
    """Generate a high-entropy cryptographically secure CSRF token."""
    return secrets.token_urlsafe(32)


def normalize_origin(origin_or_url: Optional[str]) -> Optional[str]:
    """Extract and normalize scheme://host[:port] from an origin or URL string."""
    if not origin_or_url or not origin_or_url.strip():
        return None
    try:
        parsed = urlsplit(origin_or_url.strip())
        if parsed.scheme and parsed.netloc:
            return f"{parsed.scheme.lower()}://{parsed.netloc.lower()}"
    except Exception:
        pass
    return None


def is_trusted_origin(origin_or_url: Optional[str], allowed_origins: List[str]) -> bool:
    """
    Check if an origin or referer URL matches any configured allowed origin.
    Prevents scheme, port or subpath bypasses.
    """
    norm = normalize_origin(origin_or_url)
    if not norm:
        return False

    for allowed in allowed_origins:
        allowed_norm = normalize_origin(allowed)
        if allowed_norm and norm == allowed_norm:
            return True
    return False


def validate_csrf_tokens(cookie_token: Optional[str], header_token: Optional[str]) -> bool:
    """
    Constant-time comparison between cookie and header CSRF tokens
    to prevent timing attacks.
    """
    if not cookie_token or not header_token:
        return False
    return secrets.compare_digest(cookie_token.strip(), header_token.strip())


class CSRFProtectionMiddleware:
    """
    Production-grade CSRF and Origin Protection Middleware.
    
    1. Origin / Referer Validation:
       For state-changing methods (POST, PUT, PATCH, DELETE), inspects Origin and
       Referer headers. If an untrusted origin is detected, immediately terminates with 403.
       
    2. Double-Submit Cookie CSRF Defense:
       If a request is authenticated via an HttpOnly cookie ('access_token') and
       does NOT provide an explicit 'Authorization: Bearer' header, requires a matching
       'X-CSRF-Token' header and 'csrf_token' cookie.
       
    API clients using explicit Bearer tokens without cookies are not subject to
    browser CSRF attacks and pass through once origin (if provided) is verified.
    """

    def __init__(self, app: ASGIApp, allowed_origins: Optional[List[str]] = None) -> None:
        self.app = app
        if allowed_origins is not None:
            self.allowed_origins = [o.strip() for o in allowed_origins if o.strip()]
        else:
            raw = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173")
            self.allowed_origins = [o.strip() for o in raw.split(",") if o.strip()]

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope)
        method = request.method.upper()

        # Safe read-only methods do not require CSRF token checks
        if method in SAFE_METHODS:
            await self.app(scope, receive, send)
            return

        # 1. Origin / Referer Verification for state-changing requests
        origin_header = request.headers.get("origin")
        referer_header = request.headers.get("referer")

        if origin_header:
            if not is_trusted_origin(origin_header, self.allowed_origins):
                corr_id = get_correlation_id()
                logger.warning(
                    f"Blocked state-changing request with untrusted Origin: {origin_header} "
                    f"({method} {request.url.path}, corr={corr_id})"
                )
                record_security_event(
                    event_type=SecurityEventType.UNTRUSTED_ORIGIN_BLOCKED,
                    request=request,
                    detail=f"Untrusted Origin: {origin_header}",
                )
                response = JSONResponse(
                    status_code=403,
                    content={
                        "detail": f"Cross-origin request rejected: Untrusted origin '{origin_header}'",
                        "correlation_id": corr_id,
                    },
                )
                await response(scope, receive, send)
                return
        elif referer_header:
            if not is_trusted_origin(referer_header, self.allowed_origins):
                corr_id = get_correlation_id()
                logger.warning(
                    f"Blocked state-changing request with untrusted Referer: {referer_header} "
                    f"({method} {request.url.path}, corr={corr_id})"
                )
                record_security_event(
                    event_type=SecurityEventType.UNTRUSTED_ORIGIN_BLOCKED,
                    request=request,
                    detail=f"Untrusted Referer: {referer_header}",
                )
                response = JSONResponse(
                    status_code=403,
                    content={
                        "detail": "Cross-origin request rejected: Untrusted referer header",
                        "correlation_id": corr_id,
                    },
                )
                await response(scope, receive, send)
                return

        # 2. CSRF Defense for Cookie-Authenticated Requests on Business Endpoints
        if request.url.path not in AUTH_EXEMPT_PATHS:
            cookie_access_token = request.cookies.get("access_token")
            auth_header = request.headers.get("authorization", "")
            has_bearer_token = auth_header.strip().lower().startswith("bearer ")

            # If relying on session cookie authentication without an explicit Bearer header
            if cookie_access_token and not has_bearer_token:
                csrf_cookie = request.cookies.get("csrf_token")
                csrf_header = (
                    request.headers.get("x-csrf-token")
                    or request.headers.get("x-csrftoken")
                )

                if not validate_csrf_tokens(csrf_cookie, csrf_header):
                    corr_id = get_correlation_id()
                    logger.warning(
                        f"CSRF validation failed for cookie-authenticated request "
                        f"({method} {request.url.path}, corr={corr_id})"
                    )
                    record_security_event(
                        event_type=SecurityEventType.CSRF_VALIDATION_FAILED,
                        request=request,
                        detail="Missing or mismatched X-CSRF-Token header on cookie session",
                    )
                    response = JSONResponse(
                        status_code=403,
                        content={
                            "detail": "Forbidden: CSRF validation failed. Missing or invalid X-CSRF-Token header.",
                            "correlation_id": corr_id,
                        },
                    )
                    await response(scope, receive, send)
                    return

        await self.app(scope, receive, send)
