import os
import time
import json
from typing import Optional, Dict, Any
from google import genai
from google.genai import types
from google.genai import errors as genai_errors


class GeminiServiceError(Exception):
    """Base exception for Gemini service operations."""
    pass


class GeminiAuthError(GeminiServiceError):
    """Exception raised when Gemini API key is missing or invalid."""
    pass


class GeminiRateLimitError(GeminiServiceError):
    """Exception raised when API rate limits are exceeded."""
    pass


class GeminiNetworkError(GeminiServiceError):
    """Exception raised on network failure connecting to Gemini."""
    pass


def _sanitize_error(msg: str) -> str:
    """Ensure no API key or secret token is ever exposed in error messages."""
    api_key = os.getenv("GEMINI_API_KEY")
    if api_key and api_key in msg:
        msg = msg.replace(api_key, "[REDACTED_API_KEY]")
    return msg


def get_gemini_client() -> genai.Client:
    """
    Retrieve and validate the Gemini API client.
    Reads GEMINI_API_KEY from environment variables.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or not api_key.strip() or api_key == "your_gemini_api_key_here":
        raise GeminiAuthError(
            "GEMINI_API_KEY is not configured. Please set a valid key in backend/.env"
        )
    return genai.Client(api_key=api_key.strip())


def get_gemini_model_name() -> str:
    """
    Retrieve configured Gemini model name from environment variables.
    Defaults to 'gemini-3.1-flash-lite'.
    """
    return os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite").strip()


def generate_text(prompt: str, model_name: Optional[str] = None) -> str:
    """
    Send a prompt to Gemini and return the generated text response.
    Catches and wraps SDK exceptions without leaking credentials.
    """
    if not prompt or not prompt.strip():
        raise ValueError("Prompt cannot be empty.")

    model = model_name or get_gemini_model_name()
    client = get_gemini_client()

    try:
        response = client.models.generate_content(
            model=model,
            contents=prompt,
        )
        if not response or not hasattr(response, "text") or response.text is None:
            raise GeminiServiceError("Gemini returned an empty or unparseable response.")
        return response.text.strip()
    except genai_errors.APIError as e:
        safe_msg = _sanitize_error(str(e))
        code = getattr(e, "code", None)
        if code in (401, 403):
            raise GeminiAuthError(f"Authentication failed with Gemini API: {safe_msg}") from e
        elif code == 429:
            raise GeminiRateLimitError(f"Gemini API rate limit exceeded: {safe_msg}") from e
        raise GeminiServiceError(f"Gemini API error ({code}): {safe_msg}") from e
    except Exception as e:
        safe_msg = _sanitize_error(str(e))
        raise GeminiNetworkError(f"Failed to communicate with Gemini API: {safe_msg}") from e


def generate_json(prompt: str, model_name: Optional[str] = None) -> Dict[str, Any]:
    """
    Send a prompt to Gemini requesting structured JSON output and parse the result into a dict.
    Uses response_mime_type="application/json" to ensure strict JSON conformance.
    """
    if not prompt or not prompt.strip():
        raise ValueError("Prompt cannot be empty.")

    model = model_name or get_gemini_model_name()
    client = get_gemini_client()

    try:
        cfg = types.GenerateContentConfig(response_mime_type="application/json")
        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config=cfg,
        )
        if not response or not hasattr(response, "text") or not response.text:
            raise GeminiServiceError("Gemini returned an empty response.")

        parsed = json.loads(response.text.strip())
        return parsed
    except json.JSONDecodeError as e:
        raise GeminiServiceError(f"Failed to parse Gemini response as JSON: {e}") from e
    except genai_errors.APIError as e:
        safe_msg = _sanitize_error(str(e))
        code = getattr(e, "code", None)
        if code in (401, 403):
            raise GeminiAuthError(f"Authentication failed with Gemini API: {safe_msg}") from e
        elif code == 429:
            raise GeminiRateLimitError(f"Gemini API rate limit exceeded: {safe_msg}") from e
        raise GeminiServiceError(f"Gemini API error ({code}): {safe_msg}") from e
    except Exception as e:
        safe_msg = _sanitize_error(str(e))
        raise GeminiNetworkError(f"Failed to communicate with Gemini API: {safe_msg}") from e


def verify_gemini_connectivity(
    prompt: str = "You are connected to BizPulse. Reply with: Gemini connection successful.",
    model_name: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Perform an end-to-end connectivity test against the Gemini API.
    Measures latency and returns structured status details.
    """
    model = model_name or get_gemini_model_name()
    t0 = time.perf_counter()

    try:
        response_text = generate_text(prompt=prompt, model_name=model)
        elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
        return {
            "connection_status": "connected",
            "model_name": model,
            "response": response_text,
            "response_time_ms": elapsed_ms,
        }
    except GeminiServiceError:
        raise
    except Exception as e:
        safe_msg = _sanitize_error(str(e))
        raise GeminiServiceError(f"Connectivity test failed: {safe_msg}") from e


# Backward compatibility alias
test_gemini_connection = verify_gemini_connectivity
