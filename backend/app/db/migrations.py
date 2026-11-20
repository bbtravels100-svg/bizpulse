import sqlite3
import logging
from datetime import datetime, timezone
from typing import List, Set, Optional, Dict, Any

from .connection import get_db_connection

logger = logging.getLogger("bizpulse.db.migrations")


# Definition of all canonical schema migrations in execution order
MIGRATIONS = [
    {
        "version": 1,
        "name": "001_actions_and_tasks",
        "description": "Initialize action proposals, active tasks, notes, and audit log",
        "sql": """
        CREATE TABLE IF NOT EXISTS actions (
            id TEXT PRIMARY KEY,
            investigation_id TEXT NOT NULL,
            anomaly_id TEXT NOT NULL,
            problem_description TEXT NOT NULL,
            recommended_action TEXT NOT NULL,
            responsible_department TEXT NOT NULL,
            suggested_owner_role TEXT NOT NULL,
            priority TEXT NOT NULL,
            suggested_deadline TEXT NOT NULL,
            expected_outcome TEXT NOT NULL,
            verification_criteria TEXT NOT NULL,
            status TEXT NOT NULL,
            rejection_reason TEXT,
            completion_details TEXT,
            completed_at TEXT,
            action_fingerprint TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_actions_status ON actions(status);
        CREATE INDEX IF NOT EXISTS idx_actions_investigation ON actions(investigation_id);
        CREATE INDEX IF NOT EXISTS idx_actions_anomaly ON actions(anomaly_id);
        CREATE UNIQUE INDEX IF NOT EXISTS idx_actions_fingerprint ON actions(action_fingerprint) WHERE action_fingerprint IS NOT NULL;

        CREATE TABLE IF NOT EXISTS action_notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            action_id TEXT NOT NULL,
            note TEXT NOT NULL,
            author TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (action_id) REFERENCES actions(id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_notes_action_id ON action_notes(action_id);

        CREATE TABLE IF NOT EXISTS action_audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            action_id TEXT NOT NULL,
            action_type TEXT NOT NULL,
            previous_value TEXT,
            new_value TEXT,
            details TEXT,
            timestamp TEXT NOT NULL,
            FOREIGN KEY (action_id) REFERENCES actions(id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_audit_action_id ON action_audit_log(action_id);
        """,
    },
    {
        "version": 2,
        "name": "002_verification_engine",
        "description": "Initialize metric baselines, verification runs, and notes",
        "sql": """
        CREATE TABLE IF NOT EXISTS metric_baselines (
            id TEXT PRIMARY KEY,
            action_id TEXT NOT NULL,
            investigation_id TEXT NOT NULL,
            anomaly_id TEXT NOT NULL,
            metric_name TEXT NOT NULL,
            baseline_value REAL NOT NULL,
            baseline_period TEXT NOT NULL,
            expected_improvement TEXT NOT NULL,
            target_value REAL NOT NULL,
            comparison_direction TEXT NOT NULL,
            verification_criteria TEXT NOT NULL,
            captured_at TEXT NOT NULL,
            FOREIGN KEY (action_id) REFERENCES actions(id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_baselines_action_id ON metric_baselines(action_id);

        CREATE TABLE IF NOT EXISTS verification_runs (
            id TEXT PRIMARY KEY,
            action_id TEXT NOT NULL,
            baseline_id TEXT NOT NULL,
            verification_stage TEXT NOT NULL,
            evaluation_period TEXT NOT NULL,
            current_value REAL,
            absolute_change REAL,
            percentage_change REAL,
            outcome TEXT NOT NULL,
            target_met INTEGER NOT NULL,
            is_resolved INTEGER NOT NULL,
            needs_reopening INTEGER NOT NULL,
            data_source TEXT NOT NULL,
            gemini_analysis TEXT,
            executed_at TEXT NOT NULL,
            FOREIGN KEY (action_id) REFERENCES actions(id) ON DELETE CASCADE,
            FOREIGN KEY (baseline_id) REFERENCES metric_baselines(id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_verification_action_id ON verification_runs(action_id);
        CREATE INDEX IF NOT EXISTS idx_verification_baseline_id ON verification_runs(baseline_id);

        CREATE TABLE IF NOT EXISTS verification_notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            verification_id TEXT NOT NULL,
            action_id TEXT NOT NULL,
            note TEXT NOT NULL,
            author TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (verification_id) REFERENCES verification_runs(id) ON DELETE CASCADE,
            FOREIGN KEY (action_id) REFERENCES actions(id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_ver_notes_ver_id ON verification_notes(verification_id);
        """,
    },
    {
        "version": 3,
        "name": "003_auth_and_rbac",
        "description": "Initialize user accounts with Argon2id hashing and seed personas",
        "sql": """
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            name TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'Operations Manager',
            department TEXT NOT NULL DEFAULT 'Operations',
            is_active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email ON users(email);
        CREATE INDEX IF NOT EXISTS idx_users_active ON users(is_active);
        """,
    },
    {
        "version": 4,
        "name": "004_security_audit_and_revocation",
        "description": "Initialize persistent token revocation and security audit logging",
        "sql": """
        CREATE TABLE IF NOT EXISTS revoked_tokens (
            jti TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            revoked_at TEXT NOT NULL,
            reason TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_revoked_tokens_expires ON revoked_tokens(expires_at);

        CREATE TABLE IF NOT EXISTS security_audit_log (
            id TEXT PRIMARY KEY,
            event_type TEXT NOT NULL,
            user_id TEXT,
            ip_address TEXT,
            endpoint TEXT,
            detail TEXT,
            created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_security_log_type ON security_audit_log(event_type);
        CREATE INDEX IF NOT EXISTS idx_security_log_created ON security_audit_log(created_at);
        """,
    },
    {
        "version": 5,
        "name": "005_reliability_and_wal",
        "description": "Ensure column schema consistency and performance indexes",
        "sql": """
        -- Ensure action_fingerprint exists if actions table pre-dated migration
        CREATE INDEX IF NOT EXISTS idx_actions_created ON actions(created_at);
        CREATE INDEX IF NOT EXISTS idx_actions_dept ON actions(responsible_department);
        """,
    },
]


