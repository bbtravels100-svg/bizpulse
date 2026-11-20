import os
import uuid
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError, InvalidHashError

logger = logging.getLogger("bizpulse.auth.security")

# Modern Argon2id password hasher configuration (Type.ID, 64MB memory, 3 iterations, 4 parallelism)
_hasher = PasswordHasher(
    time_cost=3,
    memory_cost=65536,
    parallelism=4,
    hash_len=32,
)

# Precomputed dummy hash for timing-safe comparison on non-existent users
_DUMMY_HASH = _hasher.hash("dummy_constant_timing_value_2026")


class AuthSecurityError(Exception):
    """Base exception for authentication and token validation errors."""
    pass


class TokenExpiredError(AuthSecurityError):
    """Raised when a JWT access token has expired."""
    pass


class InvalidTokenError(AuthSecurityError):
    """Raised when a JWT access token is malformed, has an invalid signature, or fails validation."""
    pass


class RevokedTokenError(AuthSecurityError):
    """Raised when a JWT access token has been revoked (e.g. after logout)."""
    pass


def get_jwt_secret_key() -> str:
    """Return JWT secret key from environment or development default."""
    secret = os.getenv("JWT_SECRET_KEY", "bizpulse_dev_jwt_secret_key_change_in_production_2026")
    if not secret:
        raise AuthSecurityError("JWT_SECRET_KEY is not configured in environment")
    return secret


def get_jwt_algorithm() -> str:
    """Return JWT signing algorithm (default HS256)."""
    return os.getenv("JWT_ALGORITHM", "HS256")


def get_jwt_expire_minutes() -> int:
    """Return JWT token expiration window in minutes."""
    try:
        return int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
    except ValueError:
        return 60


def hash_password(plain_password: str) -> str:
    """Hash a plaintext password using Argon2id."""
    if not plain_password:
        raise ValueError("Password cannot be empty")
    return _hasher.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plaintext password against an Argon2id hash.
    Returns True if valid, False otherwise.
    """
    if not plain_password or not hashed_password:
        return False
    try:
        return _hasher.verify(hashed_password, plain_password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def dummy_verify_password(plain_password: str) -> None:
    """
    Execute constant-time password verification on a dummy hash to prevent
    timing side-channel attacks when a user email is not found in the database.
    """
    try:
        _hasher.verify(_DUMMY_HASH, plain_password or "dummy")
    except Exception:
        pass


def create_access_token(
    payload: Dict[str, Any],
    expires_delta: Optional[timedelta] = None,
) -> str:
    """
    Generate a signed JWT access token with subject and expiration claims.
    """
    to_encode = payload.copy()
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=get_jwt_expire_minutes())

    jti = to_encode.get("jti") or str(uuid.uuid4())

    to_encode.update({
        "iat": now,
        "exp": expire,
        "jti": jti,
    })

    secret = get_jwt_secret_key()
    algorithm = get_jwt_algorithm()
    return jwt.encode(to_encode, secret, algorithm=algorithm)


def decode_access_token(token: str) -> Dict[str, Any]:
    """
    Decode and validate a signed JWT access token.
    Raises TokenExpiredError or InvalidTokenError on failure.
    """
    secret = get_jwt_secret_key()
    algorithm = get_jwt_algorithm()

    try:
        decoded = jwt.decode(
            token,
            secret,
            algorithms=[algorithm],
            options={"require": ["exp", "iat", "sub"]},
        )
        return decoded
    except jwt.ExpiredSignatureError as e:
        raise TokenExpiredError("Access token has expired") from e
    except (jwt.InvalidTokenError, jwt.DecodeError) as e:
        raise InvalidTokenError(f"Invalid access token: {str(e)}") from e
