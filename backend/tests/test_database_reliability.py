import os
import sqlite3
import tempfile
import uuid
import pytest
from pathlib import Path
from fastapi.testclient import TestClient

from app.main import app
from app.db.connection import (
    get_db_connection,
    execute_with_retry,
    db_transaction,
)
from app.db.migrations import (
    run_migrations,
    get_current_schema_version,
    get_applied_versions,
)
from app.db.backup import (
    create_database_backup,
    list_backups,
    prune_backups,
)
from app.db.restore import (
    restore_database_from_backup,
    DatabaseRestoreError,
)
from app.db.integrity import (
    check_database_integrity,
)

client = TestClient(app)

DEMO_CEO_EMAIL = "ceo.sarah@bizpulse.internal"
DEMO_CEO_PW = "BizPulseCEO2026!"
DEMO_OPS_EMAIL = "alex.morgan@bizpulse.internal"
DEMO_OPS_PW = "BizPulseDemo2026!"


@pytest.fixture
def temp_db():
    """Create a temporary SQLite database initialized with all migrations."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    run_migrations(path)
    yield path
    try:
        if os.path.exists(path):
            os.remove(path)
        wal = path + "-wal"
        shm = path + "-shm"
        if os.path.exists(wal):
            os.remove(wal)
        if os.path.exists(shm):
            os.remove(shm)
    except Exception:
        pass


@pytest.fixture
def temp_backup_dir():
    """Create a temporary directory for database backups."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


# ============================================================================
# 1. Connection & Transaction Reliability Tests
# ============================================================================

def test_db_transaction_commit(temp_db):
    """Verify that operations inside db_transaction commit successfully on clean exit."""
    test_id = f"act-{uuid.uuid4().hex[:8]}"

    with db_transaction(temp_db) as conn:
        conn.execute(
            """
            INSERT INTO actions (
                id, investigation_id, anomaly_id, problem_description,
                recommended_action, responsible_department, suggested_owner_role,
                priority, suggested_deadline, expected_outcome, verification_criteria,
                status, created_at, updated_at
            ) VALUES (?, 'inv-1', 'anom-1', 'prob', 'act', 'ops', 'lead', 'high', '2026-12-31', 'out', 'crit', 'PENDING_APPROVAL', 'now', 'now');
            """,
            (test_id,),
        )

    # Verify record was persisted
    conn = get_db_connection(temp_db)
    try:
        row = conn.execute("SELECT id FROM actions WHERE id = ?", (test_id,)).fetchone()
        assert row is not None
        assert row[0] == test_id
    finally:
        conn.close()


def test_db_transaction_rollback_on_error(temp_db):
    """Verify that unhandled exceptions trigger an automatic atomic rollback."""
    test_id = f"act-rollback-{uuid.uuid4().hex[:8]}"

    with pytest.raises(ValueError, match="Simulated error"):
        with db_transaction(temp_db) as conn:
            conn.execute(
                """
                INSERT INTO actions (
                    id, investigation_id, anomaly_id, problem_description,
                    recommended_action, responsible_department, suggested_owner_role,
                    priority, suggested_deadline, expected_outcome, verification_criteria,
                    status, created_at, updated_at
                ) VALUES (?, 'inv-1', 'anom-1', 'prob', 'act', 'ops', 'lead', 'high', '2026-12-31', 'out', 'crit', 'PENDING_APPROVAL', 'now', 'now');
                """,
                (test_id,),
            )
            raise ValueError("Simulated error inside transaction")

    # Verify record was rolled back
    conn = get_db_connection(temp_db)
    try:
        row = conn.execute("SELECT id FROM actions WHERE id = ?", (test_id,)).fetchone()
        assert row is None
    finally:
        conn.close()


def test_execute_with_retry_recovers_from_transient_lock(temp_db):
    """Verify execute_with_retry retries and succeeds when receiving transient SQLite lock errors."""
    attempts = 0

    def faulty_operation():
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise sqlite3.OperationalError("database is locked")
        return "success"

    conn = get_db_connection(temp_db)
    try:
        result = execute_with_retry(conn, faulty_operation, max_retries=4, initial_delay=0.01)
        assert result == "success"
        assert attempts == 3
    finally:
        conn.close()


# ============================================================================
# 2. Schema Versioning & Migrations Tests
# ============================================================================

def test_schema_migrations_initialization_and_idempotency(temp_db):
    """Verify migrations apply cleanly, track versions, and are idempotent."""
    current_ver = get_current_schema_version(temp_db)
    assert current_ver >= 5

    # Re-running migrations on up-to-date DB should apply 0 additional migrations
    newly_applied = run_migrations(temp_db)
    assert len(newly_applied) == 0

    conn = get_db_connection(temp_db)
    try:
        applied_versions = get_applied_versions(conn)
        assert {1, 2, 3, 4, 5}.issubset(applied_versions)
    finally:
        conn.close()


