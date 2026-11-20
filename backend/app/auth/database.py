import os
import sqlite3
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional

from ..db.connection import (
    get_db_path as _core_get_db_path,
    get_db_connection as _core_get_db_connection,
)
from ..db.migrations import run_migrations

logger = logging.getLogger("bizpulse.auth.database")

DEFAULT_DB_DIR = Path(__file__).resolve().parent.parent.parent / "data"
DEFAULT_DB_PATH = DEFAULT_DB_DIR / "bizpulse.db"


def get_db_path() -> str:
    """Return the configured SQLite database file path."""
    return _core_get_db_path()


def get_db_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    """Establish and return a robust SQLite database connection with row factory."""
    return _core_get_db_connection(db_path)


# Pre-configured demo accounts for all five business roles
DEMO_ACCOUNTS = [
    {
        "id": "usr-demo-000",
        "email": "ceo.sarah@bizpulse.internal",
        "name": "Sarah Connor",
        "role": "CEO / Admin",
        "department": "Executive Leadership",
        "plain_pw": "BizPulseCEO2026!",
    },
    {
        "id": "usr-demo-001",
        "email": "alex.morgan@bizpulse.internal",
        "name": "Alex Morgan",
        "role": "Operations Manager",
        "department": "Operations",
        "plain_pw": "BizPulseDemo2026!",
    },
    {
        "id": "usr-demo-002",
        "email": "jordan.lee@bizpulse.internal",
        "name": "Jordan Lee",
        "role": "Finance Analyst",
        "department": "Finance",
        "plain_pw": "BizPulseFinance2026!",
    },
    {
        "id": "usr-demo-003",
        "email": "taylor.swift@bizpulse.internal",
        "name": "Taylor Swift",
        "role": "Marketing Lead",
        "department": "Marketing",
        "plain_pw": "BizPulseMarketing2026!",
    },
    {
        "id": "usr-demo-004",
        "email": "sam.coder@bizpulse.internal",
        "name": "Sam Coder",
        "role": "Employee",
        "department": "Engineering",
        "plain_pw": "BizPulseEmployee2026!",
    },
    {
        "id": "usr-demo-005",
        "email": "casey.ops@bizpulse.internal",
        "name": "Casey Ops",
        "role": "Employee",
        "department": "Operations",
        "plain_pw": "BizPulseOpsWorker2026!",
    },
]

DEMO_USER_ID = DEMO_ACCOUNTS[1]["id"]
DEMO_USER_EMAIL = DEMO_ACCOUNTS[1]["email"]
DEMO_USER_NAME = DEMO_ACCOUNTS[1]["name"]
DEMO_USER_ROLE = DEMO_ACCOUNTS[1]["role"]
DEMO_USER_DEPT = DEMO_ACCOUNTS[1]["department"]
DEMO_USER_PLAIN_PW = DEMO_ACCOUNTS[1]["plain_pw"]


def init_auth_db(db_path: Optional[str] = None) -> None:
    """
    Initialize SQLite schema for Authentication, RBAC, Tokens, and Security Auditing.
    Executes ordered, tracked database migrations.
    """
    run_migrations(db_path)


def record_revoked_token(
    jti: str,
    user_id: str,
    expires_at: str,
    reason: Optional[str] = "logout",
    db_path: Optional[str] = None,
) -> None:
    """Store revoked token unique identifier (jti) and expiration timestamp in SQLite."""
    conn = get_db_connection(db_path)
    now = datetime.now(timezone.utc).isoformat()
    try:
        with conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO revoked_tokens (jti, user_id, expires_at, revoked_at, reason)
                VALUES (?, ?, ?, ?, ?);
                """,
                (jti, user_id, expires_at, now, reason or "logout"),
            )
            logger.info(f"Token revoked: jti={jti}, user_id={user_id}, reason={reason}")
    finally:
        conn.close()


def is_token_revoked(jti: str, db_path: Optional[str] = None) -> bool:
    """Check if token identifier (jti) has been recorded as revoked."""
    if not jti:
        return False
    conn = get_db_connection(db_path)
    try:
        cursor = conn.execute(
            "SELECT 1 FROM revoked_tokens WHERE jti = ?;",
            (jti,),
        )
        return cursor.fetchone() is not None
    finally:
        conn.close()


def cleanup_expired_revocations(db_path: Optional[str] = None) -> int:
    """Purge token revocation records that have passed their expiration timestamp."""
    conn = get_db_connection(db_path)
    now = datetime.now(timezone.utc).isoformat()
    try:
        with conn:
            cursor = conn.execute(
                "DELETE FROM revoked_tokens WHERE expires_at < ?;",
                (now,),
            )
            count = cursor.rowcount
            if count > 0:
                logger.info(f"Cleaned up {count} expired token revocation records")
            return count
    finally:
        conn.close()


def log_security_audit_event(
    event_type: str,
    user_id: Optional[str] = None,
    ip_address: Optional[str] = None,
    endpoint: Optional[str] = None,
    detail: Optional[str] = None,
    db_path: Optional[str] = None,
) -> str:
    """
    Persist structured security event into the SQLite audit table.
    Ensures passwords, raw tokens, and API keys are never stored.
    """
    import uuid
    log_id = f"sec-{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc).isoformat()
    conn = get_db_connection(db_path)
    try:
        with conn:
            conn.execute(
                """
                INSERT INTO security_audit_log (id, event_type, user_id, ip_address, endpoint, detail, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?);
                """,
                (log_id, event_type, user_id, ip_address or "unknown", endpoint or "unknown", detail or "", now),
            )
        return log_id
    except Exception as e:
        logger.error(f"Failed to record security audit event: {e}")
        return ""
    finally:
        conn.close()


def get_security_audit_logs(
    limit: int = 100,
    event_type: Optional[str] = None,
    db_path: Optional[str] = None,
) -> list:
    """Query recent security audit log records."""
    conn = get_db_connection(db_path)
    try:
        if event_type:
            cursor = conn.execute(
                """
                SELECT id, event_type, user_id, ip_address, endpoint, detail, created_at
                FROM security_audit_log
                WHERE event_type = ?
                ORDER BY created_at DESC
                LIMIT ?;
                """,
                (event_type, limit),
            )
        else:
            cursor = conn.execute(
                """
                SELECT id, event_type, user_id, ip_address, endpoint, detail, created_at
                FROM security_audit_log
                ORDER BY created_at DESC
                LIMIT ?;
                """,
                (limit,),
            )
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()
