import os
import time
import uuid
import pytest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient

from app.main import app
from app.auth.database import (
    get_db_connection,
    record_revoked_token,
    is_token_revoked,
    cleanup_expired_revocations,
    get_security_audit_logs,
)
from app.auth.security import (
    create_access_token,
    decode_access_token,
)
from app.auth.audit import (
    get_client_ip,
    record_security_event,
    SecurityEventType,
    sanitize_security_detail,
)
from app.auth.rate_limiter import default_rate_limiter
from app.auth.config_validator import (
    validate_security_configuration,
    SecurityConfigurationError,
)

client = TestClient(app)

DEMO_CEO_EMAIL = "ceo.sarah@bizpulse.internal"
DEMO_CEO_PW = "BizPulseCEO2026!"
DEMO_OPS_EMAIL = "alex.morgan@bizpulse.internal"
DEMO_OPS_PW = "BizPulseDemo2026!"


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    """Ensure clean rate limiter state for every test."""
    default_rate_limiter.reset()
    yield
    default_rate_limiter.reset()


# ============================================================================
# 1. Token Revocation Tests
# ============================================================================

def test_valid_token_succeeds():
    """Verify that a freshly issued token succeeds on authenticated routes."""
    login_res = client.post(
        "/api/auth/login",
        json={"email": DEMO_CEO_EMAIL, "password": DEMO_CEO_PW},
    )
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]

    me_res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_res.status_code == 200
    assert me_res.json()["email"] == DEMO_CEO_EMAIL


