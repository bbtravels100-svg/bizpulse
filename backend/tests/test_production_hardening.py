import os
import re
import uuid
import pytest
from pathlib import Path
from starlette.testclient import TestClient

from app.main import app
from app.auth.security import create_access_token
from app.auth.config_validator import (
    validate_security_configuration,
    SecurityConfigurationError,
)
from app.auth.rate_limiter import default_rate_limiter

client = TestClient(app)

ROOT_DIR = Path(__file__).resolve().parent.parent.parent


@pytest.fixture(autouse=True)
def reset_rate_limits():
    """Reset rate limiter before each test execution."""
    default_rate_limiter.reset()
    yield
    default_rate_limiter.reset()


def get_test_token(role: str = "CEO / Admin") -> str:
    return create_access_token({
        "sub": "usr-demo-000",
        "email": "sarah.connor@bizpulse.internal",
        "name": "Sarah Connor",
        "role": role,
        "department": "Executive Leadership",
    })


TEST_PROPOSAL_PAYLOAD = {
    "problem_description": "Payment gateway timeout on mobile checkout",
    "recommended_action": "Verify and patch payment provider retry logic",
    "responsible_department": "Engineering",
    "suggested_owner_role": "Platform Engineer",
    "priority": "Medium",
    "suggested_deadline": "2026-12-01",
    "expected_outcome": "Payment failure rate drops below 1%",
    "verification_criteria": "Mobile checkout conversion restored to >80%",
    "investigation_id": "INV-TEST-001",
    "anomaly_id": "ANOMALY_FUNNEL_MOBILE_001",
}


# ------------------------------------------------------------------------------
# 1. CORS Allowed & Disallowed Origin Tests
# ------------------------------------------------------------------------------
def test_cors_preflight_allowed_origin():
    """Verify that trusted origins receive CORS headers during OPTIONS preflight."""
    headers = {
        "Origin": "http://localhost:5173",
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "Authorization,Content-Type,X-CSRF-Token",
    }
    response = client.options("/api/actions/tasks", headers=headers)
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"
    assert response.headers.get("access-control-allow-credentials") == "true"
    allowed_methods = response.headers.get("access-control-allow-methods", "")
    assert "POST" in allowed_methods
    assert "DELETE" in allowed_methods


def test_cors_preflight_rejected_for_untrusted_origin():
    """Verify that untrusted origins do not receive allow headers in preflight."""
    headers = {
        "Origin": "https://malicious-attacker-domain.com",
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "Authorization",
    }
    response = client.options("/api/actions/tasks", headers=headers)
    # Untrusted origin should NOT receive access-control-allow-origin
    assert "access-control-allow-origin" not in response.headers


def test_untrusted_origin_state_changing_request_blocked():
    """Verify that state-changing requests with an untrusted Origin header return 403."""
    token = get_test_token()
    response = client.post(
        "/api/actions/propose",
        headers={
            "Authorization": f"Bearer {token}",
            "Origin": "https://evil-phishing-site.org",
        },
        json=TEST_PROPOSAL_PAYLOAD,
    )
    assert response.status_code == 403
    data = response.json()
    assert "Untrusted origin" in data["detail"]
    assert "correlation_id" in data


def test_trusted_origin_state_changing_request_allowed():
    """Verify that requests from configured trusted origins are accepted."""
    token = get_test_token()
    response = client.post(
        "/api/actions/propose",
        headers={
            "Authorization": f"Bearer {token}",
            "Origin": "http://localhost:5173",
        },
        json={**TEST_PROPOSAL_PAYLOAD, "recommended_action": f"Action {uuid.uuid4().hex[:6]}"},
    )
    # Should not be rejected by Origin/CSRF middleware
    assert response.status_code in (200, 201)


# ------------------------------------------------------------------------------
# 2. CSRF Double-Submit Cookie Protection Tests
# ------------------------------------------------------------------------------
def test_csrf_cookie_auth_rejected_without_csrf_token():
    """Verify cookie-only state-changing requests are rejected if X-CSRF-Token header is missing."""
    token = get_test_token()
    response = client.post(
        "/api/actions/propose",
        cookies={"access_token": token},  # Authenticated purely via cookie, no Bearer header
        json=TEST_PROPOSAL_PAYLOAD,
    )
    assert response.status_code == 403
    data = response.json()
    assert "CSRF validation failed" in data["detail"]


def test_csrf_cookie_auth_rejected_with_mismatched_csrf_token():
    """Verify cookie-only requests fail when X-CSRF-Token does not match csrf_token cookie."""
    token = get_test_token()
    response = client.post(
        "/api/actions/propose",
        cookies={
            "access_token": token,
            "csrf_token": "valid-token-in-cookie-12345",
        },
        headers={
            "X-CSRF-Token": "tampered-different-token-67890",
        },
        json=TEST_PROPOSAL_PAYLOAD,
    )
    assert response.status_code == 403
    data = response.json()
    assert "CSRF validation failed" in data["detail"]


def test_csrf_cookie_auth_succeeds_with_matching_csrf_token():
    """Verify cookie-only requests succeed when header matches csrf_token cookie."""
    token = get_test_token()
    shared_csrf = "matching-csrf-token-abcxyz-987654321"
    response = client.post(
        "/api/actions/propose",
        cookies={
            "access_token": token,
            "csrf_token": shared_csrf,
        },
        headers={
            "X-CSRF-Token": shared_csrf,
        },
        json={**TEST_PROPOSAL_PAYLOAD, "recommended_action": f"Action {uuid.uuid4().hex[:6]}"},
    )
    assert response.status_code in (200, 201)
    assert "id" in response.json()


