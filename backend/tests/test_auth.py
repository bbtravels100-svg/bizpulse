import os
import uuid
import pytest
from datetime import timedelta
from fastapi.testclient import TestClient

from app.main import app
from app.auth.database import (
    init_auth_db,
    DEMO_USER_EMAIL,
    DEMO_USER_PLAIN_PW,
    DEMO_USER_NAME,
)
from app.auth.security import (
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token,
    TokenExpiredError,
    InvalidTokenError,
)
from app.auth.service import default_auth_service, InvalidCredentialsError


@pytest.fixture(autouse=True)
def setup_auth():
    """Ensure auth database is initialized and seeded before tests run."""
    init_auth_db()


@pytest.fixture
def client():
    return TestClient(app)


# ─── 1. Password Hashing & Verification Tests (Argon2id) ───────────────

def test_argon2id_password_hashing():
    """Verify passwords are secure and properly hashed with Argon2id."""
    password = "SuperSecretPassword2026!"
    hashed = hash_password(password)

    assert hashed != password
    assert "$argon2id$" in hashed
    assert verify_password(password, hashed) is True
    assert verify_password("WrongPassword!", hashed) is False


def test_argon2id_salts_differ():
    """Verify identical passwords produce different salt hashes."""
    password = "SamePassword123!"
    h1 = hash_password(password)
    h2 = hash_password(password)
    assert h1 != h2
    assert verify_password(password, h1) is True
    assert verify_password(password, h2) is True


# ─── 2. JWT Generation & Expiration Tests ──────────────────────────────

def test_jwt_generation_and_decode():
    """Verify JWT access tokens encode and decode subject and custom claims."""
    payload = {"sub": "usr-test-123", "email": "test@bizpulse.internal", "role": "CEO"}
    token = create_access_token(payload, expires_delta=timedelta(minutes=15))

    decoded = decode_access_token(token)
    assert decoded["sub"] == "usr-test-123"
    assert decoded["email"] == "test@bizpulse.internal"
    assert decoded["role"] == "CEO"
    assert "exp" in decoded
    assert "iat" in decoded


def test_jwt_expired_token_raises_error():
    """Verify expired tokens are rejected with TokenExpiredError."""
    payload = {"sub": "usr-expired", "email": "expired@bizpulse.internal"}
    # Create token already expired 1 minute ago
    expired_token = create_access_token(payload, expires_delta=timedelta(minutes=-1))

    with pytest.raises(TokenExpiredError):
        decode_access_token(expired_token)


def test_jwt_invalid_signature_raises_error():
    """Verify tampered or invalid tokens raise InvalidTokenError."""
    payload = {"sub": "usr-valid"}
    token = create_access_token(payload)

    # Tamper with token payload
    tampered = token[:-4] + "abcd"
    with pytest.raises(InvalidTokenError):
        decode_access_token(tampered)


# ─── 3. Login Endpoint Tests ───────────────────────────────────────────

def test_login_valid_credentials(client):
    """Test successful login with seeded demo credentials."""
    response = client.post(
        "/api/auth/login",
        json={"email": DEMO_USER_EMAIL, "password": DEMO_USER_PLAIN_PW},
    )
    assert response.status_code == 200
    data = response.json()

    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["expires_in_seconds"] > 0
    assert data["user"]["email"] == DEMO_USER_EMAIL.lower()
    assert data["user"]["name"] == DEMO_USER_NAME
    assert "password_hash" not in data["user"]
    assert "password" not in data["user"]

    # Verify HttpOnly cookie is set
    assert "access_token" in response.cookies
    set_cookie_header = response.headers.get("set-cookie", "")
    assert "HttpOnly" in set_cookie_header or "httponly" in set_cookie_header


def test_login_invalid_password(client):
    """Test login failure with wrong password returns generic 401."""
    response = client.post(
        "/api/auth/login",
        json={"email": DEMO_USER_EMAIL, "password": "WrongPassword123!"},
    )
    assert response.status_code == 401
    data = response.json()
    assert data["detail"] == "Invalid email or password"


def test_login_nonexistent_email(client):
    """Test login failure with nonexistent email returns identical generic 401."""
    response = client.post(
        "/api/auth/login",
        json={"email": "nobody@doesnotexist.com", "password": "AnyPassword123!"},
    )
    assert response.status_code == 401
    data = response.json()
    assert data["detail"] == "Invalid email or password"


def test_login_case_insensitive_email(client):
    """Test email is normalized to lowercase."""
    response = client.post(
        "/api/auth/login",
        json={"email": DEMO_USER_EMAIL.upper(), "password": DEMO_USER_PLAIN_PW},
    )
    assert response.status_code == 200
    assert response.json()["user"]["email"] == DEMO_USER_EMAIL.lower()


