import logging
from enum import Enum
from typing import List, Set, Dict, Optional, Callable
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from .models import UserResponse
from .security import (
    decode_access_token,
    TokenExpiredError,
    InvalidTokenError,
)
from .database import is_token_revoked
from .audit import record_security_event, SecurityEventType
from .service import default_auth_service

logger = logging.getLogger("bizpulse.auth.permissions")

bearer_scheme = HTTPBearer(auto_error=False)


class Permission(str, Enum):
    """Centralized granular permissions for BizPulse operations."""
    # Analytics
    ANALYTICS_READ = "analytics:read"
    PROFITABILITY_READ = "profitability:read"

    # AI & Investigations
    AI_CHAT = "ai:chat"
    AI_INVESTIGATE = "ai:investigate"
    ADMIN_DIAGNOSTICS = "admin:diagnostics"

    # Actions & Proposals
    ACTION_VIEW = "action:view"
    ACTION_PROPOSE = "action:propose"
    ACTION_EDIT = "action:edit"
    ACTION_APPROVE = "action:approve"
    ACTION_REJECT = "action:reject"

    # Task Management
    TASK_VIEW = "task:view"
    TASK_ASSIGN = "task:assign"
    TASK_STATUS_UPDATE = "task:status_update"
    TASK_NOTE = "task:note"

    # Verification Engine
    VERIFICATION_VIEW = "verification:view"
    VERIFICATION_RUN = "verification:run"
    VERIFICATION_REOPEN = "verification:reopen"

    # Datasets
    DATASET_VIEW = "dataset:view"
    DATASET_UPLOAD = "dataset:upload"


# Standard business role names
ROLE_ADMIN = "CEO / Admin"
ROLE_OPS_MANAGER = "Operations Manager"
ROLE_FINANCE_ANALYST = "Finance Analyst"
ROLE_MARKETING_LEAD = "Marketing Lead"
ROLE_EMPLOYEE = "Employee"

# Mapping of business roles to allowed permissions
ROLE_PERMISSIONS: Dict[str, Set[Permission]] = {
    # CEO / Admin retains unrestricted access to all data and actions
    ROLE_ADMIN: set(Permission),
    "CEO": set(Permission),
    "Admin": set(Permission),

    # Operations Manager: operational data, investigations, tasks, verification.
    # CANNOT approve/reject proposals (CEO only) and CANNOT upload datasets (CEO only)
    ROLE_OPS_MANAGER: {
        Permission.ANALYTICS_READ,
        Permission.PROFITABILITY_READ,
        Permission.AI_CHAT,
        Permission.AI_INVESTIGATE,
        Permission.ADMIN_DIAGNOSTICS,
        Permission.ACTION_VIEW,
        Permission.ACTION_PROPOSE,
        Permission.ACTION_EDIT,
        Permission.TASK_VIEW,
        Permission.TASK_ASSIGN,
        Permission.TASK_STATUS_UPDATE,
        Permission.TASK_NOTE,
        Permission.VERIFICATION_VIEW,
        Permission.VERIFICATION_RUN,
        Permission.VERIFICATION_REOPEN,
        Permission.DATASET_VIEW,
    },

    # Finance Analyst: financial data, profitability, relevant investigations, chat, view tasks/datasets
    # NO proposal approval, dataset upload, or operational verification runs
    ROLE_FINANCE_ANALYST: {
        Permission.ANALYTICS_READ,
        Permission.PROFITABILITY_READ,
        Permission.AI_CHAT,
        Permission.AI_INVESTIGATE,
        Permission.ACTION_VIEW,
        Permission.TASK_VIEW,
        Permission.TASK_NOTE,
        Permission.VERIFICATION_VIEW,
        Permission.DATASET_VIEW,
    },

    # Marketing Lead: funnel/analytics, investigations, chat, view tasks/datasets
    # NO profitability (unit costs), proposal approval, or dataset upload
    ROLE_MARKETING_LEAD: {
        Permission.ANALYTICS_READ,
        Permission.AI_CHAT,
        Permission.AI_INVESTIGATE,
        Permission.ACTION_VIEW,
        Permission.TASK_VIEW,
        Permission.TASK_NOTE,
        Permission.VERIFICATION_VIEW,
        Permission.DATASET_VIEW,
    },

    # Employee: view assigned tasks, update their department task status, add notes, chat
    # NO approval, proposal generation, reassignments, verification runs, or dataset uploads
    ROLE_EMPLOYEE: {
        Permission.AI_CHAT,
        Permission.ACTION_VIEW,
        Permission.TASK_VIEW,
        Permission.TASK_STATUS_UPDATE, # Controlled via resource-level check
        Permission.TASK_NOTE,          # Controlled via resource-level check
        Permission.VERIFICATION_VIEW,
    },
}


def normalize_role(role: str) -> str:
    """Normalize raw role string to standard canonical role."""
    r = (role or "").strip().lower()
    if r in ("ceo", "admin", "ceo / admin", "ceo/admin", "administrator", "executive"):
        return ROLE_ADMIN
    if "operations" in r:
        return ROLE_OPS_MANAGER
    if "finance" in r:
        return ROLE_FINANCE_ANALYST
    if "marketing" in r:
        return ROLE_MARKETING_LEAD
    return ROLE_EMPLOYEE


def get_user_permissions(user: UserResponse) -> Set[Permission]:
    """Retrieve the set of permissions assigned to the user based on their canonical role."""
    canonical = normalize_role(user.role)
    return ROLE_PERMISSIONS.get(canonical, ROLE_PERMISSIONS[ROLE_EMPLOYEE])


