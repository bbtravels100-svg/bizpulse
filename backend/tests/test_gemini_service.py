import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from app.main import app
from app.services.gemini_service import (
    GeminiServiceError,
    GeminiAuthError,
    GeminiRateLimitError,
    get_gemini_client,
    get_gemini_model_name,
    generate_text,
    verify_gemini_connectivity,
    _sanitize_error,
)


@pytest.fixture
def client():
    return TestClient(app)


def test_sanitize_error_redacts_api_key(monkeypatch):
    test_key = "SECRET_KEY_1234567890"
    monkeypatch.setenv("GEMINI_API_KEY", test_key)
    error_msg = f"API request failed with key {test_key} at endpoint."
    sanitized = _sanitize_error(error_msg)
    assert test_key not in sanitized
    assert "[REDACTED_API_KEY]" in sanitized


def test_missing_api_key_raises_auth_error(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    with pytest.raises(GeminiAuthError) as exc_info:
        get_gemini_client()
    assert "GEMINI_API_KEY is not configured" in str(exc_info.value)


def test_placeholder_api_key_raises_auth_error(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "your_gemini_api_key_here")
    with pytest.raises(GeminiAuthError) as exc_info:
        get_gemini_client()
    assert "GEMINI_API_KEY is not configured" in str(exc_info.value)


def test_get_gemini_model_name(monkeypatch):
    monkeypatch.setenv("GEMINI_MODEL", "gemini-3.8-flash")
    assert get_gemini_model_name() == "gemini-3.8-flash"


def test_generate_text_empty_prompt():
    with pytest.raises(ValueError) as exc_info:
        generate_text("   ")
    assert "Prompt cannot be empty" in str(exc_info.value)


def test_generate_text_mocked_success(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "mock_key_abc123")
    monkeypatch.setenv("GEMINI_MODEL", "gemini-3.8-flash")

    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = "Gemini connection successful."
    mock_client.models.generate_content.return_value = mock_response

    with patch("app.services.gemini_service.get_gemini_client", return_value=mock_client):
        result = generate_text("Hello")
        assert result == "Gemini connection successful."
        mock_client.models.generate_content.assert_called_once_with(
            model="gemini-3.8-flash",
            contents="Hello",
        )


def test_verify_gemini_connectivity_structure(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "mock_key_abc123")
    monkeypatch.setenv("GEMINI_MODEL", "gemini-3.8-flash")

    with patch("app.services.gemini_service.generate_text", return_value="Gemini connection successful."):
        result = verify_gemini_connectivity()
        assert result["connection_status"] == "connected"
        assert result["model_name"] == "gemini-3.8-flash"
        assert result["response"] == "Gemini connection successful."
        assert isinstance(result["response_time_ms"], float)
        assert result["response_time_ms"] >= 0.0


def test_api_gemini_test_endpoint_mocked(client):
    mock_result = {
        "connection_status": "connected",
        "model_name": "gemini-3.8-flash",
        "response": "Gemini connection successful.",
        "response_time_ms": 320.45,
    }
    with patch("app.main.verify_gemini_connectivity", return_value=mock_result):
        resp = client.post("/api/gemini/test", json={"prompt": "Ping"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["connection_status"] == "connected"
        assert data["model_name"] == "gemini-3.8-flash"
        assert data["response"] == "Gemini connection successful."
        assert data["response_time_ms"] == 320.45
        # Ensure no secrets in output
        assert "key" not in data
        assert "api_key" not in data


def test_api_gemini_test_endpoint_auth_error(client):
    with patch(
        "app.main.verify_gemini_connectivity",
        side_effect=GeminiAuthError("GEMINI_API_KEY is not configured"),
    ):
        resp = client.post("/api/gemini/test", json={})
        assert resp.status_code == 401
        assert "GEMINI_API_KEY is not configured" in resp.json()["detail"]


def test_api_gemini_test_endpoint_service_error(client):
    with patch(
        "app.main.verify_gemini_connectivity",
        side_effect=GeminiServiceError("Upstream API error"),
    ):
        resp = client.post("/api/gemini/test", json={})
        assert resp.status_code == 502
        assert "Upstream API error" in resp.json()["detail"]
