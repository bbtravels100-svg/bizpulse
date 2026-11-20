# BizPulse — Production Release Checklist & Qualification Protocol

> **Document Version**: 1.0.0  
> **Status**: Official Production Protocol  
> **Purpose**: Mandatory verification checklist before deploying BizPulse to production environments.

---

## 1. Pre-Release Local Verification

Before opening a release PR or tagging a release candidate, complete all local checks:

- [ ] **Backend Test Suite (Local)**:
  ```powershell
  Set-Location D:\Bizpulse\backend
  .\.venv\Scripts\pytest.exe -v
  ```
  *Requirement: 232 / 232 tests passing with zero failures.*

- [ ] **Frontend Production Compilation (Local)**:
  ```powershell
  Set-Location D:\Bizpulse\frontend
  npm run build
  ```
  *Requirement: Zero TypeScript compiler errors (`tsc -b`), Vite bundle generated in `dist/`.*

- [ ] **Workflow Configuration Integrity (Local)**:
  ```powershell
  .\.venv\Scripts\pytest.exe tests/test_ci_cd.py -v
  ```
  *Requirement: Valid YAML, pinned actions, all 6 jobs present.*

- [ ] **Git Working Tree Hygiene**:
  ```powershell
  git status
  ```
  *Requirement: No uncommitted secrets, `.env` files, or temporary artifacts.*

---

## 2. GitHub Actions Automated Release Gates

Verify that GitHub Actions run on the target commit passed all 6 automated jobs:

- [ ] **Job 1: `backend-test` (Passed)**
  - Python 3.13 environment initialized.
  - All unit, integration, and E2E workflow tests passed.
  - `backend-test-results` artifact uploaded.

- [ ] **Job 2: `frontend-build` (Passed)**
  - Node.js 22 initialized with committed `package-lock.json`.
  - Production static bundle generated without errors.

- [ ] **Job 3: `docker-build` (Passed)**
  - Multi-stage Linux builds for backend (`bizpulse-backend:ci`) and frontend (`bizpulse-frontend:ci`) completed successfully.
  - No secrets copied into image layers.

- [ ] **Job 4: `container-integration-test` (Passed)**
  - Docker Compose service startup succeeded.
  - Backend minimal health check (`/api/health`) returned HTTP 200.
  - Frontend root (`/`) returned HTTP 200.
  - Nginx reverse proxy (`/api/health`) successfully forwarded to backend.
  - Auth login endpoint rejected invalid credentials with HTTP 401 (validates auth router).
  - Backend container confirmed running as unprivileged user `bizpulse` (UID 10001).
  - Volume persistence and container restart succeeded.

- [ ] **Job 5: `security-vulnerability-scan` (Passed)**
  - Trivy scanned both container images.
  - Zero unmitigated CRITICAL severity CVEs found.
  - Scan reports (`trivy-backend-report.txt`, `trivy-frontend-report.txt`) downloaded and reviewed.

- [ ] **Job 6: `release-validation-gate` (Passed)**
  - Final certification step confirmed all prerequisite gates green.

---

## 3. Production Environment & Secrets Verification

Ensure the production hosting environment is configured before container startup:

- [ ] **Cryptographic Secrets Generated**:
  - High-entropy `JWT_SECRET_KEY` generated: `openssl rand -hex 32` (>= 32 characters, never default).
  - Strong `AUTH_PROVISIONING_KEY` generated: `openssl rand -hex 24`.
  - Real Google Gemini API key configured in `GEMINI_API_KEY`.

- [ ] **Production Configuration Enforced**:
  - `ENVIRONMENT=production`
  - `COOKIE_SECURE=true` (HTTPS-only cookies)
  - `ALLOW_REGISTRATION=false` (Public registration disabled)
  - `ALLOWED_ORIGINS` explicitly set to production domain(s) without `*`.
  - `TRUST_PROXY_HEADERS=true` and `TRUSTED_PROXIES` configured for reverse proxy / load balancer.

- [ ] **Storage Volumes & File Permissions**:
  - Persistent volume `bizpulse_data` mapped to `/app/data`.
  - Host directory permissions allow write access by UID 10001 if using bind mounts.

---

## 4. Post-Deployment Verification & Smoke Tests

Immediately following container startup on the production server:

- [ ] **Verify Public Minimal Health**:
  ```bash
  curl -f https://bizpulse.yourcompany.com/api/health
  ```
  *Response must include `"status": "healthy"` without leaking paths or internals.*

- [ ] **Verify Protected Operational Diagnostics (CEO / Admin)**:
  Log in as CEO / Admin and check `GET /api/admin/diagnostics`:
  *Verify SQLite integrity check returns "OK", dataset count matches expected, Gemini reachability is true.*

- [ ] **Verify Prometheus Metrics Scraping**:
  Verify monitoring system can scrape `GET /api/admin/metrics` with Bearer auth:
  *Confirm `bizpulse_uptime_seconds`, `bizpulse_http_requests_total`, and `bizpulse_active_tasks_total` are populated.*

- [ ] **Create Initial Baseline Online Database Backup**:
  ```bash
  docker compose exec backend python -c "
  from app.db.backup import create_database_backup
  create_database_backup(label='post_release_baseline')
  "
  ```
