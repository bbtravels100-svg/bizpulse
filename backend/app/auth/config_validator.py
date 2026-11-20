import os
import logging
from pathlib import Path
from typing import Dict, Any, List

logger = logging.getLogger("bizpulse.security.config")

KNOWN_DEV_SECRETS = {
    "bizpulse_dev_jwt_secret_key_change_in_production_2026",
    "secret",
    "changeme",
    "jwt_secret",
    "default_secret",
}

SUPPORTED_JWT_ALGORITHMS = {"HS256", "HS384", "HS512", "RS256"}


class SecurityConfigurationError(Exception):
    """Raised when environment configuration violates security requirements."""
    pass


def mask_secret(secret: str, min_visible: int = 4) -> str:
    """Mask a secret string for safe logging."""
    if not secret:
        return "[NOT_SET]"
    if len(secret) <= min_visible * 2:
        return "[CONFIGURED - MASKED]"
    return f"{secret[:min_visible]}...{secret[-min_visible:]} ({len(secret)} chars)"


def validate_security_configuration() -> Dict[str, Any]:
    """
    Validate security-critical configuration on application startup.
    Strictly enforces production rules when ENVIRONMENT=production or BIZPULSE_ENV=production.
    Maintains convenient development defaults in non-production environments.
    """
    env = (os.getenv("ENVIRONMENT") or os.getenv("BIZPULSE_ENV") or "development").strip().lower()
    is_production = env in ("production", "prod")

    jwt_secret = os.getenv("JWT_SECRET_KEY", "bizpulse_dev_jwt_secret_key_change_in_production_2026")
    jwt_algo = os.getenv("JWT_ALGORITHM", "HS256").strip().upper()
    expire_minutes_raw = os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "60")
    cookie_secure_raw = os.getenv("COOKIE_SECURE", "false").strip().lower()
    allow_reg_raw = os.getenv("ALLOW_REGISTRATION", "true").strip().lower()

    errors: List[str] = []

    # 1. JWT Algorithm validation
    if jwt_algo not in SUPPORTED_JWT_ALGORITHMS:
        errors.append(
            f"Unsupported JWT_ALGORITHM '{jwt_algo}'. Supported algorithms: {sorted(SUPPORTED_JWT_ALGORITHMS)}"
        )

    # 2. Expiration validation
    try:
        expire_minutes = int(expire_minutes_raw)
        if expire_minutes <= 0 or expire_minutes > 10080:  # Max 7 days
            errors.append(f"JWT_ACCESS_TOKEN_EXPIRE_MINUTES must be between 1 and 10080 (got {expire_minutes})")
    except ValueError:
        errors.append(f"Invalid integer for JWT_ACCESS_TOKEN_EXPIRE_MINUTES: '{expire_minutes_raw}'")

    # 3. Production-specific strict checks
    if is_production:
        # Secret strength
        if jwt_secret in KNOWN_DEV_SECRETS or jwt_secret.startswith("bizpulse_dev_"):
            errors.append(
                "Known development JWT_SECRET_KEY is strictly forbidden in production. Set a cryptographically strong secret."
            )
        if len(jwt_secret) < 32:
            errors.append(
                f"JWT_SECRET_KEY must be at least 32 characters in production (current length: {len(jwt_secret)})"
            )

        # Cookie security
        if cookie_secure_raw not in ("true", "1", "yes"):
            errors.append(
                "COOKIE_SECURE must be enabled ('true') in production to enforce HTTPS-only cookies."
            )

        # Open registration check
        if allow_reg_raw in ("true", "1", "yes"):
            errors.append(
                "ALLOW_REGISTRATION must be disabled ('false') in production. Use AUTH_PROVISIONING_KEY instead."
            )

        # CORS validation
        allowed_origins_raw = os.getenv("ALLOWED_ORIGINS", "")
        origins = [o.strip() for o in allowed_origins_raw.split(",") if o.strip()]
        if not origins:
            errors.append("ALLOWED_ORIGINS must be explicitly configured in production (cannot be empty).")
        if "*" in origins:
            errors.append("Wildcard '*' in ALLOWED_ORIGINS is strictly forbidden in production when credentials are enabled.")

        # Database and backup paths validation
        db_path_val = os.getenv("DATABASE_PATH")
        if db_path_val and db_path_val != ":memory:":
            try:
                Path(db_path_val).parent.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                errors.append(f"DATABASE_PATH directory could not be created or accessed: {e}")

        backup_dir_val = os.getenv("BACKUP_DIR")
        if backup_dir_val:
            try:
                Path(backup_dir_val).mkdir(parents=True, exist_ok=True)
            except Exception as e:
                errors.append(f"BACKUP_DIR directory could not be created or accessed: {e}")

        # Gemini API Key configuration warning
        gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
        if not gemini_key or gemini_key == "your_gemini_api_key_here":
            logger.warning("GEMINI_API_KEY is unset or placeholder in production. AI investigations will fail until configured.")

    if errors:
        error_msg = "Security Configuration Validation Failed:\n- " + "\n- ".join(errors)
        logger.critical(error_msg)
        raise SecurityConfigurationError(error_msg)

    # Log safe masked configuration summary
    logger.info(
        f"Security configuration verified (env={env}): "
        f"JWT_ALGORITHM={jwt_algo}, "
        f"JWT_SECRET_KEY={mask_secret(jwt_secret)}, "
        f"COOKIE_SECURE={cookie_secure_raw in ('true', '1', 'yes')}, "
        f"ALLOW_REGISTRATION={allow_reg_raw in ('true', '1', 'yes')}"
    )

    return {
        "environment": env,
        "is_production": is_production,
        "jwt_algorithm": jwt_algo,
        "jwt_secret_masked": mask_secret(jwt_secret),
        "cookie_secure": cookie_secure_raw in ("true", "1", "yes"),
        "allow_registration": allow_reg_raw in ("true", "1", "yes"),
    }
