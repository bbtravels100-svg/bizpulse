# BizPulse — Known Architectural Constraints & Technical Debt

> **Document Version**: 1.0.0  
> **Status**: Active Reference  
> **Purpose**: Provides an honest, rigorous catalog of current technical limitations, architectural trade-offs, and design boundaries in the BizPulse codebase.

---

## 1. Authentication & RBAC Boundaries (Resolved in Phase 6)

### Status: RESOLVED
- **Backend Authentication**: Fully implemented in Phase 6 Steps 1-3 using Argon2id password hashing, cryptographically signed JWT access tokens (HS256), and persistent token revocation via SQLite `revoked_tokens` table.
- **Role-Based Access Control**: Fully enforced on all sensitive business routes across 5 standard roles (`CEO / Admin`, `Operations Manager`, `Finance Analyst`, `Marketing Lead`, `Department Employee`) with department resource-level task ownership rules.
- **Frontend Integration**: Frontend `AuthContext` performs HttpOnly cookie session hydration and in-memory token management with automatic 401 interception.

---

## 2. Process Concurrency & Horizontal Scaling

### Current State
- Duplicate proposal prevention and dataset change tracking rely partly on process-memory mechanisms (`threading.Lock` in `ActionService` and `DatasetTracker`).
- Sliding-window rate limiters (`SlidingWindowRateLimiter`) and Prometheus metrics counters are stored in process memory.
- Persistence is handled via a single SQLite database file (`bizpulse.db`).

### Impact & Risk
- **Single-Process Constraint**: If BizPulse is scaled horizontally across multiple Uvicorn worker processes (`--workers 4`) or multi-container clusters (Kubernetes pods), in-memory rate limiters and metric counters will maintain separate state per worker process.
- While SQLite partial unique indexes (`idx_actions_fingerprint`) safeguard against duplicate row insertions in the database, extreme write surges across multiple workers could encounter busy waits.

### Recommended Future Remediation
- Transition rate limiting and distributed locks to Redis or Memcached.
- For multi-instance clustered scaling, migrate from local SQLite to managed cloud PostgreSQL (Amazon RDS or Google Cloud SQL) with PgBouncer connection pooling.

---

## 3. Local Environment Docker Engine Availability

### Current State
- On the current development Windows host, the Docker CLI (`docker`, `docker compose`) is not installed or available in the system PATH.
- Container specifications (`backend/Dockerfile`, `frontend/Dockerfile`, `frontend/nginx.conf`, `docker-compose.yml`, `docker-compose.dev.yml`) were verified via automated static analysis and specification test cases in `backend/tests/test_production_hardening.py`.

### Impact & Risk
- Live container image build (`docker build`) and containerized execution (`docker compose up`) cannot be executed directly on this local machine without installing Docker Desktop or Docker Engine.

### Recommended Future Remediation
- Install Docker Desktop or configure a remote Docker daemon host (e.g. CI/CD runner on GitHub Actions or GitLab CI) to execute live container builds and smoke tests.

---

## 4. Remote GitHub Actions CI/CD Execution Status

### Current State
- The local git repository is initialized on branch `main` but does not yet have a remote GitHub repository origin configured (`git remote -v` outputs nothing).
- The complete automated GitHub Actions workflow (`.github/workflows/ci.yml`) has been authored, verified for YAML syntax and structure, and validated through automated unit tests (`backend/tests/test_ci_cd.py`).

### Impact & Risk
- Live remote cloud pipeline execution (building Docker images on Ubuntu runners, running Trivy vulnerability scans, and running container integration tests) cannot trigger until the repository is connected to a remote GitHub repository (`git remote add origin ...`) and pushed.

### Recommended Future Remediation
- Connect the repository to GitHub following [`CI_CD.md`](file:///d:/Bizpulse/CI_CD.md) to activate the automated cloud release validation workflow.

---

## 5. Real-Time Communication & Polling

### Current State
- The frontend synchronizes data with the backend using on-demand HTTP polling or user-triggered refreshes.
- There are no active WebSockets, Server-Sent Events (SSE), or HTTP/2 push channels implemented for task status updates or verification completions.

### Impact & Risk
- Multi-user collaboration displays updated data only after page navigation or explicit refresh.
- Long-running multi-agent investigations block the HTTP request until completion rather than streaming intermediate agent thoughts.

### Recommended Future Remediation
- Implement FastAPI WebSocket endpoints or Server-Sent Events (`EventSource`) for real-time task notifications and multi-agent streaming thoughts.

---

## 5. Single-Host SQLite Engine & Distributed Clustering

### Current State
- Phase 6 Step 4 implemented native SQLite online backups (`sqlite3.Connection.backup()`), SHA-256 integrity checks, automated pre-restore safety snapshots, explicit transaction boundaries (`db_transaction`), and an ordered schema migration engine (`schema_migrations`).
- Write-Ahead Logging (`WAL`) and `PRAGMA synchronous = NORMAL;` are enforced, supporting high read concurrency and resilient crash recovery.
- Persistence remains anchored to a persistent volume file (`/app/data/bizpulse.db`).

### Impact & Risk
- Highly reliable for single-node container or VM deployments, but cannot support multi-instance load balancing across distributed clusters without shared storage.

### Recommended Future Remediation
- For multi-node distributed enterprise scaling, migrate from local SQLite to managed cloud PostgreSQL.

---

## 6. Dataset Upload Scope & Scalability

### Current State
- Datasets are loaded from and written to CSV files on disk (`/app/data/`).
- The entire dataset is parsed into memory via `pandas.read_csv()` for analytics calculations.
- Upload validation checks schemas synchronously in the request lifecycle.

### Impact & Risk
- Works efficiently for datasets with tens or hundreds of thousands of rows.
- Datasets exceeding tens of gigabytes will cause memory exhaustion (OOM) on small compute instances.

### Recommended Future Remediation
- Connect to a columnar cloud data warehouse (BigQuery, Snowflake, ClickHouse, or DuckDB) for enterprise data ingestion.
- Offload large file processing to asynchronous background job queues (Celery, ARQ, or Google Cloud Tasks).
