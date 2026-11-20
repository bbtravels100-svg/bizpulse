# BizPulse — Database Operations Guide

> **Document Version**: 1.0.0  
> **Status**: Active Operational Reference  
> **Target Database**: SQLite 3 with Write-Ahead Logging (WAL) Mode  
> **Managed Data Path**: `backend/data/bizpulse.db`

---

## 1. Database Architecture & Concurrency Model

BizPulse uses an optimized, reliable SQLite architecture designed for high local concurrency and transaction safety.

### 1.1 Core Engine Pragmas

Every database connection created through `app.db.connection.get_db_connection()` is configured with:

- **`PRAGMA journal_mode = WAL;`**: Write-Ahead Logging allows concurrent readers and a writer to operate without blocking each other. Readers never wait for writers, and writers do not block readers.
- **`PRAGMA synchronous = NORMAL;`**: In WAL mode, `NORMAL` synchronization provides full crash and power-loss durability while drastically reducing disk I/O overhead.
- **`PRAGMA foreign_keys = ON;`**: Enforces relational integrity across parent and child entities (`actions` ➔ `action_notes`, `metric_baselines` ➔ `verification_runs`, etc.) with cascading deletes where defined.
- **`PRAGMA busy_timeout = 15000;`**: Configures SQLite to wait up to 15 seconds during transient lock contention before raising an operational error.

---

## 2. Transaction Boundaries & Reliability

### 2.1 Explicit Atomic Transactions (`db_transaction`)

All state-modifying operations must be executed inside explicit transaction blocks:

```python
from app.db import db_transaction

with db_transaction() as conn:
    conn.execute("UPDATE actions SET status = ? WHERE id = ?;", (new_status, action_id))
    conn.execute("INSERT INTO action_audit_log (...) VALUES (...);")
    # Both statements commit atomically on block exit
    # Any unhandled exception rolls back all changes
```

### 2.2 Transient Lock Retries (`execute_with_retry`)

For high-concurrency write paths subject to transient contention, `execute_with_retry` provides bounded exponential backoff with jitter:

```python
from app.db import execute_with_retry

result = execute_with_retry(conn, lambda: conn.execute("..."), max_retries=3)
```

---

## 3. Schema Versioning & Migrations

BizPulse includes a dedicated, ordered migration engine (`app.db.migrations`) tracked via the `schema_migrations` table.

### 3.1 Migration Tracking Table

```sql
CREATE TABLE IF NOT EXISTS schema_migrations (
    version INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    applied_at TEXT NOT NULL,
    description TEXT
);
```

### 3.2 Canonical Migrations Inventory

| Version | Name | Description | Key Tables |
|:---:|---|---|---|
| `1` | `001_actions_and_tasks` | Action proposals, active tasks, threaded notes, audit trail | `actions`, `action_notes`, `action_audit_log` |
| `2` | `002_verification_engine` | Baseline capture, deterministic evaluation runs, verification notes | `metric_baselines`, `verification_runs`, `verification_notes` |
| `3` | `003_auth_and_rbac` | User accounts, Argon2id hashes, role and department mappings | `users` |
| `4` | `004_security_audit_and_revocation` | Persistent token revocation and structured security event logging | `revoked_tokens`, `security_audit_log` |
| `5` | `005_reliability_and_wal` | Schema consistency checks, department indexes, performance tuning | `actions` indexes |

### 3.3 Running Migrations

Migrations execute automatically on application startup via FastAPI `lifespan` handler. To manually apply pending migrations via Python:

```python
from app.db import run_migrations

applied = run_migrations()
print(f"Applied migrations: {applied}")
```

---

## 4. Database Integrity Inspection

A controlled diagnostic module (`app.db.integrity`) evaluates database health and structural soundness without downtime.

### 4.1 CLI Inspection

```python
from app.db import check_database_integrity

report = check_database_integrity()
print(report["status"])         # "healthy", "corrupted", or "fk_violations"
print(report["integrity_ok"])   # True / False
print(report["tables"])         # Table names and row counts
```

### 4.2 Admin REST API

Restricted strictly to the `CEO / Admin` role:

- `GET /api/admin/db/integrity`: Returns the complete structural health, page count, journal mode, and schema version report.
