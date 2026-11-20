# BizPulse — Production Environment Configuration Reference

> **Document Version**: 1.0.0  
> **Status**: Official Reference  
> **Scope**: Configuration variables, validation rules, secrets management, and security boundaries.

---

## 1. Environment Variable Reference

| Variable Name | Type | Required in Prod | Default | Description |
|:---|:---:|:---:|:---|:---|
| `ENVIRONMENT` | string | **Yes** | `development` | Environment mode (`development` or `production`). In `production`, strict fail-fast validation is enforced. |
| `HOST` | string | No | `0.0.0.0` | Bind host address for ASGI server. In containers, must be `0.0.0.0`. |
| `PORT` | integer | No | `8000` | Port for backend ASGI server. |
| `ALLOWED_ORIGINS` | string | **Yes** | (localhost) | Comma-separated list of exact allowed browser origins. Wildcards (`*`) are strictly forbidden in production. |
| `JWT_SECRET_KEY` | string | **Yes** | (none) | Cryptographic signing secret for JWT access tokens. Must be >= 32 characters and cannot match dev templates. |
| `JWT_ALGORITHM` | string | No | `HS256` | JWT signing algorithm (`HS256`, `HS384`, `HS512`, `RS256`). |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | integer | No | `60` | Token expiration window in minutes (1 to 10080). |
| `COOKIE_SECURE` | boolean | **Yes** | `false` | When `true`, enforces HTTPS `Secure` flag on authentication cookies. **Must be `true` in production.** |
| `ALLOW_REGISTRATION` | boolean | **Yes** | `true` | When `false`, blocks public account registration. **Must be `false` in production.** |
| `AUTH_PROVISIONING_KEY` | string | **Yes** | (none) | Shared administrative secret required to onboard new user accounts via `/api/auth/provision`. |
| `GEMINI_API_KEY` | string | **Yes** | (none) | Google Gemini API key for quantitative causal reasoning and multi-agent investigations. |
| `GEMINI_MODEL` | string | No | `gemini-2.5-flash` | Gemini model name for AI orchestration. |
| `LOG_LEVEL` | string | No | `INFO` | Logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`). `INFO` recommended for production. |
| `TRUST_PROXY_HEADERS` | boolean | No | `false` | Enable to resolve client IP addresses from `X-Forwarded-For` when operating behind a reverse proxy. |
| `TRUSTED_PROXIES` | string | No | `127.0.0.1` | Comma-separated list of trusted reverse proxy IPs or hostnames (e.g. `frontend,127.0.0.1`). |
| `DATABASE_PATH` | string | No | `backend/data/bizpulse.db` | Absolute or relative filesystem path to the primary SQLite database. |
| `BACKUP_DIR` | string | No | `backend/data/backups` | Filesystem directory for online SQLite database backups. |
| `DATA_DIR` | string | No | `backend/data` | Filesystem directory storing business CSV datasets (`sales.csv`, etc.). |
| `FRONTEND_PORT` | integer | No | `80` | Host port mapped to Nginx web server in `docker-compose.yml`. |

---

## 2. Production Security Validation Rules

On startup during FastAPI lifespan, `validate_security_configuration()` executes strict checks:

1. **JWT Secret Strength**:
   - Rejects secrets shorter than 32 characters.
   - Rejects known development secrets (`bizpulse_dev_...`, `secret`, `changeme`, `default_secret`).
2. **Secure Cookies**:
   - In production, `COOKIE_SECURE` must evaluate to `true`.
3. **Controlled Registration**:
   - In production, `ALLOW_REGISTRATION` must evaluate to `false`. User onboarding requires `AUTH_PROVISIONING_KEY`.
4. **CORS Origin Strictness**:
   - `ALLOWED_ORIGINS` cannot be empty.
   - `ALLOWED_ORIGINS` cannot contain wildcards (`*`).
5. **Path Validation**:
   - Verifies that directories for `DATABASE_PATH` and `BACKUP_DIR` exist or are writable.
6. **Gemini Key Sanity**:
   - Checks that `GEMINI_API_KEY` is configured and not the placeholder `your_gemini_api_key_here`.

---

## 3. Generating Cryptographic Secrets

Use `openssl` to generate cryptographically strong pseudo-random strings:

```bash
# JWT Secret Key (64 hex characters / 256 bits):
openssl rand -hex 32

# Onboarding Provisioning Key (48 hex characters / 192 bits):
openssl rand -hex 24
```

---

## 4. Secret Storage Best Practices

- **Never Commit Secrets**: Ensure `.env` and `.env.production` remain listed in `.gitignore` and `.dockerignore`.
- **File Permissions**: When storing secrets in a `.env.production` file on a server:
  ```bash
  chmod 600 .env.production
  chown root:root .env.production
  ```
- **Container Injection**: Pass environment variables to Docker via Docker Compose environment interpolation or your cloud provider's secret manager (AWS Secrets Manager, Google Cloud Secret Manager, Kubernetes Secrets).