def test_logout_revokes_token_bearer_and_cookie():
    """Verify that logout revokes active JWT token for both Bearer and Cookie."""
    login_res = client.post(
        "/api/auth/login",
        json={"email": DEMO_CEO_EMAIL, "password": DEMO_CEO_PW},
    )
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]

    # 1. Perform logout with Bearer token
    logout_res = client.post(
        "/api/auth/logout",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert logout_res.status_code == 200

    # 2. Re-attempt to use the logged-out token via Bearer header: must return 401
    me_bearer = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_bearer.status_code == 401
    assert "revoked" in me_bearer.json()["detail"].lower()

    # 3. Re-attempt to use the logged-out token via Cookie: must return 401
    cookie_client = TestClient(app)
    cookie_client.cookies.set("access_token", token)
    me_cookie = cookie_client.get("/api/auth/me")
    assert me_cookie.status_code == 401
    assert "revoked" in me_cookie.json()["detail"].lower()


def test_revocation_persists_in_database():
    """Verify that token revocation is stored in SQLite and checked persistently."""
    test_jti = str(uuid.uuid4())
    test_user_id = "usr-test-persistence-001"
    future_exp = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()

    assert not is_token_revoked(test_jti)

    record_revoked_token(
        jti=test_jti,
        user_id=test_user_id,
        expires_at=future_exp,
        reason="admin_action",
    )

    # Check revocation directly
    assert is_token_revoked(test_jti)

    # Issue a token with this jti and verify FastAPI rejects it
    token = create_access_token({
        "sub": "usr-demo-000",
        "email": DEMO_CEO_EMAIL,
        "name": "Sarah Connor",
        "role": "CEO / Admin",
        "department": "Executive Leadership",
        "jti": test_jti,
    })

    res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 401
    assert "revoked" in res.json()["detail"].lower()


def test_cleanup_expired_revocations():
    """Verify expired revocation records can be safely purged without touching active ones."""
    past_exp = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
    future_exp = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()

    expired_jti = f"expired-{uuid.uuid4()}"
    active_jti = f"active-{uuid.uuid4()}"

    record_revoked_token(jti=expired_jti, user_id="usr-1", expires_at=past_exp)
    record_revoked_token(jti=active_jti, user_id="usr-2", expires_at=future_exp)

    assert is_token_revoked(expired_jti)
    assert is_token_revoked(active_jti)

    deleted_count = cleanup_expired_revocations()
    assert deleted_count >= 1

    assert not is_token_revoked(expired_jti)
    assert is_token_revoked(active_jti)


# ============================================================================
# 2. Rate Limiting Tests
# ============================================================================

def test_rate_limiting_enforcement():
    """Verify that exceeding configured rate limit triggers HTTP 429 with Retry-After header."""
    rate_key = "test_rate_endpoint:127.0.0.1"

    # Limit to 3 requests per 60 seconds
    allowed1, retry1 = default_rate_limiter.is_allowed(rate_key, "3/minute")
    allowed2, retry2 = default_rate_limiter.is_allowed(rate_key, "3/minute")
    allowed3, retry3 = default_rate_limiter.is_allowed(rate_key, "3/minute")
    allowed4, retry4 = default_rate_limiter.is_allowed(rate_key, "3/minute")

    assert allowed1 is True
    assert allowed2 is True
    assert allowed3 is True
    assert allowed4 is False
    assert retry4 > 0


def test_login_rate_limiting_endpoint(monkeypatch):
    """Verify that rapid repeated login calls return 429 when threshold is reached."""
    monkeypatch.setenv("RATE_LIMIT_LOGIN", "2/minute")

    # Call 1
    res1 = client.post("/api/auth/login", json={"email": "wrong@example.com", "password": "bad"})
    assert res1.status_code == 401

    # Call 2
    res2 = client.post("/api/auth/login", json={"email": "wrong@example.com", "password": "bad"})
    assert res2.status_code == 401

    # Call 3 - exceeds 2/minute
    res3 = client.post("/api/auth/login", json={"email": "wrong@example.com", "password": "bad"})
    assert res3.status_code == 429
    assert "Retry-After" in res3.headers
    assert int(res3.headers["Retry-After"]) >= 1


# ============================================================================
# 3. Client IP Resolution & Proxy Protection Tests
# ============================================================================

def test_client_ip_proxy_spoofing_defense(monkeypatch):
    """Verify that proxy headers (X-Forwarded-For) are ignored when untrusted."""
    from starlette.requests import Request

    class DummyClient:
        host = "192.168.1.50"

    # Default: TRUST_PROXY_HEADERS is false
    monkeypatch.setenv("TRUST_PROXY_HEADERS", "false")
    scope = {
        "type": "http",
        "client": ("192.168.1.50", 1234),
        "headers": [(b"x-forwarded-for", b"203.0.113.195")],
    }
    req = Request(scope)
    resolved_ip = get_client_ip(req)
    assert resolved_ip == "192.168.1.50"  # Ignores spoofed X-Forwarded-For

    # With TRUST_PROXY_HEADERS=true and host in TRUSTED_PROXIES
    monkeypatch.setenv("TRUST_PROXY_HEADERS", "true")
    monkeypatch.setenv("TRUSTED_PROXIES", "192.168.1.50,127.0.0.1")
    resolved_ip_trusted = get_client_ip(req)
    assert resolved_ip_trusted == "203.0.113.195"  # Trusted reverse proxy honored


# ============================================================================
# 4. Security Event Logging Tests
# ============================================================================

def test_security_audit_event_logging():
    """Verify structured security events are persisted to SQLite without credentials."""
    test_user_id = f"usr-{uuid.uuid4().hex[:8]}"

    log_id = record_security_event(
        event_type=SecurityEventType.LOGIN_SUCCESS,
        user_id=test_user_id,
        endpoint="POST /api/auth/login",
        detail="User logged in with password=SuperSecretPassword! and token=Bearer abc.def.ghi",
    )
    assert log_id.startswith("sec-")

    logs = get_security_audit_logs(limit=10, event_type=SecurityEventType.LOGIN_SUCCESS.value)
    matching = [log for log in logs if log["id"] == log_id]
    assert len(matching) == 1

    entry = matching[0]
    assert entry["event_type"] == SecurityEventType.LOGIN_SUCCESS.value
    assert entry["user_id"] == test_user_id
    # Ensure sensitive credentials were sanitized
    assert "SuperSecretPassword!" not in entry["detail"]
    assert "[REDACTED]" in entry["detail"]


def test_audit_logs_endpoint_rbac():
    """Verify that query audit logs endpoint requires CEO/Admin role."""
    # 1. Unauthenticated -> 401
    res_unauth = client.get("/api/auth/audit-logs")
    assert res_unauth.status_code == 401

    # 2. Operations Manager -> 403
    ops_login = client.post(
        "/api/auth/login",
        json={"email": DEMO_OPS_EMAIL, "password": DEMO_OPS_PW},
    )
    ops_token = ops_login.json()["access_token"]
    res_ops = client.get("/api/auth/audit-logs", headers={"Authorization": f"Bearer {ops_token}"})
    assert res_ops.status_code == 403

    # 3. CEO / Admin -> 200
    ceo_login = client.post(
        "/api/auth/login",
        json={"email": DEMO_CEO_EMAIL, "password": DEMO_CEO_PW},
    )
    ceo_token = ceo_login.json()["access_token"]
    res_ceo = client.get("/api/auth/audit-logs", headers={"Authorization": f"Bearer {ceo_token}"})
    assert res_ceo.status_code == 200
    assert isinstance(res_ceo.json(), list)


# ============================================================================
# 5. Security Configuration Validation Tests
# ============================================================================

def test_config_validation_development():
    """Verify development configuration passes with standard defaults."""
    os.environ["ENVIRONMENT"] = "development"
    os.environ["JWT_SECRET_KEY"] = "bizpulse_dev_jwt_secret_key_change_in_production_2026"
    os.environ["COOKIE_SECURE"] = "false"
    os.environ["ALLOW_REGISTRATION"] = "true"

    summary = validate_security_configuration()
    assert summary["environment"] == "development"
    assert summary["is_production"] is False


def test_config_validation_production_rejects_dev_secret(monkeypatch):
    """Verify that known dev secret is strictly rejected in production."""
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("JWT_SECRET_KEY", "bizpulse_dev_jwt_secret_key_change_in_production_2026")
    monkeypatch.setenv("COOKIE_SECURE", "true")
    monkeypatch.setenv("ALLOW_REGISTRATION", "false")

    with pytest.raises(SecurityConfigurationError) as exc_info:
        validate_security_configuration()
    assert "known development jwt_secret_key is strictly forbidden" in str(exc_info.value).lower()


def test_config_validation_production_requires_secure_cookie(monkeypatch):
    """Verify that COOKIE_SECURE=false is rejected in production."""
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("JWT_SECRET_KEY", "a_very_long_cryptographically_secure_random_key_2026_production")
    monkeypatch.setenv("COOKIE_SECURE", "false")
    monkeypatch.setenv("ALLOW_REGISTRATION", "false")

    with pytest.raises(SecurityConfigurationError) as exc_info:
        validate_security_configuration()
    assert "cookie_secure must be enabled" in str(exc_info.value).lower()


def test_config_validation_production_rejects_open_registration(monkeypatch):
    """Verify that ALLOW_REGISTRATION=true is rejected in production."""
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("JWT_SECRET_KEY", "a_very_long_cryptographically_secure_random_key_2026_production")
    monkeypatch.setenv("COOKIE_SECURE", "true")
    monkeypatch.setenv("ALLOW_REGISTRATION", "true")

    with pytest.raises(SecurityConfigurationError) as exc_info:
        validate_security_configuration()
    assert "allow_registration must be disabled" in str(exc_info.value).lower()


def test_config_validation_production_valid(monkeypatch):
    """Verify that compliant production configuration succeeds."""
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("JWT_SECRET_KEY", "a_very_long_cryptographically_secure_random_key_2026_production")
    monkeypatch.setenv("COOKIE_SECURE", "true")
    monkeypatch.setenv("ALLOW_REGISTRATION", "false")
    monkeypatch.setenv("JWT_ALGORITHM", "HS256")
    monkeypatch.setenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "60")

    summary = validate_security_configuration()
    assert summary["is_production"] is True
    assert summary["cookie_secure"] is True
    assert summary["allow_registration"] is False


