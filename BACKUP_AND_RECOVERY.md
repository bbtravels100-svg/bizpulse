# BizPulse — Backup, Restoration & Disaster Recovery Guide

> **Document Version**: 1.0.0  
> **Status**: Active Operational Reference  
> **Default Backup Directory**: `backend/data/backups/`  
> **Backup Format**: Standard SQLite Database Files (`bizpulse_backup_YYYYMMDD_HHMMSS.db`)

---

## 1. Automated Online Backup Architecture

Direct filesystem copying of an active SQLite database in WAL mode can produce a torn or corrupted file if a write occurs mid-copy. BizPulse eliminates this risk by using SQLite's native online backup API (`sqlite3.Connection.backup()`).

### 1.1 Key Backup Guarantees

1. **Transactional Consistency**: Backups capture an exact point-in-time snapshot of the database, integrating WAL pages safely.
2. **Zero Reader Downtime**: Backups proceed online while the API continues serving read queries.
3. **Automated Post-Backup Verification**: Every newly generated backup file is immediately validated with `PRAGMA integrity_check;` before being cataloged.
4. **Metadata Isolation**: Backups include file size, row counts, and SHA-256 digests. Sensitive credentials, passwords, and API keys are never stored in backup metadata.

---

## 2. Backup Execution Procedures

### 2.1 Programmatic Backup Creation

```python
from app.db import create_database_backup, prune_backups

# Create timestamped online backup
metadata = create_database_backup(label="daily_maintenance")
print(f"Created: {metadata['filename']} (SHA-256: {metadata['sha256']})")

# Prune older backups according to retention policy (keep last 7)
pruned = prune_backups(retention_count=7)
print(f"Pruned older archives: {pruned}")
```

### 2.2 Admin REST API Endpoint

Restricted to the `CEO / Admin` role:

- **Endpoint**: `POST /api/admin/db/backup`
- **Payload** *(optional)*:
  ```json
  {
    "label": "pre_deployment_snapshot",
    "prune_after": true,
    "retention_count": 7
  }
  ```
- **Response**:
  ```json
  {
    "filename": "bizpulse_backup_20261120_234500_pre_deployment_snapshot.db",
    "created_at": "2026-11-20T18:15:00.000000Z",
    "size_bytes": 147456,
    "sha256": "3a7b9c...f4e1",
    "tables_count": 8,
    "integrity": "OK",
    "pruned_backups": []
  }
  ```

---

## 3. Database Restoration Workflow

Database restoration is a critical administrative operation. BizPulse enforces strict safety gates to prevent data loss or accidental overwrites:

```
[Operator Invokes Restore (confirm_overwrite=true)]
                     │
         [1. Pre-Restore Validation]
         (PRAGMA integrity_check on backup file)
         Fails ➔ ABORT with DatabaseRestoreError
                     │
         [2. Safety Snapshot Capture]
         (Live active DB backed up to bizpulse_pre_restore_safety_*.db)
                     │
         [3. Online Atomic Restore]
         (Native SQLite backup API applies data to target)
                     │
         [4. Post-Restore Integrity Verification]
         (PRAGMA integrity_check + PRAGMA foreign_key_check)
                     │
     ┌───────────────┴───────────────┐
     │                               │
  [Passed]                        [Failed]
     │                               │
[Restoration Complete]     [5. Emergency Rollback]
                           (Restores from Safety Snapshot)
```

### 3.1 Programmatic Restoration

```python
from app.db import restore_database_from_backup

result = restore_database_from_backup(
    backup_path="backend/data/backups/bizpulse_backup_20261120_234500.db",
    confirm_overwrite=True,  # Mandatory safety gate
)
print(f"Restored successfully. Safety snapshot saved at: {result['safety_snapshot']}")
```

### 3.2 Admin REST API Restoration

Restricted to the `CEO / Admin` role:

- **Endpoint**: `POST /api/admin/db/restore`
- **Payload**:
  ```json
  {
    "backup_filename": "bizpulse_backup_20261120_234500.db",
    "confirm_overwrite": true
  }
  ```

---

## 4. Disaster Recovery & Manual Fallback

In the event of total server loss or manual emergency recovery:

1. Locate the latest verified backup in `backend/data/backups/` or offsite storage.
2. Stop the BizPulse API service:
   ```powershell
   Stop-Process -Name uvicorn -Force
   ```
3. Copy the backup file over the active database:
   ```powershell
   Copy-Item "backend\data\backups\bizpulse_backup_LATEST.db" "backend\data\bizpulse.db" -Force
   Remove-Item "backend\data\bizpulse.db-wal" -ErrorAction SilentlyContinue
   Remove-Item "backend\data\bizpulse.db-shm" -ErrorAction SilentlyContinue
   ```
4. Verify structural integrity:
   ```powershell
   .\.venv\Scripts\python.exe -c "from app.db import check_database_integrity; print(check_database_integrity())"
   ```
5. Restart the BizPulse service.