def test_schema_migrations_preserve_existing_records(temp_db):
    """Verify that running migrations preserves pre-existing user and action data."""
    test_email = f"user-{uuid.uuid4().hex[:6]}@bizpulse.internal"

    # Insert a user record
    conn = get_db_connection(temp_db)
    try:
        with conn:
            conn.execute(
                """
                INSERT INTO users (id, email, password_hash, name, role, department, is_active, created_at, updated_at)
                VALUES (?, ?, 'dummy_hash', 'Test User', 'Operations Manager', 'Operations', 1, 'now', 'now');
                """,
                (f"usr-{uuid.uuid4().hex[:8]}", test_email),
            )
    finally:
        conn.close()

    # Run migrations again
    run_migrations(temp_db)

    # Verify user record is completely intact
    conn = get_db_connection(temp_db)
    try:
        row = conn.execute("SELECT email FROM users WHERE email = ?", (test_email,)).fetchone()
        assert row is not None
        assert row[0] == test_email
    finally:
        conn.close()


# ============================================================================
# 3. Backup System Tests
# ============================================================================

def test_backup_creation_and_integrity(temp_db, temp_backup_dir):
    """Verify SQLite native backup creation, naming format, and integrity."""
    meta = create_database_backup(db_path=temp_db, backup_dir=temp_backup_dir, label="test")

    assert meta["integrity"] == "OK"
    assert meta["tables_count"] > 0
    assert meta["size_bytes"] > 0
    assert meta["filename"].startswith("bizpulse_backup_")
    assert meta["filename"].endswith("_test.db")
    assert len(meta["sha256"]) == 64

    backup_file = Path(temp_backup_dir) / meta["filename"]
    assert backup_file.exists()

    # Validate with SQLite directly
    b_conn = sqlite3.connect(str(backup_file))
    try:
        res = b_conn.execute("PRAGMA integrity_check;").fetchone()[0]
        assert res.lower() == "ok"
    finally:
        b_conn.close()


def test_list_and_prune_backups(temp_db, temp_backup_dir):
    """Verify listing and retention pruning of older database backups."""
    # Create 5 backups
    for i in range(5):
        create_database_backup(db_path=temp_db, backup_dir=temp_backup_dir, label=f"run{i}")

    all_backups = list_backups(temp_backup_dir)
    assert len(all_backups) == 5

    # Prune keeping latest 2
    pruned = prune_backups(retention_count=2, backup_dir=temp_backup_dir)
    assert len(pruned) == 3

    remaining = list_backups(temp_backup_dir)
    assert len(remaining) == 2


# ============================================================================
# 4. Database Restoration Tests
# ============================================================================

def test_database_restoration_success(temp_db, temp_backup_dir):
    """Verify controlled restore accurately rolls database back to backup state."""
    # Step 1: Create baseline action in database
    base_id = f"act-base-{uuid.uuid4().hex[:6]}"
    with db_transaction(temp_db) as conn:
        conn.execute(
            """
            INSERT INTO actions (
                id, investigation_id, anomaly_id, problem_description,
                recommended_action, responsible_department, suggested_owner_role,
                priority, suggested_deadline, expected_outcome, verification_criteria,
                status, created_at, updated_at
            ) VALUES (?, 'inv-1', 'anom-1', 'prob', 'act', 'ops', 'lead', 'high', '2026-12-31', 'out', 'crit', 'PENDING_APPROVAL', 'now', 'now');
            """,
            (base_id,),
        )

    # Step 2: Take backup
    meta = create_database_backup(db_path=temp_db, backup_dir=temp_backup_dir, label="pre_mutation")

    # Step 3: Mutate database by adding a new record that should vanish after restore
    mutated_id = f"act-mutated-{uuid.uuid4().hex[:6]}"
    with db_transaction(temp_db) as conn:
        conn.execute(
            """
            INSERT INTO actions (
                id, investigation_id, anomaly_id, problem_description,
                recommended_action, responsible_department, suggested_owner_role,
                priority, suggested_deadline, expected_outcome, verification_criteria,
                status, created_at, updated_at
            ) VALUES (?, 'inv-1', 'anom-1', 'prob', 'act', 'ops', 'lead', 'high', '2026-12-31', 'out', 'crit', 'PENDING_APPROVAL', 'now', 'now');
            """,
            (mutated_id,),
        )

    # Step 4: Restore from backup
    restore_meta = restore_database_from_backup(
        backup_path=meta["path"],
        target_db_path=temp_db,
        confirm_overwrite=True,
    )
    assert restore_meta["status"] == "restored"

    # Step 5: Verify base record exists and mutated record does not
    conn = get_db_connection(temp_db)
    try:
        base_row = conn.execute("SELECT id FROM actions WHERE id = ?", (base_id,)).fetchone()
        mutated_row = conn.execute("SELECT id FROM actions WHERE id = ?", (mutated_id,)).fetchone()
        assert base_row is not None
        assert mutated_row is None
    finally:
        conn.close()


