import json
import logging
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.observability.correlation import (
    generate_correlation_id,
    validate_correlation_id,
    set_correlation_id,
    get_correlation_id,
)
from app.observability.logging import (
    JsonLogFormatter,
    redact_sensitive_string,
)
from app.observability.metrics import (
    metrics_collector,
    normalize_metric_route,
)
from app.observability.diagnostics import (
    check_db_health,
    check_datasets_health,
    check_gemini_health,
    run_operational_diagnostics,
)

from app.auth.rate_limiter import default_rate_limiter
from app.auth.security import create_access_token

client = TestClient(app)

DEMO_CEO_EMAIL = "ceo.sarah@bizpulse.internal"
DEMO_OPS_EMAIL = "alex.morgan@bizpulse.internal"


@pytest.fixture(autouse=True)
def clean_state():
    """Ensure clean unauthenticated client cookie state and reset rate limiter for every test."""
    default_rate_limiter.reset()
    client.cookies.clear()
    yield
    default_rate_limiter.reset()
    client.cookies.clear()


def get_test_token(role: str, email: str, user_id: str) -> str:
    """Generate a valid signed JWT access token for testing."""
    return create_access_token({
        "sub": user_id,
        "email": email,
        "name": "Test User",
        "role": role,
        "department": "Operations",
    })


# ============================================================================
# 1. Correlation ID & Formatting Tests
# ============================================================================

def test_generate_correlation_id_format():
    """Verify generated correlation ID has expected prefix and length."""
    cid = generate_correlation_id()
    assert cid.startswith("corr-")
    assert len(cid) >= 16


def test_validate_correlation_id():
    """Verify valid and invalid incoming correlation IDs."""
    # Valid
    valid_id = "corr-test-12345678"
    assert validate_correlation_id(valid_id) == valid_id

    # Invalid: dangerous characters
    assert validate_correlation_id("corr-test;<script>") is None
    assert validate_correlation_id("corr-test space") is None
    # Invalid: too short
    assert validate_correlation_id("short") is None
    # Invalid: too long (>64 chars)
    assert validate_correlation_id("c" * 70) is None
    # Invalid: None or empty
    assert validate_correlation_id(None) is None
    assert validate_correlation_id("") is None


def test_response_correlation_headers_and_propagation():
    """Verify X-Correlation-ID header propagation in HTTP requests."""
    # 1. Without client-supplied ID: generates fresh ID and returns it
    res1 = client.get("/api/health")
    assert res1.status_code == 200
    cid1 = res1.headers.get("X-Correlation-ID")
    assert cid1 is not None
    assert cid1.startswith("corr-")

    # 2. With valid client-supplied ID: echoes it back
    custom_cid = "corr-client-custom-98765432"
    res2 = client.get("/api/health", headers={"X-Correlation-ID": custom_cid})
    assert res2.status_code == 200
    assert res2.headers.get("X-Correlation-ID") == custom_cid

    # 3. With invalid client-supplied ID: replaces it with a valid generated one
    res3 = client.get("/api/health", headers={"X-Correlation-ID": "bad!@#$"})
    assert res3.status_code == 200
    cid3 = res3.headers.get("X-Correlation-ID")
    assert cid3 != "bad!@#$"
    assert cid3.startswith("corr-")


def test_json_log_formatter_output():
    """Verify JsonLogFormatter produces valid JSON with required observability fields."""
    formatter = JsonLogFormatter()
    record = logging.LogRecord(
        name="bizpulse.test",
        level=logging.INFO,
        pathname="test.py",
        lineno=10,
        msg="Operational test event for order",
        args=(),
        exc_info=None,
    )
    record.correlation_id = "corr-test-11223344"
    record.method = "POST"
    record.endpoint = "/api/actions/proposals"
    record.status_code = 200
    record.duration_ms = 45.2

    output = formatter.format(record)
    parsed = json.loads(output)

    assert parsed["level"] == "INFO"
    assert parsed["logger"] == "bizpulse.test"
    assert parsed["message"] == "Operational test event for order"
    assert parsed["correlation_id"] == "corr-test-11223344"
    assert parsed["method"] == "POST"
    assert parsed["endpoint"] == "/api/actions/proposals"
    assert parsed["status_code"] == 200
    assert parsed["duration_ms"] == 45.2
    assert "timestamp" in parsed


def test_sensitive_data_redaction():
    """Verify that credentials, passwords, JWTs, and API keys are redacted."""
    raw = (
        "User logged in with password='SuperSecretPassword123' and "
        "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIn0.signature "
        "and api_key=AQ.Ab8RN6IOtcRNo and access_token=my_secret_token"
    )
    sanitized = redact_sensitive_string(raw)

    assert "SuperSecretPassword123" not in sanitized
    assert "password=[REDACTED]" in sanitized
    assert "Bearer [REDACTED]" in sanitized
    assert "api_key=[REDACTED]" in sanitized
    assert "access_token=[REDACTED]" in sanitized


