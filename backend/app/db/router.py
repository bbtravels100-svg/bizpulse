from typing import Optional, List
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, status

from ..auth.permissions import require_roles, ROLE_ADMIN
from .integrity import check_database_integrity
from .backup import create_database_backup, list_backups, prune_backups, get_backup_dir
from .restore import restore_database_from_backup, DatabaseRestoreError

db_admin_router = APIRouter(prefix="/api/admin/db", tags=["Database Administration"])


class BackupTriggerRequest(BaseModel):
    label: Optional[str] = Field(default=None, max_length=50)
    prune_after: bool = Field(default=True)
    retention_count: int = Field(default=7, ge=1, le=100)


class RestoreTriggerRequest(BaseModel):
    backup_filename: str = Field(min_length=1, max_length=255)
    confirm_overwrite: bool = Field(default=False)


@db_admin_router.get(
    "/integrity",
    summary="Run SQLite database integrity and diagnostic checks",
    dependencies=[Depends(require_roles([ROLE_ADMIN]))],
)
def get_db_integrity():
    """Execute structural and relational integrity checks on the active database."""
    report = check_database_integrity()
    return report


@db_admin_router.get(
    "/backups",
    summary="List available database backup snapshots",
    dependencies=[Depends(require_roles([ROLE_ADMIN]))],
)
def get_backups_list():
    """Retrieve catalog of verified database backup archives."""
    return list_backups()


@db_admin_router.post(
    "/backup",
    summary="Trigger an immediate online database backup",
    dependencies=[Depends(require_roles([ROLE_ADMIN]))],
)
def trigger_backup(request: Optional[BackupTriggerRequest] = None):
    """
    Perform an online, transactional backup using SQLite's native backup API.
    Optionally prunes old backups according to retention policy.
    """
    label = request.label if request else None
    retention = request.retention_count if request else 7

    try:
        metadata = create_database_backup(label=label)
        if request and request.prune_after:
            pruned = prune_backups(retention_count=retention)
            metadata["pruned_backups"] = pruned
        return metadata
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Backup creation failed: {str(e)}",
        )


@db_admin_router.post(
    "/restore",
    summary="Restore database from a verified backup snapshot",
    dependencies=[Depends(require_roles([ROLE_ADMIN]))],
)
def trigger_restore(request: RestoreTriggerRequest):
    """
    Perform a controlled database restoration from a verified backup snapshot.
    Strictly requires confirm_overwrite=true.
    Takes a pre-restore safety snapshot and automatically rolls back if integrity check fails.
    """
    if not request.confirm_overwrite:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Restoration aborted: 'confirm_overwrite' must be explicitly set to true.",
        )

    backup_dir = get_backup_dir()
    backup_path = backup_dir / request.backup_filename

    if not backup_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Backup file '{request.backup_filename}' not found in backup directory.",
        )

    try:
        result = restore_database_from_backup(
            backup_path=str(backup_path),
            confirm_overwrite=True,
        )
        return result
    except DatabaseRestoreError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database restoration failed: {str(e)}",
        )
