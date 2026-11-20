# BizPulse — Automated CI/CD Pipeline & Release Validation Guide

> **Document Version**: 1.0.0  
> **Status**: Official Production Reference  
> **Pipeline Configuration**: [`.github/workflows/ci.yml`](file:///d:/Bizpulse/.github/workflows/ci.yml)

---

## 1. Overview & Pipeline Architecture

BizPulse enforces automated quality, security, and integration gates on every commit and pull request targeting the `main` branch via GitHub Actions.

```
                                  Git Push / Pull Request / Dispatch
                                                  │
                                                  ▼
                       ┌─────────────────────────────────────────────────────┐
                       │           GitHub Actions Runner (Ubuntu)            │
                       │           Permissions: contents: read               │
                       └───────────┬─────────────────────────────┬───────────┘
                                   │                             │
                                   ▼                             ▼
                    ┌──────────────────────────────┐ ┌──────────────────────────────┐
                    │   Job 1: backend-test        │ │   Job 2: frontend-build      │
                    │   - Python 3.13 + pip cache  │ │   - Node.js 22 + npm cache   │
                    │   - 232 pytest tests         │ │   - TypeScript strict check  │
                    │   - JUnit XML test report    │ │   - Vite production bundle   │
                    └──────────────┬───────────────┘ └──────────────┬───────────────┘
                                   │                                │
                                   └────────────────┬───────────────┘
                                                    │
                                                    ▼
                                    ┌──────────────────────────────┐
                                    │   Job 3: docker-build        │
                                    │   - Docker Buildx on Linux   │
                                    │   - bizpulse-backend:ci      │
                                    │   - bizpulse-frontend:ci     │
                                    └───────────────┬──────────────┘
                                                    │
                                   ┌────────────────┴────────────────┐
                                   │                                 │
                                   ▼                                 ▼
                    ┌──────────────────────────────┐ ┌──────────────────────────────┐
                    │ Job 4: container-integration │ │ Job 5: security-vuln-scan    │
                    │ - docker compose up          │ │ - Trivy scanner on images    │
                    │ - Backend /api/health probe  │ │ - CRITICAL/HIGH/MED/LOW      │
                    │ - Frontend HTTP probe        │ │ - Machine-readable reports   │
                    │ - Nginx reverse-proxy probe  │ │ - Fails on CRITICAL          │
                    │ - Auth endpoint verify       │ └──────────────┬───────────────┘
                    │ - Non-root UID 10001 check   │                │
                    │ - Persistence after restart  │                │
                    │ - Ephemeral compose cleanup  │                │
                    └──────────────┬───────────────┘                │
                                   │                                │
                                   └────────────────┬───────────────┘
                                                    │
                                                    ▼
                                    ┌──────────────────────────────┐
                                    │ Job 6: release-validation    │
                                    │ - All prerequisites passed   │
                                    │ - Qualified for deployment   │
                                    └──────────────────────────────┘
```

---

## 2. Connecting to GitHub & Activating CI/CD

### Step 1: Initialize Remote Origin
If the repository is not yet linked to GitHub, add the remote repository URL:
```bash
git remote add origin https://github.com/<your-org-or-user>/bizpulse.git
git branch -M main
```

### Step 2: Push Workflow to GitHub
```bash
git add .
git commit -m "feat(ci): add automated GitHub Actions CI/CD release validation pipeline"
git push -u origin main
```

### Step 3: Verify GitHub Actions Activation
1. Navigate to your repository on GitHub: `https://github.com/<your-org-or-user>/bizpulse/actions`.
2. Verify the **BizPulse CI/CD & Automated Release Validation** workflow is active.
3. Every subsequent push or pull request to `main` will automatically trigger the 6 release validation jobs.

---

## 3. Pipeline Jobs & Validation Gates

| Job Name | Trigger / Dependencies | Runner | Success Criteria |
|:---|:---|:---|:---|
| **`backend-test`** | Push, PR, Dispatch | `ubuntu-latest` | Python 3.13 setup, dependency installation from `backend/requirements.txt`, 100% pass across all 232 tests, JUnit XML report generation. |
| **`frontend-build`** | Push, PR, Dispatch | `ubuntu-latest` | Node 22 setup, clean `npm ci` install from committed `package-lock.json`, 0 TypeScript compiler errors (`tsc -b`), clean Vite minified bundle. |
| **`docker-build`** | Needs `backend-test` + `frontend-build` | `ubuntu-latest` | Multi-stage Docker build for both backend and frontend images using Buildx. No public push; images reside exclusively in runner daemon. |
| **`container-integration-test`** | Needs `docker-build` | `ubuntu-latest` | Launches stack via Docker Compose, verifies `/api/health` returns 200, verifies frontend HTTP returns 200, tests Nginx `/api/` reverse-proxy, tests auth 401 response, validates backend runs as UID 10001, verifies volume restart resilience, and cleanly tears down all containers and volumes. |
| **`security-vulnerability-scan`** | Needs `docker-build` | `ubuntu-latest` | Runs Aqua Security Trivy container scanner against built images. Evaluates OS and package vulnerabilities across CRITICAL, HIGH, MEDIUM, and LOW. Produces JSON and table reports. Fails if unmitigated CRITICAL vulnerabilities are discovered. |
| **`release-validation-gate`** | Needs all preceding jobs | `ubuntu-latest` | Validates that all automated tests, builds, integration probes, and vulnerability checks passed before certifying the release candidate. |

---

## 4. Downloading Artifacts & Investigating Failures

### 1. Test Failure Reports
- **Artifact Name**: `backend-test-results`
- **Contents**: `test-results-backend.xml` (JUnit standard XML format).
- **How to Inspect**: In the GitHub Actions run summary, scroll to the **Artifacts** section at the bottom of the page and click `backend-test-results.zip`.

### 2. Frontend Compiled Bundle
- **Artifact Name**: `frontend-dist-bundle`
- **Contents**: Full production distribution (`dist/index.html`, minified CSS, JavaScript chunks).

### 3. Vulnerability Scan Reports
- **Artifact Name**: `vulnerability-scan-reports`
- **Contents**:
  - `trivy-backend-report.txt`: Human-readable table of backend package & OS findings.
  - `trivy-frontend-report.txt`: Human-readable table of frontend Nginx & OS findings.
  - `trivy-backend-report.json`: Machine-readable JSON for automated compliance tools.

---

## 5. CI/CD Security Posture

1. **Least Privilege Permissions**:
   The workflow declares top-level `permissions: contents: read`. It possesses no rights to write to code, push tags, or alter pull requests.
2. **Zero Production Secrets in CI**:
   The pipeline tests against ephemeral, sanitized test secrets:
   - `JWT_SECRET_KEY: "ci_test_jwt_secret_key_minimum_32_characters_long_12345"`
   - `AUTH_PROVISIONING_KEY: "bizpulse_demo_provisioning_key_2026"`
   - `ALLOWED_ORIGINS: "http://localhost:5173,http://127.0.0.1:5173"`
   Production secrets are never placed in repository secrets or logged to console outputs.
3. **Pull Request Isolation**:
   Pull requests submitted from fork repositories execute in isolated runner contexts without access to organization repository secrets.
4. **No Automated Production Deployment**:
   The workflow explicitly stops at release qualification. Actual production deployments require deliberate human authorization following the [`RELEASE_CHECKLIST.md`](file:///d:/Bizpulse/RELEASE_CHECKLIST.md).