# ============================================================================
# 6. AI Resource Protection & Input Size Validation Tests
# ============================================================================

def test_chat_message_length_limit():
    """Verify that chat messages exceeding 2000 characters are rejected with 400 or 422."""
    login_res = client.post(
        "/api/auth/login",
        json={"email": DEMO_CEO_EMAIL, "password": DEMO_CEO_PW},
    )
    token = login_res.json()["access_token"]

    oversized_message = "A" * 2500
    res = client.post(
        "/api/chat",
        headers={"Authorization": f"Bearer {token}"},
        json={"message": oversized_message, "history": []},
    )
    assert res.status_code in (400, 422)


def test_gemini_test_prompt_length_limit():
    """Verify that Gemini connectivity test prompt exceeding 1000 characters is rejected."""
    login_res = client.post(
        "/api/auth/login",
        json={"email": DEMO_CEO_EMAIL, "password": DEMO_CEO_PW},
    )
    token = login_res.json()["access_token"]

    oversized_prompt = "X" * 1500
    res = client.post(
        "/api/gemini/test",
        headers={"Authorization": f"Bearer {token}"},
        json={"prompt": oversized_prompt},
    )
    assert res.status_code == 400
    assert "1000 characters" in res.json()["detail"]


def test_investigation_anomaly_id_length_limit():
    """Verify that investigation anomaly_id exceeding 64 characters is rejected."""
    login_res = client.post(
        "/api/auth/login",
        json={"email": DEMO_CEO_EMAIL, "password": DEMO_CEO_PW},
    )
    token = login_res.json()["access_token"]

    oversized_id = "ANOMALY_" + "A" * 70
    res = client.post(
        "/api/investigate",
        headers={"Authorization": f"Bearer {token}"},
        json={"anomaly_id": oversized_id},
    )
    assert res.status_code == 400
    assert "64 characters" in res.json()["detail"]


def test_agent_orchestration_anomaly_id_length_limit():
    """Verify that agent run anomaly_id exceeding 64 characters is rejected."""
    login_res = client.post(
        "/api/auth/login",
        json={"email": DEMO_CEO_EMAIL, "password": DEMO_CEO_PW},
    )
    token = login_res.json()["access_token"]

    oversized_id = "ANOMALY_" + "B" * 70
    res = client.post(
        "/api/agents/run",
        headers={"Authorization": f"Bearer {token}"},
        json={"anomaly_id": oversized_id},
    )
    assert res.status_code == 400
    assert "64 characters" in res.json()["detail"]
