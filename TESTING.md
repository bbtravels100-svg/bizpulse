# BizPulse — Comprehensive Testing & Quality Assurance Suite

> **Total Tests**: 232 Backend Tests  
> **Frontend Validation**: TypeScript 5 Strict (`tsc -b`), Vite Production Build  
> **Test Status**: 100% Passing (232 passed in 47s)

---

## 1. Test Architecture & Directory Structure

BizPulse testing is divided across unit, integration, and security suites located in `backend/tests/`:

```
backend/tests/
├── conftest.py                   # Shared pytest fixtures, temporary databases, test authentication context
├── test_actions.py               # 24 tests: Proposal lifecycle, editing rules, idempotency, concurrency
├── test_advanced_security.py     # 18 tests: Token revocation, sliding rate limiter, security audits, AI guards
├── test_agents.py                # 13 tests: 4-agent roles, orchestration pipeline, error handling
├── test_analytics.py             # 8 tests: Financial math, margins, funnel, anomaly rules
├── test_api.py                   # 8 tests: Core HTTP endpoints, status codes, payload contracts
├── test_auth.py                  # 18 tests: Argon2id hashing, JWT lifecycle, cookie sessions, user provisioning
├── test_chat.py                  # 10 tests: Conversational assistant, intent routing, grounded citations
├── test_ci_cd.py                 # 7 tests: GitHub Actions workflow syntax, triggers, permissions, jobs, Trivy
├── test_data_loader.py           # 4 tests: Raw dataset loading, schema verification, parsing
├── test_database_reliability.py  # 12 tests: Backups, integrity checks, restoration, transactions, migrations
├── test_datasets.py              # 13 tests: CSV loading, schema validation, version tracking, cache invalidation
├── test_e2e_workflow.py          # 8 tests: Comprehensive end-to-end remediation lifecycles
├── test_gemini_service.py        # 10 tests: Auth validation, error sanitization, JSON parsing
├── test_investigation.py         # 15 tests: Fact extraction, prompt synthesis, diagnostic runs
├── test_observability.py         # 11 tests: Request correlation, structured JSON logs, diagnostics, metrics
├── test_production_hardening.py  # 16 tests: CORS preflight/origins, CSRF cookie tokens, security headers, Docker specs
├── test_rbac.py                  # 18 tests: Granular role boundaries, resource-level task ownership
└── test_verification.py          # 19 tests: Deterministic math, baseline immutability, approval gate
```

---

## 2. Test Execution Commands

### 2.1 Running the Complete Backend Suite
```powershell
# From D:\Bizpulse\backend
Set-Location D:\Bizpulse\backend
.\.venv\Scripts\pytest.exe -v
```

### 2.2 Running Production Hardening & Security Tests
```powershell
# Production Hardening Suite (Phase 6 Step 6)
.\.venv\Scripts\pytest.exe tests/test_production_hardening.py -v

# Advanced API Security & Token Revocation Suite (Phase 6 Step 3)
.\.venv\Scripts\pytest.exe tests/test_advanced_security.py -v

# Role-Based Access Control Suite (Phase 6 Step 2)
.\.venv\Scripts\pytest.exe tests/test_rbac.py -v
```

### 2.3 Running Frontend TypeScript Strict Check & Production Build
```powershell
# From D:\Bizpulse\frontend
Set-Location D:\Bizpulse\frontend
npm run build
```

---

## 3. Test Coverage by Capability Area

| Capability Area | Test Modules | Test Count | Key Invariants Verified |
|:---|:---|:---:|:---|
| **Production Hardening & Containerization** | `test_production_hardening.py` | 16 | CORS allowed/rejected origins, CSRF double-submit token enforcement, security headers, non-root user and volume specs. |
| **Authentication & RBAC** | `test_auth.py`, `test_rbac.py` | 36 | Argon2id verification, JWT expiration, role permissions, task department access boundaries. |
| **API Security & Abuse Defense** | `test_advanced_security.py` | 18 | Persistent token revocation, sliding window rate limiter, audit logs, AI payload limits. |
| **Observability & Telemetry** | `test_observability.py` | 11 | Structured JSON logs, X-Correlation-ID propagation, diagnostics RBAC, Prometheus metrics format. |
| **Database Reliability** | `test_database_reliability.py` | 12 | SQLite WAL mode, atomic transactions, online backup API, backup integrity, rollback safety. |
| **Action Centre & Tasks** | `test_actions.py` | 24 | Approval state machine, task assignment, progress notes, duplicate proposal prevention. |
| **Verification Engine** | `test_verification.py` | 19 | Approval-state verification gate, metric delta math, baseline immutability, action reopening. |
| **Multi-Agent Orchestration** | `test_agents.py`, `test_investigation.py` | 28 | 4-agent pipeline execution, prompt generation, causal reasoning, Gemini error handling. |
| **Dataset Invalidation** | `test_datasets.py`, `test_data_loader.py` | 17 | Version tracking, CSV validation, cache invalidation on upload, analytics reload. |
| **Business Analytics Engine** | `test_analytics.py`, `test_api.py` | 16 | Revenue comparisons, gross margins, funnel conversion, anomaly detection. |
| **AI Assistant Chat** | `test_chat.py` | 10 | Conversational assistant, intent classification, source citations. |
| **End-to-End Workflow** | `test_e2e_workflow.py` | 8 | Complete lifecycle: Detect → Explain → Recommend → Approve → Assign → Follow Up → Verify → Close. |
| **CI/CD Pipeline Validation** | `test_ci_cd.py` | 7 | GitHub Actions workflow syntax, permissions, triggers, Ubuntu runner, Docker Buildx, Trivy scan. |
| **TOTAL** | **17 Suites** | **232** | **All 232 passing with 0 regressions.** |
