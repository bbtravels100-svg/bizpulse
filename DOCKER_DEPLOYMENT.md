# BizPulse — Production Docker Deployment Guide

> **Document Version**: 1.0.0  
> **Status**: Production Ready Specifications  
> **Application**: BizPulse (AI-Powered Business Intelligence & Execution Platform)

---

## 1. Overview & Architecture

BizPulse is containerized using a clean, multi-tier decoupled architecture:
- **Backend Service (`bizpulse-backend`)**: Containerized FastAPI service on Python 3.13-slim using a multi-stage build, running unprivileged as `bizpulse` (UID 10001), serving the REST API with Uvicorn.
- **Frontend Service (`bizpulse-frontend`)**: Containerized React + TypeScript application built with Node 22-alpine and served via a hardened Nginx 1.27-alpine reverse proxy with SPA client-side routing.
- **Persistent Storage**: Docker named volume (`bizpulse_data`) mapped to `/app/data` to persist SQLite database (`bizpulse.db`, `bizpulse.db-wal`, `bizpulse.db-shm`), database backups (`/app/data/backups/`), and uploaded CSV datasets.
- **Network Isolation**: Dedicated private bridge network (`bizpulse-net`) shielding backend internal ports from the public internet.

```
                    ┌────────────────────────────────────────────────────────┐
                    │                      HOST MACHINE                      │
                    │                                                        │
                    │     HTTP Port 80                                       │
                    └───────────┬────────────────────────────────────────────┘
                                │
                                ▼
            ┌──────────────────────────────────────────────┐
            │   Frontend Container (nginx:1.27-alpine)      │
            │   - Serves React Static Bundle               │
            │   - Fallback SPA Routing (index.html)        │
            │   - Foundational Security Headers            │
            │   - Reverse Proxies /api/ ───┐               │
            └──────────────────────────────┼───────────────┘
                                           │
                        Internal Bridge    │ http://backend:8000/api/
                        Network            ▼
            ┌──────────────────────────────────────────────┐
            │   Backend Container (python:3.13-slim)       │
            │   - Non-root user: bizpulse (UID 10001)      │
            │   - FastAPI + Uvicorn ASGI Server            │
            │   - Observability, Correlation, Metrics      │
            │   - Strict CORS & Double-Submit CSRF         │
            └──────────────────────┬───────────────────────┘
                                   │
                                   ▼ Mounted at /app/data
            ┌──────────────────────────────────────────────┐
            │      Persistent Volume: bizpulse_data        │
            │      - bizpulse.db (WAL + SHM)               │
            │      - backups/ (Automated online backups)   │
            │      - *.csv (Business Data Sources)         │
            └──────────────────────────────────────────────┘
```

---

## 2. Docker Files Overview

