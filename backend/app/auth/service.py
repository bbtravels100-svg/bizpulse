import os
import sqlite3
import uuid
import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

from .database import get_db_connection
from .models import UserResponse, UserRegisterRequest
from .security import (
    hash_password,
    verify_password,
    dummy_verify_password,
)

logger = logging.getLogger("bizpulse.auth.service")


class AuthServiceError(Exception):
    """Base exception for authentication service operations."""
    pass


class InvalidCredentialsError(AuthServiceError):
    """Raised when authentication fails due to incorrect email or password."""
    pass


class UserAlreadyExistsError(AuthServiceError):
    """Raised when attempting to provision a user with an existing email."""
    pass


class ProvisioningDeniedError(AuthServiceError):
    """Raised when registration is attempted without proper provisioning authorization."""
    pass


class UserNotFoundError(AuthServiceError):
    """Raised when a user ID or email is not found in the database."""
    pass


class AuthService:
    """Service handling user authentication, credential validation, and controlled provisioning."""

    def __init__(self, db_path: Optional[str] = None):
        self._db_path = db_path

    def _get_connection(self) -> sqlite3.Connection:
        return get_db_connection(self._db_path)

    def _row_to_user_response(self, row: sqlite3.Row) -> UserResponse:
        """Convert database row to public UserResponse, explicitly omitting password_hash."""
        return UserResponse(
            id=row["id"],
            email=row["email"],
            name=row["name"],
            role=row["role"],
            department=row["department"],
            is_active=bool(row["is_active"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def authenticate_user(self, email: str, plain_password: str) -> UserResponse:
        """
        Authenticate user credentials.
        Applies timing defense on non-existent users and returns a generic error.
        Never reveals whether the email exists.
        """
        normalized_email = (email or "").strip().lower()
        if not normalized_email or not plain_password:
            dummy_verify_password(plain_password)
            raise InvalidCredentialsError("Invalid email or password")

        conn = self._get_connection()
        try:
            cursor = conn.execute(
                """
                SELECT id, email, password_hash, name, role, department, is_active, created_at, updated_at
                FROM users
                WHERE email = ?;
                """,
                (normalized_email,),
            )
            row = cursor.fetchone()

            if not row:
                # Mitigate timing attacks by performing constant-time hash verification on dummy value
                dummy_verify_password(plain_password)
                raise InvalidCredentialsError("Invalid email or password")

            # Verify Argon2id password hash
            if not verify_password(plain_password, row["password_hash"]):
                raise InvalidCredentialsError("Invalid email or password")

            # Check if user is active
            if not bool(row["is_active"]):
                raise InvalidCredentialsError("Invalid email or password")

            return self._row_to_user_response(row)
        finally:
            conn.close()

    def get_user_by_id(self, user_id: str) -> Optional[UserResponse]:
        """Fetch user by ID. Returns None if not found."""
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                """
                SELECT id, email, password_hash, name, role, department, is_active, created_at, updated_at
                FROM users
                WHERE id = ?;
                """,
                (user_id,),
            )
            row = cursor.fetchone()
            if not row:
                return None
            return self._row_to_user_response(row)
        finally:
            conn.close()

    def get_user_by_email(self, email: str) -> Optional[UserResponse]:
        """Fetch user by email. Returns None if not found."""
        normalized_email = (email or "").strip().lower()
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                """
                SELECT id, email, password_hash, name, role, department, is_active, created_at, updated_at
                FROM users
                WHERE email = ?;
                """,
                (normalized_email,),
            )
            row = cursor.fetchone()
            if not row:
                return None
            return self._row_to_user_response(row)
        finally:
            conn.close()

    def provision_user(
        self,
        request: UserRegisterRequest,
        is_bootstrap: bool = False,
    ) -> UserResponse:
        """
        Provision a new user account under controlled access conditions.
        Requires either ALLOW_REGISTRATION=true or matching AUTH_PROVISIONING_KEY.
        """
        normalized_email = request.email.strip().lower()

        # Controlled registration gate
        if not is_bootstrap:
            allow_reg = os.getenv("ALLOW_REGISTRATION", "false").lower() in ("true", "1", "yes")
            expected_key = os.getenv("AUTH_PROVISIONING_KEY", "")

            key_matches = bool(expected_key and request.provisioning_key == expected_key)
            if not allow_reg and not key_matches:
                raise ProvisioningDeniedError(
                    "User registration is restricted. A valid provisioning key is required."
                )

        conn = self._get_connection()
        try:
            with conn:
                # Check for existing email
                cursor = conn.execute(
                    "SELECT id FROM users WHERE email = ?;",
                    (normalized_email,),
                )
                if cursor.fetchone():
                    raise UserAlreadyExistsError(
                        "An account with this email address already exists."
                    )

                user_id = f"usr-{uuid.uuid4().hex[:12]}"
                hashed_password = hash_password(request.password)
                now = datetime.now(timezone.utc).isoformat()

                conn.execute(
                    """
                    INSERT INTO users (
                        id, email, password_hash, name, role, department, is_active, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?);
                    """,
                    (
                        user_id,
                        normalized_email,
                        hashed_password,
                        request.name.strip(),
                        request.role.strip() if request.role else "Operations Manager",
                        request.department.strip() if request.department else "Operations",
                        now,
                        now,
                    ),
                )

                cursor = conn.execute(
                    """
                    SELECT id, email, password_hash, name, role, department, is_active, created_at, updated_at
                    FROM users WHERE id = ?;
                    """,
                    (user_id,),
                )
                row = cursor.fetchone()
                return self._row_to_user_response(row)
        finally:
            conn.close()


default_auth_service = AuthService()
