# BizPulse — Production Security Review & Threat Model

> **Document Version**: 1.0.0  
> **Status**: Comprehensive Security Audit  
> **Scope**: CORS, CSRF, Authentication, RBAC, Data Protection, Container Security.

---

## 1. Executive Summary

BizPulse has undergone systematic security hardening across Phase 6:
- **Phase 6 Step 1**: Argon2id password hashing, JWT signed tokens, HttpOnly cookie sessions.
- **Phase 6 Step 2**: Backend RBAC protecting all business routes with 5 distinct business roles.
- **Phase 6 Step 3**: Persistent JWT token revocation (`jti`), in-memory sliding rate limiting, SQLite tamper-evident security audit logs, AI payload size limits.
- **Phase 6 Step 4**: SQLite transactional safety (`PRAGMA foreign_keys = ON;`, `WAL` mode), online backup API with SHA-256 verification, safe pre-restore snapshots, and ordered tracked schema migrations.
- **Phase 6 Step 5**: Structured single-line JSON logging with sensitive credential redaction, asynchronous context correlation IDs, minimal public health endpoint, and protected low-cardinality Prometheus metrics.
- **Phase 6 Step 6**: Strict production CORS configuration, Double-Submit Cookie CSRF protection with Origin validation, unprivileged container execution (UID 10001), and Nginx reverse proxy routing.

---

## 2. CORS Policy Hardening

### Threat Mitigated
Malicious cross-origin web applications attempting to issue unauthorized API calls and read sensitive business metrics, financial anomalies, or employee tasks.

### Controls Enforced
1. **No Wildcard with Credentials**:
   `CORSMiddleware` explicitly rejects wildcard `*` when `allow_credentials=True`. In production, `validate_security_configuration` terminates startup if `*` is detected in `ALLOWED_ORIGINS`.
2. **Explicit Whitelisted Origins**:
   Origins are parsed and validated strictly against configured production domains (e.g. `https://bizpulse.example.com`).
3. **Restricted HTTP Methods & Headers**:
   - Allowed methods: strictly `["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"]`.
   - Allowed headers: strictly `["Content-Type", "Authorization", "X-Correlation-ID", "X-CSRF-Token", "Accept"]`.
   - Exposed headers: strictly `["X-Correlation-ID"]`.

---

## 3. Cross-Site Request Forgery (CSRF) Defense

### Threat Mitigated
A malicious website in another browser tab executing unauthorized state-changing actions (creating proposals, approving actions, deleting datasets, or triggering verification) using the victim's ambient browser cookies.

### Defense-in-Depth Implementation
BizPulse enforces a dual-layer CSRF defense implemented in `CSRFProtectionMiddleware`:

1. **Origin & Referer Validation**:
   For all unsafe HTTP methods (`POST`, `PUT`, `PATCH`, `DELETE`):
   - If an `Origin` header is present, it must normalize and match one of the whitelisted entries in `ALLOWED_ORIGINS`. Untrusted origins return HTTP 403 Forbidden immediately.
   - If `Origin` is absent, the `Referer` origin is checked against `ALLOWED_ORIGINS`.
2. **Double-Submit Cookie CSRF Tokens**:
   - When authenticating via `/api/auth/login`, the backend issues an HttpOnly `access_token` cookie and a non-HttpOnly `csrf_token` cookie.
   - Frontend JavaScript reads `csrf_token` and automatically transmits it via the `X-CSRF-Token` request header.
   - When a state-changing request relies on cookie authentication (i.e. `access_token` cookie is present without an `Authorization: Bearer` header):
     - The middleware checks `csrf_token` from cookies against `X-CSRF-Token` from headers.
     - Tokens are compared using `secrets.compare_digest` to prevent timing attacks.
     - If missing, mismatched, or empty, the request is rejected with `403 Forbidden`.
3. **Bearer Token Immunity**:
   Requests using explicit `Authorization: Bearer <token>` headers without relying on cookies are not subject to browser CSRF and pass directly (subject to Origin validation if sent by a browser).

---

## 4. Container & Operating System Hardening

1. **Unprivileged Execution User**:
   The backend container creates a dedicated system group and user `bizpulse` with UID/GID 10001:
   ```dockerfile
   RUN groupadd -g 10001 bizpulse && useradd -u 10001 -g bizpulse -s /bin/bash -m bizpulse
   USER bizpulse:bizpulse
   ```
   No application process runs as `root`.
2. **Minimal Base Image**:
   Uses `python:3.13-slim` and `nginx:1.27-alpine` without superfluous development compilers or debuggers in the final runner stage.
3. **Exclusion of Secrets**:
   `.dockerignore` prevents `.env`, local SQLite database files, `.git`, virtual environments, and test files from being copied into container layers.
4. **Foundational Security Headers**:
   Both FastAPI `SecurityHeadersMiddleware` and Nginx `nginx.conf` emit:
   - `X-Content-Type-Options: nosniff`
   - `X-Frame-Options: DENY` (SAMEORIGIN for Nginx)
   - `X-XSS-Protection: 1; mode=block`
   - `Referrer-Policy: strict-origin-when-cross-origin`

---

## 5. Security Audit Logging

All security-relevant events continue to be permanently recorded in SQLite `security_audit_log`:
- `LOGIN_SUCCESS`, `LOGIN_FAILED`, `USER_LOGOUT`
- `REVOKED_TOKEN_REJECTED`, `RATE_LIMIT_EXCEEDED`
- `AUTH_401_DENIED`, `AUTH_403_DENIED`
- `PROVISIONING_RESTRICTED`, `AI_PAYLOAD_LIMIT_EXCEEDED`
- `CSRF_VALIDATION_FAILED`, `UNTRUSTED_ORIGIN_BLOCKED`

All logged events record the client IP (with trusted proxy validation), target endpoint, timestamp, and sanitized details with zero credential leakage.