def test_bearer_token_exempt_from_cookie_csrf_enforcement():
    """
    Verify API clients sending Authorization: Bearer without cookies
    are NOT blocked by CSRF token checks.
    """
    token = get_test_token()
    response = client.post(
        "/api/actions/propose",
        headers={"Authorization": f"Bearer {token}"},
        json={**TEST_PROPOSAL_PAYLOAD, "recommended_action": f"Action {uuid.uuid4().hex[:6]}"},
    )
    assert response.status_code in (200, 201)


def test_csrf_token_endpoint_and_cookie_generation():
    """Verify GET /api/auth/csrf returns token and sets csrf_token cookie."""
    response = client.get("/api/auth/csrf")
    assert response.status_code == 200
    data = response.json()
    assert "csrf_token" in data
    assert len(data["csrf_token"]) >= 32
    assert "csrf_token" in response.cookies


# ------------------------------------------------------------------------------
# 3. Security Headers Verification
# ------------------------------------------------------------------------------
def test_security_headers_present_on_api_responses():
    """Verify foundational security headers are returned on all responses."""
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.headers.get("X-Content-Type-Options") == "nosniff"
    assert response.headers.get("X-Frame-Options") == "DENY"
    assert response.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"


# ------------------------------------------------------------------------------
# 4. Production Environment Validation Tests
# ------------------------------------------------------------------------------
def test_production_env_validation_rejects_weak_secret(monkeypatch):
    """Verify validate_security_configuration rejects dev secrets in production."""
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("JWT_SECRET_KEY", "bizpulse_dev_jwt_secret_key_change_in_production_2026")
    monkeypatch.setenv("COOKIE_SECURE", "true")
    monkeypatch.setenv("ALLOW_REGISTRATION", "false")
    monkeypatch.setenv("ALLOWED_ORIGINS", "https://app.bizpulse.com")

    with pytest.raises(SecurityConfigurationError) as exc_info:
        validate_security_configuration()
    assert "strictly forbidden in production" in str(exc_info.value)


def test_production_env_validation_rejects_wildcard_cors(monkeypatch):
    """Verify validate_security_configuration rejects '*' in ALLOWED_ORIGINS in production."""
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("JWT_SECRET_KEY", "a_very_strong_production_secret_key_64_characters_long_1234567890")
    monkeypatch.setenv("COOKIE_SECURE", "true")
    monkeypatch.setenv("ALLOW_REGISTRATION", "false")
    monkeypatch.setenv("ALLOWED_ORIGINS", "*")

    with pytest.raises(SecurityConfigurationError) as exc_info:
        validate_security_configuration()
    assert "Wildcard '*'" in str(exc_info.value)


def test_production_env_validation_passes_valid_config(monkeypatch):
    """Verify validate_security_configuration succeeds when all production criteria are met."""
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("JWT_SECRET_KEY", "a_very_strong_production_secret_key_64_characters_long_1234567890")
    monkeypatch.setenv("COOKIE_SECURE", "true")
    monkeypatch.setenv("ALLOW_REGISTRATION", "false")
    monkeypatch.setenv("ALLOWED_ORIGINS", "https://bizpulse.example.com")

    config = validate_security_configuration()
    assert config["is_production"] is True
    assert config["cookie_secure"] is True
    assert config["allow_registration"] is False


# ------------------------------------------------------------------------------
# 5. Static Architectural & Container Specification Tests
# ------------------------------------------------------------------------------
def test_backend_dockerfile_specifications():
    """Verify backend Dockerfile implements non-root execution and healthchecks."""
    dockerfile_path = ROOT_DIR / "backend" / "Dockerfile"
    assert dockerfile_path.exists(), "Backend Dockerfile must exist"
    content = dockerfile_path.read_text(encoding="utf-8")

    assert "FROM python:3.13-slim" in content, "Must use pinned Python base image"
    assert "USER bizpulse:bizpulse" in content, "Must switch to unprivileged user"
    assert "HEALTHCHECK" in content, "Must define container HEALTHCHECK"
    assert "/api/health" in content, "Health check must probe /api/health"
    assert "EXPOSE 8000" in content, "Must expose application port 8000"
    assert "AS builder" in content, "Must utilize multi-stage build"


def test_frontend_dockerfile_specifications():
    """Verify frontend Dockerfile uses multi-stage build with Nginx."""
    dockerfile_path = ROOT_DIR / "frontend" / "Dockerfile"
    assert dockerfile_path.exists(), "Frontend Dockerfile must exist"
    content = dockerfile_path.read_text(encoding="utf-8")

    assert "FROM node:22-alpine AS build" in content, "Build stage must use pinned Node image"
    assert "FROM nginx:1.27-alpine AS serve" in content, "Runner stage must use pinned Nginx image"
    assert "HEALTHCHECK" in content, "Must define frontend HEALTHCHECK"
    assert "nginx.conf" in content, "Must copy hardened nginx.conf"
    assert "EXPOSE 80" in content, "Must expose port 80"


def test_docker_compose_volume_and_security_specifications():
    """Verify docker-compose.yml configures named volumes, private network, and env interpolation."""
    compose_path = ROOT_DIR / "docker-compose.yml"
    assert compose_path.exists(), "docker-compose.yml must exist"
    content = compose_path.read_text(encoding="utf-8")

    assert "bizpulse_data:" in content, "Must define persistent named volume for SQLite and data"
    assert "/app/data" in content, "Volume must mount to /app/data"
    assert "bizpulse-net:" in content, "Must define isolated bridge network"
    assert "service_healthy" in content, "Frontend must wait for backend health check"
    assert "unless-stopped" in content, "Must configure restart policies"
    assert "JWT_SECRET_KEY" in content, "Must interpolate JWT_SECRET_KEY"
    assert "bizpulse_dev_" not in content, "Must not contain hardcoded development secrets"
