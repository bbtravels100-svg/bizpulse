import os
import shutil
import sqlite3
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, Dict, Any

from .connection import get_db_path, get_db_connection

logger = logging.getLogger("bizpulse.db.restore")


class DatabaseRestoreError(Exception):
    """Raised when database restoration fails or validation rejects the backup."""
    pass


def restore_database_from_backup(
    backup_path: str,
    target_db_path: Optional[str] = None,
    confirm_overwrite: bool = False,
) -> Dict[str, Any]:
    """
    Perform a controlled, transactional database restoration from a verified backup file.

    Safety Controls:
    1. Operator Confirmation Gate: Strictly requires confirm_overwrite=True.
    2. Pre-Validation: Backup file must exist and pass PRAGMA integrity_check.
    3. Safety Snapshot: Current active database is archived to safety snapshot before touch.
    4. Online Atomic Restore: Uses native SQLite backup API to restore data.
    5. Post-Validation: Restored database must pass integrity and foreign-key checks.
    6. Automatic Rollback: If any error occurs, active database is restored from safety snapshot.
    """
    if not confirm_overwrite:
        raise DatabaseRestoreError(
            "Restoration rejected: Explicit operator confirmation (confirm_overwrite=True) is required "
            "to prevent accidental data overwrite."
        )

    b_path = Path(backup_path)
    if not b_path.exists() or not b_path.is_file():
        raise DatabaseRestoreError(f"Backup file not found: {backup_path}")

    target_path = Path(target_db_path or get_db_path())
    logger.warning(f"Initiating database restoration from {b_path.name} to {target_path}...")

    # Step 1: Pre-validate backup file integrity before touching active database
    try:
        val_conn = sqlite3.connect(str(b_path))
        try:
            cursor = val_conn.execute("PRAGMA integrity_check;")
            res = cursor.fetchone()[0]
            if res.lower() != "ok":
                raise DatabaseRestoreError(f"Backup file failed pre-restore integrity check: {res}")
        finally:
            val_conn.close()
    except sqlite3.DatabaseError as e:
        raise DatabaseRestoreError(f"Backup file is corrupted or not a valid SQLite database: {e}")

    # Step 2: Take pre-restore safety snapshot of the current active database
    now_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    safety_snapshot_path: Optional[Path] = None

    if target_path.exists():
        safety_snapshot_path = target_path.parent / f"bizpulse_pre_restore_safety_{now_str}.db"
        logger.info(f"Creating pre-restore safety snapshot at {safety_snapshot_path}...")
        try:
            active_conn = get_db_connection(str(target_path))
            try:
                snap_conn = sqlite3.connect(str(safety_snapshot_path))
                try:
                    with snap_conn:
                        active_conn.backup(snap_conn)
                finally:
                    snap_conn.close()
            finally:
                active_conn.close()
        except Exception as e:
            logger.error(f"Failed to create pre-restore safety snapshot: {e}")
            raise DatabaseRestoreError(f"Could not create safety snapshot prior to restore: {e}")

    # Step 3: Perform restoration using SQLite backup API from backup to target
    restored_successfully = False
    try:
        backup_conn = sqlite3.connect(str(b_path))
        try:
            # Connect to target DB and apply backup
            dest_conn = get_db_connection(str(target_path))
            try:
                with dest_conn:
                    backup_conn.backup(dest_conn)
            finally:
                dest_conn.close()
        finally:
            backup_conn.close()

        # Step 4: Run post-restoration integrity checks on target
        chk_conn = get_db_connection(str(target_path))
        try:
            chk_res = chk_conn.execute("PRAGMA integrity_check;").fetchone()[0]
            if chk_res.lower() != "ok":
                raise DatabaseRestoreError(f"Post-restore integrity check failed: {chk_res}")

            # Check foreign keys
            fk_violations = chk_conn.execute("PRAGMA foreign_key_check;").fetchall()
            if fk_violations:
                raise DatabaseRestoreError(
                    f"Post-restore foreign key check found {len(fk_violations)} violations"
                )

            table_count = chk_conn.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table';").fetchone()[0]
        finally:
            chk_conn.close()

        restored_successfully = True

    except Exception as restore_err:
        logger.critical(f"Database restore failed: {restore_err}. Executing automatic emergency rollback...")
        # Step 5: Emergency Rollback to safety snapshot
        if safety_snapshot_path and safety_snapshot_path.exists():
            try:
                roll_snap_conn = sqlite3.connect(str(safety_snapshot_path))
                try:
                    roll_dest_conn = get_db_connection(str(target_path))
                    try:
                        with roll_dest_conn:
                            roll_snap_conn.backup(roll_dest_conn)
                    finally:
                        roll_dest_conn.close()
                finally:
                    roll_snap_conn.close()
                logger.info("Emergency rollback to safety snapshot succeeded.")
            except Exception as rollback_err:
                logger.critical(f"FATAL: Emergency rollback also failed: {rollback_err}")
                raise DatabaseRestoreError(
                    f"Restoration failed ({restore_err}) AND rollback failed ({rollback_err}). "
                    f"Safety snapshot preserved at: {safety_snapshot_path}"
                )

        raise DatabaseRestoreError(f"Database restoration aborted and rolled back: {restore_err}")

    return {
        "status": "restored",
        "backup_source": str(b_path),
        "target_database": str(target_path),
        "safety_snapshot": str(safety_snapshot_path) if safety_snapshot_path else None,
        "restored_tables_count": table_count,
        "restored_at": datetime.now(timezone.utc).isoformat(),
    }