def init_migration_tracker(conn: sqlite3.Connection) -> None:
    """Ensure the schema_migrations tracking table exists."""
    conn.execute("""
    CREATE TABLE IF NOT EXISTS schema_migrations (
        version INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        applied_at TEXT NOT NULL,
        description TEXT
    );
    """)


def get_applied_versions(conn: sqlite3.Connection) -> Set[int]:
    """Retrieve all previously applied migration versions."""
    init_migration_tracker(conn)
    cursor = conn.execute("SELECT version FROM schema_migrations ORDER BY version ASC;")
    return {row[0] for row in cursor.fetchall()}


def get_current_schema_version(db_path: Optional[str] = None) -> int:
    """Return the highest applied schema migration version."""
    conn = get_db_connection(db_path)
    try:
        init_migration_tracker(conn)
        cursor = conn.execute("SELECT MAX(version) FROM schema_migrations;")
        row = cursor.fetchone()
        return row[0] if (row and row[0] is not None) else 0
    finally:
        conn.close()


def run_migrations(db_path: Optional[str] = None) -> List[int]:
    """
    Apply any unapplied schema migrations in explicit sequential order.
    Each migration is executed inside its own atomic transaction.
    Returns the list of migration versions applied during this invocation.
    """
    conn = get_db_connection(db_path)
    applied_now: List[int] = []

    try:
        with conn:
            init_migration_tracker(conn)

        applied = get_applied_versions(conn)

        for migration in MIGRATIONS:
            v = migration["version"]
            if v not in applied:
                logger.info(f"Applying migration v{v} ({migration['name']})...")
                now = datetime.now(timezone.utc).isoformat()

                with conn:
                    # 1. Execute migration SQL
                    conn.executescript(migration["sql"])

                    # 2. Record migration in tracker
                    conn.execute(
                        """
                        INSERT INTO schema_migrations (version, name, applied_at, description)
                        VALUES (?, ?, ?, ?);
                        """,
                        (v, migration["name"], now, migration.get("description", "")),
                    )

                applied_now.append(v)
                logger.info(f"Successfully applied migration v{v}")

        # Post-migration: seed auth demo personas if users table exists and accounts are missing
        _ensure_seed_personas(conn)

        return applied_now
    finally:
        conn.close()


def _ensure_seed_personas(conn: sqlite3.Connection) -> None:
    """Ensure demo user accounts are provisioned if users table is empty."""
    try:
        # Check if users table exists
        cursor = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='users';"
        )
        if not cursor.fetchone():
            return

        from ..auth.database import DEMO_ACCOUNTS
        from ..auth.security import hash_password

        now = datetime.now(timezone.utc).isoformat()
        with conn:
            for account in DEMO_ACCOUNTS:
                c = conn.execute(
                    "SELECT 1 FROM users WHERE email = ?;",
                    (account["email"].lower(),),
                )
                if not c.fetchone():
                    hashed = hash_password(account["plain_pw"])
                    conn.execute(
                        """
                        INSERT INTO users (id, email, password_hash, name, role, department, is_active, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?);
                        """,
                        (
                            account["id"],
                            account["email"].lower(),
                            hashed,
                            account["name"],
                            account["role"],
                            account["department"],
                            now,
                            now,
                        ),
                    )
    except Exception as e:
        logger.debug(f"Seed persona check during migration: {e}")