def test_restore_rejects_without_confirmation(temp_db, temp_backup_dir):
    """Verify restore refuses execution if confirm_overwrite is False."""
    meta = create_database_backup(db_path=temp_db, backup_dir=temp_backup_dir)

    with pytest.raises(DatabaseRestoreError, match="Explicit operator confirmation"):
        restore_database_from_backup(
            backup_path=meta["path"],
            target_db_path=temp_db,
            confirm_overwrite=False,
        )


def test_restore_rejects_corrupted_backup_and_preserves_active(temp_db, temp_backup_dir):
    """Verify pre-validation blocks restore of corrupted backup without touching active DB."""
    # Write corrupt dummy file
    corrupt_file = Path(temp_backup_dir) / "corrupt_backup.db"
    corrupt_file.write_bytes(b"NOT_A_SQLITE_DATABASE_DATA_12345")

    # Insert canary record in active DB
    canary_id = f"canary-{uuid.uuid4().hex[:6]}"
    with db_transaction(temp_db) as conn:
        conn.execute(
            """
            INSERT INTO actions (
                id, investigation_id, anomaly_id, problem_description,
                recommended_action, responsible_department, suggested_owner_role,
                priority, suggested_deadline, expected_outcome, verification_criteria,
                status, created_at, updated_at
            ) VALUES (?, 'inv-1', 'anom-1', 'prob', 'act', 'ops', 'lead', 'high', '2026-12-31', 'out', 'crit', 'PENDING_APPROVAL', 'now', 'now');
            """,
            (canary_id,),
        )

    with pytest.raises(DatabaseRestoreError):
        restore_database_from_backup(
            backup_path=str(corrupt_file),
            target_db_path=temp_db,
            confirm_overwrite=True,
        )

    # Verify active DB is 100% unharmed
    conn = get_db_connection(temp_db)
    try:
        row = conn.execute("SELECT id FROM actions WHERE id = ?", (canary_id,)).fetchone()
        assert row is not None
    finally:
        conn.close()


# ============================================================================
# 5. Database Integrity Checks & Diagnostic API Tests
# ============================================================================

def test_check_database_integrity(temp_db):
    """Verify integrity diagnostic inspection report."""
    report = check_database_integrity(temp_db)
    assert report["status"] == "healthy"
    assert report["integrity_ok"] is True
    assert report["foreign_keys_ok"] is True
    assert report["schema_version"] >= 5
    assert len(report["errors"]) == 0
    assert "actions" in report["tables"]
    assert "users" in report["tables"]


def test_admin_db_api_rbac_and_execution():
    """Verify RBAC and endpoints on /api/admin/db."""
    # 1. Unauthenticated -> 401
    res_unauth = client.get("/api/admin/db/integrity")
    assert res_unauth.status_code == 401

    # 2. Operations Manager -> 403 (CEO/Admin Only)
    ops_login = client.post(
        "/api/auth/login",
        json={"email": DEMO_OPS_EMAIL, "password": DEMO_OPS_PW},
    )
    ops_token = ops_login.json()["access_token"]
    res_ops = client.get("/api/admin/db/integrity", headers={"Authorization": f"Bearer {ops_token}"})
    assert res_ops.status_code == 403

    # 3. CEO / Admin -> 200
    ceo_login = client.post(
        "/api/auth/login",
        json={"email": DEMO_CEO_EMAIL, "password": DEMO_CEO_PW},
    )
    ceo_token = ceo_login.json()["access_token"]
    headers = {"Authorization": f"Bearer {ceo_token}"}

    # Integrity check
    res_ceo = client.get("/api/admin/db/integrity", headers=headers)
    assert res_ceo.status_code == 200
    assert res_ceo.json()["integrity_ok"] is True

    # Backup trigger
    res_backup = client.post(
        "/api/admin/db/backup",
        headers=headers,
        json={"label": "api_test", "prune_after": True, "retention_count": 5},
    )
    assert res_backup.status_code == 200
    backup_meta = res_backup.json()
    assert backup_meta["integrity"] == "OK"

    # List backups
    res_list = client.get("/api/admin/db/backups", headers=headers)
    assert res_list.status_code == 200
    assert len(res_list.json()) >= 1