# ============================================================================
# 2. Health Monitoring Tests
# ============================================================================

def test_public_health_endpoint_minimal_and_safe():
    """Verify public health endpoint returns only minimal metadata without leaking internal secrets."""
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()

    # Allowed public fields
    assert data["status"] == "healthy"
    assert data["service"] == "BizPulse API"
    assert "version" in data
    assert "timestamp" in data
    assert "uptime_seconds" in data

    # Prohibited leak fields
    assert "database_path" not in data
    assert "db" not in data
    assert "api_key" not in data
    assert "secrets" not in data
    assert "environment" not in data


def test_protected_diagnostics_rbac():
    """Verify RBAC restrictions on /api/admin/diagnostics."""
    # 1. Unauthenticated -> 401
    res_unauth = client.get("/api/admin/diagnostics")
    assert res_unauth.status_code == 401

    # 2. Operations Manager -> 403 (CEO/Admin Only)
    ops_token = get_test_token("Operations Manager", DEMO_OPS_EMAIL, "usr-demo-001")
    res_ops = client.get(
        "/api/admin/diagnostics",
        headers={"Authorization": f"Bearer {ops_token}"},
    )
    assert res_ops.status_code == 403

    # 3. CEO / Admin -> 200
    ceo_token = get_test_token("CEO / Admin", DEMO_CEO_EMAIL, "usr-demo-000")
    res_ceo = client.get(
        "/api/admin/diagnostics",
        headers={"Authorization": f"Bearer {ceo_token}"},
    )
    assert res_ceo.status_code == 200
    data = res_ceo.json()

    assert data["status"] in ("healthy", "degraded")
    assert "uptime_seconds" in data
    assert "database" in data["subsystems"]
    assert "datasets" in data["subsystems"]
    assert "ai_gemini" in data["subsystems"]
    assert data["subsystems"]["database"]["available"] is True


def test_diagnostics_subsystem_checks():
    """Verify individual diagnostic functions operate without throwing unhandled exceptions."""
    db_res = check_db_health()
    assert "status" in db_res
    assert "available" in db_res

    ds_res = check_datasets_health()
    assert "status" in ds_res
    assert "available" in ds_res

    ai_res = check_gemini_health()
    assert "status" in ai_res
    assert "available" in ai_res


# ============================================================================
# 3. Operational Metrics Tests
# ============================================================================

def test_metrics_route_normalization():
    """Verify dynamic IDs in paths are normalized to prevent label cardinality explosion."""
    assert normalize_metric_route("/api/overview") == "/api/overview"
    assert normalize_metric_route("/api/actions/tasks/act-12345/status") == "/api/actions/tasks/{id}/status"
    assert normalize_metric_route("/api/users/usr-abcdef123456/profile") == "/api/users/{id}/profile"
    assert normalize_metric_route("/api/items/12345678-1234-1234-1234-123456789abc") == "/api/items/{id}"


def test_admin_metrics_endpoint_rbac_and_prometheus_format():
    """Verify RBAC and standard Prometheus exposition format on /api/admin/metrics."""
    # 1. Unauthenticated -> 401
    res_unauth = client.get("/api/admin/metrics")
    assert res_unauth.status_code == 401

    # 2. Operations Manager -> 403
    ops_token = get_test_token("Operations Manager", DEMO_OPS_EMAIL, "usr-demo-001")
    res_ops = client.get(
        "/api/admin/metrics",
        headers={"Authorization": f"Bearer {ops_token}"},
    )
    assert res_ops.status_code == 403

    # 3. CEO / Admin -> 200 with Prometheus text format
    ceo_token = get_test_token("CEO / Admin", DEMO_CEO_EMAIL, "usr-demo-000")
    res_ceo = client.get(
        "/api/admin/metrics",
        headers={"Authorization": f"Bearer {ceo_token}"},
    )
    assert res_ceo.status_code == 200
    assert "text/plain" in res_ceo.headers.get("content-type", "")

    body = res_ceo.text
    assert "# HELP bizpulse_http_requests_total" in body
    assert "# TYPE bizpulse_http_requests_total counter" in body
    assert "# HELP bizpulse_http_request_duration_seconds" in body
    assert "# HELP bizpulse_app_uptime_seconds" in body
    assert "# HELP bizpulse_rate_limit_rejections_total" in body
    assert "# HELP bizpulse_active_tasks_count" in body


def test_error_response_contains_correlation_id():
    """Verify error responses include the correlation ID."""
    res = client.get("/api/nonexistent-route-404")
    assert res.status_code == 404
    data = res.json()
    assert "correlation_id" in data
    assert res.headers.get("X-Correlation-ID") == data["correlation_id"]
