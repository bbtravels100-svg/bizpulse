import sqlite3
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List

from .connection import get_db_path, get_db_connection
from .migrations import get_current_schema_version

logger = logging.getLogger("bizpulse.db.integrity")


def check_database_integrity(db_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Run non-destructive SQLite integrity and diagnostic checks.
    Evaluates:
    - PRAGMA integrity_check (structure, B-tree balance, free-list)
    - PRAGMA foreign_key_check (relational integrity across all tables)
    - Journal mode & pragmas
    - Table counts & database page size
    - Applied schema migration version
    """
    target_path = Path(db_path or get_db_path())
    if not target_path.exists():
        return {
            "status": "not_found",
            "database_path": str(target_path),
            "integrity_ok": False,
            "errors": ["Database file does not exist"],
        }

    conn = get_db_connection(str(target_path))
    errors: List[str] = []

    try:
        # 1. Structural integrity check
        cursor = conn.execute("PRAGMA integrity_check;")
        raw_checks = [row[0] for row in cursor.fetchall()]
        integrity_ok = len(raw_checks) == 1 and raw_checks[0].lower() == "ok"
        if not integrity_ok:
            errors.extend([f"Integrity check issue: {c}" for c in raw_checks if c.lower() != "ok"])

        # 2. Foreign key check
        fk_cursor = conn.execute("PRAGMA foreign_key_check;")
        fk_violations = fk_cursor.fetchall()
        foreign_keys_ok = len(fk_violations) == 0
        if not foreign_keys_ok:
            for v in fk_violations:
                errors.append(f"Foreign key violation in table '{v[0]}' rowid {v[1]} -> parent '{v[2]}'")

        # 3. Pragmas & metadata
        journal_mode = conn.execute("PRAGMA journal_mode;").fetchone()[0]
        page_size = conn.execute("PRAGMA page_size;").fetchone()[0]
        page_count = conn.execute("PRAGMA page_count;").fetchone()[0]
        busy_timeout = conn.execute("PRAGMA busy_timeout;").fetchone()[0]

        # 4. Table inventories and row counts
        tables_cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name;"
        )
        tables: Dict[str, int] = {}
        for (table_name,) in tables_cursor.fetchall():
            try:
                count = conn.execute(f"SELECT COUNT(*) FROM {table_name};").fetchone()[0]
                tables[table_name] = count
            except Exception as e:
                tables[table_name] = -1
                errors.append(f"Could not count rows in {table_name}: {e}")

        # 5. Schema version
        schema_version = get_current_schema_version(str(target_path))

        status = "healthy"
        if not integrity_ok:
            status = "corrupted"
        elif not foreign_keys_ok:
            status = "fk_violations"

        return {
            "status": status,
            "database_path": str(target_path),
            "file_size_bytes": target_path.stat().st_size,
            "integrity_ok": integrity_ok,
            "foreign_keys_ok": foreign_keys_ok,
            "journal_mode": journal_mode,
            "page_size": page_size,
            "page_count": page_count,
            "busy_timeout_ms": busy_timeout,
            "schema_version": schema_version,
            "tables": tables,
            "errors": errors,
        }
    finally:
        conn.close()