| File | Purpose | Key Hardening Measures |
|:---|:---|:---|
| [`backend/Dockerfile`](file:///d:/Bizpulse/backend/Dockerfile) | Multi-stage Python build | Pinned base `python:3.13-slim`, virtualenv builder, non-root user `bizpulse` (UID 10001), `/api/health` health check, signal-aware ASGI entrypoint. |
| [`frontend/Dockerfile`](file:///d:/Bizpulse/frontend/Dockerfile) | Multi-stage Node + Nginx | Pinned `node:22-alpine` builder, minified production bundle, `nginx:1.27-alpine` runner, unprivileged pid/cache permissions. |
| [`frontend/nginx.conf`](file:///d:/Bizpulse/frontend/nginx.conf) | Production Nginx server block | `try_files $uri $uri/ /index.html;`, `/api/` proxy pass, gzip compression, asset caching headers, security headers. |
| [`docker-compose.yml`](file:///d:/Bizpulse/docker-compose.yml) | Production stack orchestration | Service health dependencies, private bridge network, volume mounts for persistence, environment interpolation. |
| [`docker-compose.dev.yml`](file:///d:/Bizpulse/docker-compose.dev.yml) | Development stack orchestration | Live volume bind mounts, hot-reloading (`--reload`, `npm run dev`), exposed ports 8000 & 5173. |
| [`.dockerignore`](file:///d:/Bizpulse/.dockerignore) | Root build exclusion | Excludes `.git`, `.env*`, `*.db*`, `node_modules`, `dist`, `.venv`, and `tests/`. |

---

## 3. Production Deployment Instructions

### Prerequisites
- Docker Engine 24.0+ and Docker Compose v2.20+ installed on host.
- Domain name pointed to the host IP.
- Gemini API key from Google AI Studio.

### Step 1: Clone Repository & Create Production Environment
```bash
git clone https://github.com/your-org/bizpulse.git /opt/bizpulse
cd /opt/bizpulse

# Copy production template
cp .env.production.example .env.production
chmod 600 .env.production
```

### Step 2: Generate Cryptographic Secrets
Generate strong 256-bit random keys for JWT signing and onboarding provisioning:
```bash
# Generate JWT Secret (min 32 chars)
openssl rand -hex 32

# Generate Provisioning Key (min 24 chars)
openssl rand -hex 24
```
Edit `.env.production` and populate:
- `JWT_SECRET_KEY=<generated-hex>`
- `AUTH_PROVISIONING_KEY=<generated-hex>`
- `GEMINI_API_KEY=<your-real-gemini-key>`
- `ALLOWED_ORIGINS=https://bizpulse.yourcompany.com`
- `COOKIE_SECURE=true`
- `ALLOW_REGISTRATION=false`

### Step 3: Launch with Docker Compose
```bash
docker compose --env-file .env.production up -d --build
```

### Step 4: Verify Deployment Health
```bash
# Check container status
docker compose ps

# Inspect backend minimal health
curl -f http://localhost:80/api/health

# Inspect container health logs
docker compose logs -f backend
```

---

## 4. Persistent Storage Management

All operational data resides in the named volume `bizpulse_data`:
- **Path in Container**: `/app/data`
- **Database File**: `/app/data/bizpulse.db`
- **Backups Directory**: `/app/data/backups/`
- **Datasets Directory**: `/app/data/` (seeded with initial CSV files)

### Creating an Immediate Online Backup Inside Container
```bash
docker compose exec backend python -c "
from app.db.backup import create_database_backup
meta = create_database_backup(label='manual_pre_maintenance')
print('Created backup:', meta['filename'])
"
```

### Restoring Database from a Backup File
```bash
docker compose exec backend python -c "
from app.db.restore import restore_database_backup
res = restore_database_backup('/app/data/backups/bizpulse_backup_20261121_000000_manual_pre_maintenance.db')
print('Restored:', res['restored_from'])
"
```

### Exporting Backups to Host
```bash
docker compose cp backend:/app/data/backups ./host_backups/
```

---

## 5. Development with Docker

For local development with live code editing and hot-reloading:
```bash
# Start development services
docker compose -f docker-compose.dev.yml up

# Access Frontend at http://localhost:5173
# Access Backend at http://localhost:8000
# Access Swagger Docs at http://localhost:8000/docs
```

---

## 6. Troubleshooting & Common Issues

### 1. `SecurityConfigurationError` on Backend Startup
- **Symptom**: Backend container exits immediately with code 1.
- **Cause**: In `ENVIRONMENT=production`, the configuration validator caught a dev secret, `COOKIE_SECURE=false`, `ALLOW_REGISTRATION=true`, or wildcard CORS origin.
- **Remedy**: Check `docker compose logs backend`. Ensure `JWT_SECRET_KEY` is not a default dev key and `ALLOWED_ORIGINS` has valid origins without `*`.

### 2. Frontend 403 "Cross-origin request rejected: Untrusted Origin"
- **Symptom**: API calls from browser fail with HTTP 403.
- **Cause**: Browser domain is not listed in `ALLOWED_ORIGINS`.
- **Remedy**: Add the exact domain (`https://yourdomain.com`) to `ALLOWED_ORIGINS` in `.env.production` and restart backend: `docker compose restart backend`.

### 3. Permission Denied on `/app/data`
- **Symptom**: SQLite operational error writing to database.
- **Cause**: Host directory mounted into container does not allow writes by UID 10001.
- **Remedy**: When using named volumes, Docker manages ownership automatically. If using host bind mounts, ensure UID 10001 has write permissions: `chown -R 10001:10001 ./data`.