def has_permission(user: UserResponse, permission: Permission) -> bool:
    """Check whether a user has a specific permission."""
    if not user.is_active:
        return False
    perms = get_user_permissions(user)
    return permission in perms


def has_any_role(user: UserResponse, roles: List[str]) -> bool:
    """Check if the user belongs to any of the specified roles."""
    if not user.is_active:
        return False
    user_canonical = normalize_role(user.role)
    canonical_targets = [normalize_role(r) for r in roles]
    return user_canonical in canonical_targets


def check_task_resource_access(
    user: UserResponse,
    task_department: str,
    task_owner_role: Optional[str] = None,
) -> bool:
    """
    Enforce backend resource-level authorization on task access and mutations.
    - CEO / Admin and Operations Manager can modify tasks across all departments.
    - Department leads can modify tasks in their department.
    - Employees can ONLY update or add notes to tasks assigned to their department or role.
    """
    canonical_role = normalize_role(user.role)
    if canonical_role in (ROLE_ADMIN, ROLE_OPS_MANAGER):
        return True

    user_dept = (user.department or "").strip().lower()
    task_dept = (task_department or "").strip().lower()

    if user_dept and (user_dept in task_dept or task_dept in user_dept):
        return True

    if task_owner_role and user.role.strip().lower() == task_owner_role.strip().lower():
        return True

    return False


def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> UserResponse:
    """
    FastAPI dependency to extract and validate the authenticated user.
    Extracts the token from:
    1. Authorization: Bearer <token> header
    2. access_token HttpOnly cookie
    Validates token signature, expiration, and user database state.
    """
    token: Optional[str] = None

    # Check Authorization header first
    if credentials and credentials.credentials:
        token = credentials.credentials
    else:
        # Fall back to HttpOnly cookie
        token = request.cookies.get("access_token")

    if not token:
        record_security_event(
            event_type=SecurityEventType.AUTH_401_DENIED,
            request=request,
            detail="Missing access token",
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required: No access token provided",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = decode_access_token(token)
    except TokenExpiredError:
        record_security_event(
            event_type=SecurityEventType.AUTH_401_DENIED,
            request=request,
            detail="Token signature expired",
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication session expired: Please log in again",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except InvalidTokenError:
        record_security_event(
            event_type=SecurityEventType.AUTH_401_DENIED,
            request=request,
            detail="Invalid token signature or format",
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")
    jti = payload.get("jti")

    # Check persistent token revocation (Phase 6 Step 3)
    if jti and is_token_revoked(jti):
        record_security_event(
            event_type=SecurityEventType.REVOKED_TOKEN_REJECTED,
            request=request,
            user_id=user_id,
            detail=f"Revoked token presented: jti={jti}",
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token has been revoked: Please log in again",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user_id:
        record_security_event(
            event_type=SecurityEventType.AUTH_401_DENIED,
            request=request,
            detail="Missing subject identifier in token payload",
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload: missing subject identifier",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = default_auth_service.get_user_by_id(user_id)
    if not user:
        record_security_event(
            event_type=SecurityEventType.AUTH_401_DENIED,
            request=request,
            user_id=user_id,
            detail="User account no longer exists in database",
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account associated with this token no longer exists",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        record_security_event(
            event_type=SecurityEventType.AUTH_401_DENIED,
            request=request,
            user_id=user_id,
            detail="Deactivated user account accessed",
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account has been deactivated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


def require_active_user(user: UserResponse = Depends(get_current_user)) -> UserResponse:
    """Alias dependency explicitly denoting active user requirement."""
    return user


def require_authenticated_user(user: UserResponse = Depends(get_current_user)) -> UserResponse:
    """Dependency verifying that the user is authenticated and active."""
    return user


def require_permissions(permissions: List[Permission]) -> Callable:
    """
    Dependency factory ensuring the authenticated user has ALL specified permissions.
    Raises HTTP 403 Forbidden if permissions are insufficient.
    """
    def dependency(user: UserResponse = Depends(get_current_user)) -> UserResponse:
        for perm in permissions:
            if not has_permission(user, perm):
                logger.warning(
                    f"Forbidden access: User '{user.email}' ({user.role}) lacks permission '{perm.value}'"
                )
                record_security_event(
                    event_type=SecurityEventType.AUTH_403_DENIED,
                    user_id=user.id,
                    detail=f"User {user.email} ({user.role}) lacks permission '{perm.value}'",
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Access forbidden: Insufficient permissions for '{perm.value}'. Required role: CEO/Admin or authorized manager.",
                )
        return user
    return dependency


def require_roles(roles: List[str]) -> Callable:
    """
    Dependency factory ensuring the authenticated user has at least one of the specified roles.
    Raises HTTP 403 Forbidden if the role is not authorized.
    """
    def dependency(user: UserResponse = Depends(get_current_user)) -> UserResponse:
        if not has_any_role(user, roles):
            logger.warning(
                f"Forbidden access: User '{user.email}' ({user.role}) is not in authorized roles {roles}"
            )
            record_security_event(
                event_type=SecurityEventType.AUTH_403_DENIED,
                user_id=user.id,
                detail=f"User {user.email} ({user.role}) not in authorized roles {roles}",
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access forbidden: Action restricted to roles: {', '.join(roles)}",
            )
        return user
    return dependency
