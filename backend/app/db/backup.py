import os
import hashlib
import sqlite3
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

from .connection import get_db_path, get_db_connection

logger = logging.getLogger("bizpulse.db.backup")

DEFAULT_BACKUP_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "backups"


def get_backup_dir() -> Path:
    """Return the configured database backup directory path."""
    configured = os.getenv("BACKUP_DIR")
    if configured:
        p = Path(configured)
    else:
        p = DEFAULT_BACKUP_DIR
    p.mkdir(parents=True, exist_ok=True)
    return p


def calculate_file_sha256(file_path: Path) -> str:
    """Compute SHA-256 digest of a backup file."""
    sha = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            sha.update(chunk)
    return sha.hexdigest()


def create_database_backup(
    db_path: Optional[str] = None,
    backup_dir: Optional[str] = None,
    label: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Perform a consistent online backup of the SQLite database using SQLite's native backup API.
    Avoids copying active database files directly, guaranteeing transactional consistency.
    Validates backup integrity with PRAGMA integrity_check before completing.
    Never stores credentials, tokens, or private keys in metadata.
    """
    src_path = db_path or get_db_path()
    dest_dir = Path(backup_dir) if backup_dir else get_backup_dir()
    dest_dir.mkdir(parents=True, exist_ok=True)

    now = datetime.now(timezone.utc)
    timestamp_str = now.strftime("%Y%m%d_%H%M%S")
    clean_label = f"_{label.strip()}" if label else ""
    backup_filename = f"bizpulse_backup_{timestamp_str}{clean_label}.db"
    backup_filepath = dest_dir / backup_filename

    logger.info(f"Initiating online database backup to {backup_filepath}...")

    # Step 1: Execute online backup using native SQLite backup API
    src_conn = get_db_connection(src_path)
    try:
        dest_conn = sqlite3.connect(str(backup_filepath))
        try:
            with dest_conn:
                src_conn.backup(dest_conn, pages=100)
        finally:
            dest_conn.close()
    finally:
        src_conn.close()

    # Step 2: Validate integrity of newly created backup
    chk_conn = sqlite3.connect(str(backup_filepath))
    try:
        cursor = chk_conn.execute("PRAGMA integrity_check;")
        check_result = cursor.fetchone()[0]
        if check_result.lower() != "ok":
            if backup_filepath.exists():
                backup_filepath.unlink()
            raise RuntimeError(f"Backup failed integrity verification: {check_result}")

        # Count tables in backup for metadata
        tbl_cursor = chk_conn.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table';")
        tables_count = tbl_cursor.fetchone()[0]
    finally:
        chk_conn.close()

    # Step 3: Compute file properties
    file_size_bytes = backup_filepath.stat().st_size
    sha256 = calculate_file_sha256(backup_filepath)

    metadata = {
        "filename": backup_filename,
        "path": str(backup_filepath),
        "created_at": now.isoformat(),
        "size_bytes": file_size_bytes,
        "sha256": sha256,
        "tables_count": tables_count,
        "integrity": "OK",
    }

    logger.info(
        f"Backup completed successfully: {backup_filename} "
        f"({file_size_bytes} bytes, {tables_count} tables, sha256={sha256[:12]}...)"
    )

    return metadata


def list_backups(backup_dir: Optional[str] = None) -> List[Dict[str, Any]]:
    """List all available database backup files sorted by creation time descending."""
    target_dir = Path(backup_dir) if backup_dir else get_backup_dir()
    if not target_dir.exists():
        return []

    backups: List[Dict[str, Any]] = []
    for file in sorted(target_dir.glob("bizpulse_backup_*.db"), reverse=True):
        try:
            stat = file.stat()
            backups.append({
                "filename": file.name,
                "path": str(file),
                "size_bytes": stat.st_size,
                "modified_at": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
            })
        except Exception as e:
            logger.debug(f"Could not stat backup file {file}: {e}")

    return backups


def prune_backups(
    retention_count: int = 7,
    backup_dir: Optional[str] = None,
) -> List[str]:
    """
    Enforce backup retention policy.
    Keeps the latest `retention_count` backups and removes older ones.
    Returns list of pruned filenames.
    """
    target_dir = Path(backup_dir) if backup_dir else get_backup_dir()
    all_backups = list_backups(str(target_dir))

    pruned: List[str] = []
    if len(all_backups) > retention_count:
        to_remove = all_backups[retention_count:]
        for b in to_remove:
            fpath = Path(b["path"])
            try:
                if fpath.exists():
                    fpath.unlink()
                    pruned.append(b["filename"])
                    logger.info(f"Pruned old database backup: {b['filename']}")
            except Exception as e:
                logger.error(f"Failed to delete old backup {b['filename']}: {e}")

    return pruned
