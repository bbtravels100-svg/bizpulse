# BizPulse — Production Readiness Assessment & Deployment Guide

> **Document Version**: 0.5.0  
> **Evaluation Date**: 2026-11-20  
> **Current Verdict**: **PROTOTYPE / PILOT READY** (Requires Auth & Containerization before Public Cloud Production)

---

## 1. Production Readiness Scorecard (9 Categories)

| Category | Status | Evaluation Summary & Evidence |
|---|:---:|---|
| **1. Authentication & Backend RBAC** | **NOT IMPLEMENTED** | No authentication middleware or JWT verification on FastAPI routes. All endpoints are open. User roles in Settings are simulated in frontend state. |
| **2. API Security & CORS** | **PARTIAL** | CORS origins are restricted via `ALLOWED_ORIGINS` environment variable. Lacks API rate limiting, request signature checks, and CSRF protection. |
| **3. Secret Management** | **PASS** | `GEMINI_API_KEY` loaded via `.env` file (gitignored). `_sanitize_error()` automatically redacts API keys matching `AIza...` from all exceptions and logs. No client-side secrets. |
| **4. Database Backup & Recovery** | **PARTIAL** | CSV uploads feature automatic transactional `.bak` snapshots and rollback. SQLite `bizpulse.db` has WAL mode enabled, but lacks automated offsite replication or snapshotting. |
| **5. Logging & Monitoring** | **PARTIAL** | Comprehensive Python standard library logging across modules. Lacks structured JSON log shipping, APM tracing (OpenTelemetry), and Prometheus metric scrapers. |
| **6. Error Handling** | **PASS** | Robust domain exception hierarchy (`app.core.errors`) mapped to standard HTTP status codes (400, 401, 404, 409, 500, 502) with normalized JSON payloads. |
| **7. Dataset Integrity** | **PASS** | Strict schema validation, column type checking, numeric boundary verification, and SHA-256 fingerprint tracking on all dataset modifications. |
| **8. Process Concurrency** | **PARTIAL** | Thread-safe in-memory locks and SQLite partial unique index (`idx_actions_fingerprint`) prevent duplicate proposals and race conditions in single process; lacks distributed lock (Redis) for multi-worker setups. |
| **9. Deployment Configuration** | **PARTIAL** | Builds clean static bundle (`vite build`); requires manual virtualenv and npm setup; Dockerfile and Kubernetes manifests are not yet committed. |

---

## 2. Hard Blockers for Public Production Deployment

The following three items are **critical prerequisites** before deploying BizPulse to an untrusted public network or production enterprise environment:

1. **Implement Backend Authentication (JWT / OAuth2)**:
   - Prevent unauthorized access to action approvals, task assignments, and dataset uploads.
   - Enforce backend role-based access control (RBAC).

2. **Add API Rate Limiting & Protection**:
   - Protect `/api/investigate`, `/api/chat`, and `/api/agents/run` from denial-of-service or Gemini quota exhaustion using `slowapi` or an API gateway (e.g. Cloudflare / Kong).

3. **Containerization (Docker & Docker Compose)**:
   - Commit standardized multi-stage `Dockerfile` and `docker-compose.yml` configurations for predictable container execution.

---

## 3. Production Deployment Architecture (Recommended Target)

When ready for enterprise cloud deployment, the recommended infrastructure architecture is:

```
[ Internet Traffic ]
        │
        ▼
[ Cloudflare / Cloud CDN ] (SSL Termination, Rate Limiting, WAF)
        │
        ├───────────────────────────────┐
        ▼                               ▼
[ Static Web Storage / CDN ]   [ Reverse Proxy / API Gateway ]
(React Vite Production Dist)            │
                                        ▼
                       [ Containerized FastAPI Backend ]
                       (Google Cloud Run / AWS ECS / K8s)
                                        │
                       ┌────────────────┴────────────────┐
                       ▼                                 ▼
             [ Managed PostgreSQL ]             [ Google Gemini API ]
             (Cloud SQL / AWS RDS)              (Managed Enterprise AI)
```

---

## 4. Pre-Deployment Verification Checklist

Before taking any release to staging or production, execute this verification protocol:

- [x] **Backend Test Suite**: All 132 tests passing (`pytest tests/ -v`).
- [x] **Frontend Compilation**: TypeScript compilation passes with zero errors (`tsc -b`).
- [x] **Production Bundle**: Vite build produces clean optimized distribution (`vite build`).
- [x] **Secret Audit**: Verify `.env` files are excluded from version control (`.gitignore`).
- [x] **Idempotency Check**: Confirm duplicate action proposals are rejected or deduplicated via SHA-256 fingerprints.
- [x] **State Gate Check**: Verify verification runs are blocked on unapproved actions (HTTP 409).
- [x] **Dataset Rollback Check**: Confirm invalid CSV uploads trigger immediate `.bak` restoration.
- [ ] **Auth Layer**: Configure OAuth2/OIDC provider on backend routes (Pending Phase 6).
- [ ] **Container Build**: Build and scan production Docker images (Pending Phase 6).
