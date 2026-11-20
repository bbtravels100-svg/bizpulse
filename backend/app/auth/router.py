import os
import logging
from datetime import datetime, timezone
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from .models import (
    UserLoginRequest,
    UserRegisterRequest,
    UserResponse,
    TokenResponse,
    MessageResponse,
)
from .security import (
    create_access_token,
    decode_access_token,
    get_jwt_expire_minutes,
)
from .service import (
    default_auth_service,
    InvalidCredentialsError,
    UserAlreadyExistsError,
    ProvisioningDeniedError,
)
from .permissions import (
    get_current_user,
    require_active_user,
    require_authenticated_user,
    require_roles,
    ROLE_ADMIN,
)
from .database import record_revoked_token, get_security_audit_logs
from .audit import record_security_event, SecurityEventType
from .rate_limiter import rate_limit
from .csrf import generate_csrf_token

logger = logging.getLogger("bizpulse.auth.router")

auth_router = APIRouter(prefix="/api/auth", tags=["Authentication"])
bearer_scheme = HTTPBearer(auto_error=False)


@auth_router.post(
    "/login",
    response_model=TokenResponse,
    summary="Authenticate user and obtain JWT access token",
    dependencies=[
        Depends(rate_limit(limit_default="10/minute", env_var_name="RATE_LIMIT_LOGIN", key_prefix="login"))
    ],
)
def login(request: UserLoginRequest, response: Response, http_request: Request):
    """
    Authenticate user credentials with generic error response and timing mitigation.
    Returns JWT token and sets secure HttpOnly cookie.
    Enforces rate limiting and logs security audit events.
    """
    try:
        user = default_auth_service.authenticate_user(request.email, request.password)
    except InvalidCredentialsError:
        record_security_event(
            event_type=SecurityEventType.LOGIN_FAILED,
            request=http_request,
            detail=f"Failed login attempt for email: {request.email}",
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    expire_minutes = get_jwt_expire_minutes()
    expires_in_seconds = expire_minutes * 60

    token = create_access_token({
        "sub": user.id,
        "email": user.email,
        "name": user.name,
        "role": user.role,
        "department": user.department,
    })

    # Set HttpOnly cookie for access token
    is_secure = os.getenv("COOKIE_SECURE", "false").lower() in ("true", "1", "yes")
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        max_age=expires_in_seconds,
        expires=expires_in_seconds,
        samesite="lax",
        secure=is_secure,
        path="/",
    )

    # Set non-HttpOnly cookie for CSRF token (Double-Submit Cookie pattern)
    csrf_token = generate_csrf_token()
    response.set_cookie(
        key="csrf_token",
        value=csrf_token,
        httponly=False,
        max_age=expires_in_seconds,
        expires=expires_in_seconds,
        samesite="lax",
        secure=is_secure,
        path="/",
    )

    record_security_event(
        event_type=SecurityEventType.LOGIN_SUCCESS,
        request=http_request,
        user_id=user.id,
        detail=f"User {user.email} logged in successfully",
    )

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in_seconds=expires_in_seconds,
        user=user,
    )


@auth_router.post(
    "/logout",
    response_model=MessageResponse,
    summary="Clear authentication cookie, revoke active JWT token, and invalidate session",
)
def logout(
    response: Response,
    http_request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
):
    """
    Revoke active JWT token in SQLite database and clear access_token HttpOnly cookie.
    Both Bearer header and cookie tokens are revoked.
    """
    token: Optional[str] = None
    if credentials and credentials.credentials:
        token = credentials.credentials
    else:
        token = http_request.cookies.get("access_token")

    user_id_logged_out: Optional[str] = None

    if token:
        try:
            payload = decode_access_token(token)
            jti = payload.get("jti")
            sub = payload.get("sub")
            exp = payload.get("exp")
            if jti and exp and sub:
                user_id_logged_out = sub
                expires_at = datetime.fromtimestamp(exp, tz=timezone.utc).isoformat()
                record_revoked_token(
                    jti=jti,
                    user_id=sub,
                    expires_at=expires_at,
                    reason="logout",
                )
        except Exception as e:
            logger.debug(f"Token decoding during logout: {e}")

    record_security_event(
        event_type=SecurityEventType.USER_LOGOUT,
        request=http_request,
        user_id=user_id_logged_out,
        detail="User logged out and session revoked",
    )

    is_secure = os.getenv("COOKIE_SECURE", "false").lower() in ("true", "1", "yes")
    response.delete_cookie(
        key="access_token",
        path="/",
        samesite="lax",
        secure=is_secure,
        httponly=True,
    )
    response.delete_cookie(
        key="csrf_token",
        path="/",
        samesite="lax",
        secure=is_secure,
        httponly=False,
    )
    return MessageResponse(message="Successfully logged out")


@auth_router.get(
    "/csrf",
    summary="Retrieve or generate a CSRF token for Double-Submit Cookie defense",
)
def get_csrf(response: Response, http_request: Request):
    """
    Retrieve current or generate fresh CSRF token and set the non-HttpOnly
    csrf_token cookie for double-submit cookie validation.
    """
    token = http_request.cookies.get("csrf_token") or generate_csrf_token()
    is_secure = os.getenv("COOKIE_SECURE", "false").lower() in ("true", "1", "yes")
    expire_seconds = get_jwt_expire_minutes() * 60
    response.set_cookie(
        key="csrf_token",
        value=token,
        httponly=False,
        max_age=expire_seconds,
        expires=expire_seconds,
        samesite="lax",
        secure=is_secure,
        path="/",
    )
    return {"csrf_token": token}


@auth_router.get(
    "/me",
    response_model=UserResponse,
    summary="Retrieve profile of the currently authenticated user",
)
def get_current_user_profile(user: UserResponse = Depends(get_current_user)):
    """Protected endpoint returning the profile of the verified user."""
    return user


@auth_router.post(
    "/provision",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Controlled user account provisioning for demo/admin onboarding",
    dependencies=[
        Depends(rate_limit(limit_default="5/minute", env_var_name="RATE_LIMIT_PROVISION", key_prefix="provision"))
    ],
)
def provision_user(request: UserRegisterRequest, http_request: Request):
    """
    Controlled user provisioning.
    Requires ALLOW_REGISTRATION=true or matching AUTH_PROVISIONING_KEY.
    Enforces rate limiting and logs security audit events.
    """
    try:
        return default_auth_service.provision_user(request)
    except ProvisioningDeniedError as e:
        record_security_event(
            event_type=SecurityEventType.PROVISIONING_RESTRICTED,
            request=http_request,
            detail=f"Restricted registration attempt for email: {request.email}",
        )
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except UserAlreadyExistsError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@auth_router.get(
    "/audit-logs",
    summary="Query recent security audit events (CEO / Admin Only)",
    dependencies=[Depends(require_roles([ROLE_ADMIN]))],
)
def query_audit_logs(
    limit: int = 50,
    event_type: Optional[str] = None,
):
    """Retrieve persistent security audit logs. Restricted to CEO/Admin."""
    return get_security_audit_logs(limit=min(limit, 200), event_type=event_type)
