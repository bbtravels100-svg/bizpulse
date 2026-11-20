from fastapi import APIRouter, HTTPException, Depends

from ..auth.permissions import Permission, require_permissions
from ..auth.rate_limiter import rate_limit
from ..auth.audit import record_security_event, SecurityEventType
from ..services.gemini_service import (
    GeminiAuthError,
    GeminiRateLimitError,
    GeminiServiceError,
)
from .models import ChatRequest, ChatResponse
from .service import ChatError, handle_chat

router = APIRouter(tags=["AI Assistant"])


@router.post(
    "/api/chat",
    response_model=ChatResponse,
    summary="Conversational BizPulse AI",
    dependencies=[
        Depends(require_permissions([Permission.AI_CHAT])),
        Depends(rate_limit(limit_default="20/minute", env_var_name="RATE_LIMIT_CHAT", key_prefix="chat")),
    ],
)
def chat_endpoint(payload: ChatRequest):
    """
    Route a free-text message to existing BizPulse capabilities:
    investigation questions run the existing 4-role orchestrator; everything else is
    answered by Gemini grounded strictly in the Python analytics engine's output.
    Never executes actions: proposals/approvals use the existing /api/actions endpoints.
    Enforces payload size validation and abuse rate limiting.
    """
    if len(payload.message) > 2000:
        record_security_event(
            event_type=SecurityEventType.AI_PAYLOAD_LIMIT_EXCEEDED,
            detail=f"Chat message length ({len(payload.message)}) exceeds limit of 2000 characters",
        )
        raise HTTPException(
            status_code=400,
            detail="Message exceeds maximum allowed length of 2000 characters",
        )
    try:
        return handle_chat(payload)
    except ChatError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except GeminiAuthError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except GeminiRateLimitError as e:
        raise HTTPException(status_code=429, detail=str(e))
    except GeminiServiceError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat failed: {type(e).__name__}")
