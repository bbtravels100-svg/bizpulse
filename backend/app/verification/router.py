from typing import Optional, Dict, Any, List
from fastapi import APIRouter, HTTPException, Query, Depends, status

from ..auth.permissions import Permission, require_permissions
from .models import (
    BaselineMetric,
    BaselineCaptureRequest,
    VerificationRunResponse,
    VerificationTriggerRequest,
    VerificationHistoryResponse,
    VerificationNoteCreateRequest,
    VerificationNoteResponse,
    ReopenInvestigationRequest,
)
from .service import (
    default_verification_service,
    VerificationNotFoundError,
    VerificationError,
    InvalidActionStateForVerificationError,
)
from ..actions.service import ActionNotFoundError

verification_router = APIRouter(prefix="/api/verification", tags=["Verification"])


@verification_router.post(
    "/baseline",
    response_model=BaselineMetric,
    status_code=status.HTTP_201_CREATED,
    summary="Capture or retrieve immutable baseline metrics for an action",
    dependencies=[Depends(require_permissions([Permission.VERIFICATION_RUN]))],
)
def capture_baseline_endpoint(req: BaselineCaptureRequest):
    """
    Capture baseline metrics for an approved business action.
    If a baseline already exists for this action, it is returned unchanged (baselines are immutable).
    """
    try:
        baseline = default_verification_service.capture_baseline_for_action(
            action_id=req.action_id,
            custom_req=req,
        )
        return baseline
    except ActionNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@verification_router.post(
    "/verify",
    response_model=VerificationRunResponse,
    status_code=status.HTTP_200_OK,
    summary="Trigger follow-up verification run for an action",
    dependencies=[Depends(require_permissions([Permission.VERIFICATION_RUN]))],
)
def verify_action_endpoint(req: VerificationTriggerRequest):
    """
    Execute follow-up verification for an action:
    - Compares current metrics against the captured baseline via deterministic Python math.
    - Determines quantitative outcome (Improved, Not Improved, Deteriorated, Inconclusive, Insufficient Data).
    - Enforces the rule that task completion does not equal problem resolution.
    - Generates Gemini follow-up interpretation and causal attribution.
    - Stores the verification run and updates the audit log.
    """
    try:
        run_result = default_verification_service.verify_action(req)
        return run_result
    except ActionNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except InvalidActionStateForVerificationError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@verification_router.get(
    "/results/{action_id}",
    response_model=VerificationRunResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve latest verification outcome for an action",
    dependencies=[Depends(require_permissions([Permission.VERIFICATION_VIEW]))],
)
def get_latest_verification_result(action_id: str):
    """Fetch the latest verification run result for a specified action."""
    try:
        return default_verification_service.get_latest_result(action_id)
    except VerificationNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@verification_router.get(
    "/history/{action_id}",
    response_model=VerificationHistoryResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve complete verification history, baseline, and notes for an action",
    dependencies=[Depends(require_permissions([Permission.VERIFICATION_VIEW]))],
)
def get_verification_history_endpoint(action_id: str):
    """Fetch complete chronological verification runs, baseline, and diagnostic notes."""
    try:
        return default_verification_service.get_verification_history(action_id)
    except VerificationNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@verification_router.post(
    "/notes",
    response_model=VerificationNoteResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a diagnostic or management note to a verification attempt",
    dependencies=[Depends(require_permissions([Permission.VERIFICATION_RUN]))],
)
def add_verification_note_endpoint(req: VerificationNoteCreateRequest):
    """Add a diagnostic observation, post-mortem note, or manager comment to a verification run."""
    try:
        return default_verification_service.add_verification_note(req)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@verification_router.post(
    "/reopen",
    status_code=status.HTTP_200_OK,
    summary="Reopen investigation after failed verification and create a new proposal",
    dependencies=[Depends(require_permissions([Permission.VERIFICATION_REOPEN]))],
)
def reopen_investigation_endpoint(req: ReopenInvestigationRequest):
    """
    Handle failed verification:
    - Flags the problem as unresolved.
    - Generates a secondary action proposal with recommended diagnostic steps.
    - Logs the reopening in the immutable audit log.
    """
    try:
        return default_verification_service.reopen_investigation(req)
    except ActionNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