# ─── 4. Protected Route & Current User Tests (/api/auth/me) ────────────

def test_auth_me_with_bearer_token(client):
    """Test /api/auth/me succeeds with valid Authorization Bearer header."""
    login_res = client.post(
        "/api/auth/login",
        json={"email": DEMO_USER_EMAIL, "password": DEMO_USER_PLAIN_PW},
    )
    token = login_res.json()["access_token"]

    response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == DEMO_USER_EMAIL.lower()
    assert data["name"] == DEMO_USER_NAME
    assert "password_hash" not in data


def test_auth_me_with_cookie(client):
    """Test /api/auth/me succeeds with HttpOnly cookie without Bearer header."""
    # First login to establish cookie session
    login_res = client.post(
        "/api/auth/login",
        json={"email": DEMO_USER_EMAIL, "password": DEMO_USER_PLAIN_PW},
    )
    assert login_res.status_code == 200

    # TestClient automatically preserves cookies
    response = client.get("/api/auth/me")
    assert response.status_code == 200
    assert response.json()["email"] == DEMO_USER_EMAIL.lower()


def test_auth_me_missing_token_returns_401(client):
    """Test accessing protected route without token returns 401."""
    # Create fresh client without cookies
    fresh_client = TestClient(app)
    response = fresh_client.get("/api/auth/me")
    assert response.status_code == 401
    assert "Authentication required" in response.json()["detail"]


def test_auth_me_invalid_token_returns_401(client):
    """Test accessing protected route with invalid token returns 401."""
    response = client.get(
        "/api/auth/me",
        headers={"Authorization": "Bearer invalid.garbage.jwt.token"},
    )
    assert response.status_code == 401
    assert "Invalid authentication token" in response.json()["detail"]


def test_auth_me_expired_token_returns_401(client):
    """Test accessing protected route with expired token returns 401 with session expired detail."""
    payload = {"sub": "usr-demo-001", "email": DEMO_USER_EMAIL}
    expired_token = create_access_token(payload, expires_delta=timedelta(minutes=-5))

    response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {expired_token}"},
    )
    assert response.status_code == 401
    assert "expired" in response.json()["detail"].lower()


# ─── 5. Logout Tests ───────────────────────────────────────────────────

def test_logout_clears_cookie(client):
    """Test logout endpoint deletes access_token cookie."""
    # Login first
    client.post(
        "/api/auth/login",
        json={"email": DEMO_USER_EMAIL, "password": DEMO_USER_PLAIN_PW},
    )
    assert "access_token" in client.cookies

    # Logout
    logout_res = client.post("/api/auth/logout")
    assert logout_res.status_code == 200
    assert logout_res.json()["message"] == "Successfully logged out"


# ─── 6. Controlled Provisioning Tests ──────────────────────────────────

def test_provision_user_with_valid_key(client):
    """Test controlled provisioning of a new user account."""
    new_email = f"finance.lead.{uuid.uuid4().hex[:6]}@bizpulse.internal"
    res = client.post(
        "/api/auth/provision",
        json={
            "email": new_email,
            "password": "SecurePassword2026!",
            "name": "Jordan Lee",
            "role": "Finance Analyst",
            "department": "Finance",
            "provisioning_key": "bizpulse_demo_provisioning_key_2026",
        },
    )
    assert res.status_code == 201
    data = res.json()
    assert data["email"] == new_email
    assert data["name"] == "Jordan Lee"
    assert "password_hash" not in data

    # Verify newly provisioned user can log in
    login_res = client.post(
        "/api/auth/login",
        json={"email": new_email, "password": "SecurePassword2026!"},
    )
    assert login_res.status_code == 200
    assert login_res.json()["user"]["name"] == "Jordan Lee"


def test_provision_duplicate_email_rejected(client):
    """Test provisioning with existing email returns 409 Conflict."""
    res = client.post(
        "/api/auth/provision",
        json={
            "email": DEMO_USER_EMAIL,
            "password": "AnotherPassword2026!",
            "name": "Duplicate User",
            "provisioning_key": "bizpulse_demo_provisioning_key_2026",
        },
    )
    assert res.status_code == 409
    assert "already exists" in res.json()["detail"]


def test_provision_short_password_rejected(client):
    """Test password shorter than 8 characters is rejected by validation."""
    res = client.post(
        "/api/auth/provision",
        json={
            "email": "short@bizpulse.internal",
            "password": "short",
            "name": "Short PW User",
        },
    )
    assert res.status_code == 422
