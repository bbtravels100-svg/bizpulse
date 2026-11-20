import pytest
from app.main import app
from app.auth.router import get_current_user
from app.auth.models import UserResponse

DEFAULT_TEST_ADMIN = UserResponse(
    id="usr-test-admin-001",
    email="test.admin@bizpulse.internal",
    name="Test Admin CEO",
    role="CEO / Admin",
    department="Executive Leadership",
    is_active=True,
    created_at="2026-11-20T00:00:00Z",
    updated_at="2026-11-20T00:00:00Z",
)


@pytest.fixture(autouse=True)
def setup_test_auth_context(request):
    """
    Ensure backwards compatibility for pre-Phase 6 test suites by providing
    an authenticated admin context.
    RBAC and Auth test suites (test_auth.py, test_rbac.py) explicitly bypass
    this override to test raw unauthenticated 401s, 403s, and role boundaries.
    """
    module_name = request.module.__name__
    is_security_suite = any(
        target in module_name for target in (
            "test_auth",
            "test_rbac",
            "test_advanced_security",
            "test_security",
            "test_database_reliability",
            "test_observability",
            "test_production_hardening",
            "test_cors",
            "test_ci_cd",
        )
    )

    if is_security_suite:
        # Do not override for security test suites: test real headers, cookies, and 401/403 rejections
        if get_current_user in app.dependency_overrides:
            del app.dependency_overrides[get_current_user]
        yield
        if get_current_user in app.dependency_overrides:
            del app.dependency_overrides[get_current_user]
    else:
        # Provide authenticated admin context for legacy tests
        app.dependency_overrides[get_current_user] = lambda: DEFAULT_TEST_ADMIN
        yield
        if get_current_user in app.dependency_overrides:
            del app.dependency_overrides[get_current_user]
