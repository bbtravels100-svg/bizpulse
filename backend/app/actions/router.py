from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, Depends, status

from ..auth.models import UserResponse
from ..auth.permissions import (
    Permission,
    require_permissions,
    check_task_resource_access,
)
from .models import (
    ActionStatus,
    ActionCreateRequest,
    ActionUpdateRequest,
    ActionApproveRequest,
    ActionRejectRequest,
    TaskStatusUpdateRequest,
    TaskAssignmentUpdateRequest,
    ProgressNoteCreateRequest,
    ActionResponse,
    ProgressNoteResponse,
    ActionHistoryResponse,
    ActionGenerateRequest,
)
from .service import (
    default_action_service,
    ActionNotFoundError,
    InvalidStatusTransitionError,
    ActionValidationError,
)
from ..agents.orchestrator import default_orchestrator
from ..services.gemini_service import GeminiAuthError, GeminiRateLimitError, GeminiServiceError

router = APIRouter(tags=["Action Management"])


# ============================================================================
# Action Proposals & Human Approval Endpoints
# ============================================================================

@router.post(
    "/api/actions/propose",
    response_model=ActionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create an Action Proposal",
    dependencies=[Depends(require_permissions([Permission.ACTION_PROPOSE]))],
)
def propose_action(payload: ActionCreateRequest):
    """Manually create a new action proposal in 'Pending Approval' status."""
    try:
        return default_action_service.create_action(payload)
    except ActionValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create action: {str(e)}")


@router.post(
    "/api/actions/generate",
    response_model=List[ActionResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Generate Action Proposals from AI Multi-Agent Orchestration",
    dependencies=[Depends(require_permissions([Permission.ACTION_PROPOSE]))],
)
def generate_actions_from_ai(payload: Optional[ActionGenerateRequest] = None):
    """
    Run the 4-agent orchestrator for an anomaly and automatically generate
    action proposals for human manager approval.
    """
    anomaly_id = payload.anomaly_id if payload and payload.anomaly_id else "ANOMALY_FUNNEL_MOBILE_001"
    try:
        # Run 4-agent pipeline
        orchestration = default_orchestrator.run(anomaly_id=anomaly_id)
        if orchestration.status == "failed":
            raise HTTPException(
                status_code=500,
                detail=f"Agent orchestration failed: {orchestration.stages.analyst.error or 'Pipeline error'}",
            )
        # Generate persistent proposals
        proposals = default_action_service.generate_proposals_from_orchestration(orchestration)
        return proposals
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except GeminiAuthError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except GeminiRateLimitError as e:
        raise HTTPException(status_code=429, detail=str(e))
    except GeminiServiceError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate actions: {str(e)}")


@router.get(
    "/api/actions/proposals",
    response_model=List[ActionResponse],
    summary="List Actions Pending Human Approval",
    dependencies=[Depends(require_permissions([Permission.ACTION_VIEW]))],
)
def list_proposals():
    """Retrieve all action proposals currently awaiting manager review and approval."""
    return default_action_service.list_proposals()


@router.get(
    "/api/actions",
    response_model=List[ActionResponse],
    summary="List Actions with Optional Filters",
    dependencies=[Depends(require_permissions([Permission.ACTION_VIEW]))],
)
def list_actions(
    status: Optional[ActionStatus] = Query(None, description="Filter by exact status"),
    active_only: bool = Query(False, description="Filter to active tasks (Approved, In Progress, Overdue, Completed)"),
    department: Optional[str] = Query(None, description="Filter by department name"),
    investigation_id: Optional[str] = Query(None, description="Filter by investigation reference"),
):
    """List action proposals and tasks with filtering."""
    return default_action_service.list_actions(
        status=status,
        active_only=active_only,
        department=department,
        investigation_id=investigation_id,
    )


@router.get(
    "/api/actions/{action_id}",
    response_model=ActionResponse,
    summary="Get Action Details by ID",
    dependencies=[Depends(require_permissions([Permission.ACTION_VIEW]))],
)
def get_action_details(action_id: str):
    """Fetch details of a single action or task."""
    try:
        return default_action_service.get_action(action_id)
    except ActionNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.patch(
    "/api/actions/{action_id}",
    response_model=ActionResponse,
    summary="Edit Action Proposal Before Approval",
    dependencies=[Depends(require_permissions([Permission.ACTION_EDIT]))],
)
def edit_proposal_before_approval(action_id: str, payload: ActionUpdateRequest):
    """
    Allow managers to edit a proposal's action, department, role, priority, or deadline
    before approving it. Rejects modifications on active or approved tasks.
    """
    try:
        return default_action_service.edit_proposal(action_id, payload)
    except ActionNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ActionValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post(
    "/api/actions/{action_id}/approve",
    response_model=ActionResponse,
    summary="Approve Action Proposal",
    dependencies=[Depends(require_permissions([Permission.ACTION_APPROVE]))],
)
def approve_action(action_id: str, payload: Optional[ActionApproveRequest] = None):
    """
    Manager approval gate: Transitions a proposal from 'Pending Approval' into 'Approved'.
    Only approved actions can enter the active task workflow. Restricted to CEO / Admin.
    """
    try:
        req = payload or ActionApproveRequest()
        return default_action_service.approve_action(action_id, req)
    except ActionNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except InvalidStatusTransitionError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post(
    "/api/actions/{action_id}/reject",
    response_model=ActionResponse,
    summary="Reject Action Proposal",
    dependencies=[Depends(require_permissions([Permission.ACTION_REJECT]))],
)
def reject_action(action_id: str, payload: ActionRejectRequest):
    """
    Manager rejection: Rejects an action proposal with a mandatory explanation reason.
    Restricted to CEO / Admin.
    """
    try:
        return default_action_service.reject_action(action_id, payload)
    except ActionNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except InvalidStatusTransitionError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============================================================================
# Task Management Endpoints (Active Workflow)
# ============================================================================

@router.get(
    "/api/tasks",
    response_model=List[ActionResponse],
    summary="List Active Workflow Tasks",
    dependencies=[Depends(require_permissions([Permission.TASK_VIEW]))],
)
def list_active_tasks():
    """Retrieve all approved, in progress, overdue, and completed tasks."""
    return default_action_service.list_active_tasks()


@router.patch(
    "/api/tasks/{action_id}/status",
    response_model=ActionResponse,
    summary="Update Task Execution Status",
)
def update_task_status(
    action_id: str,
    payload: TaskStatusUpdateRequest,
    current_user: UserResponse = Depends(require_permissions([Permission.TASK_STATUS_UPDATE])),
):
    """
    Update the lifecycle status of a task.
    Enforces valid transitions and resource-level authorization.
    """
    try:
        action = default_action_service.get_action(action_id)
        if not check_task_resource_access(current_user, action.responsible_department, action.suggested_owner_role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access forbidden: You cannot modify tasks outside your department ('{current_user.department}')",
            )
        return default_action_service.update_task_status(action_id, payload)
    except ActionNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except InvalidStatusTransitionError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.patch(
    "/api/tasks/{action_id}/assignment",
    response_model=ActionResponse,
    summary="Update Task Assignment & Deadlines",
    dependencies=[Depends(require_permissions([Permission.TASK_ASSIGN]))],
)
def update_task_assignment(action_id: str, payload: TaskAssignmentUpdateRequest):
    """Reassign task department, owner role, or adjust deadline."""
    try:
        return default_action_service.update_task_assignment(action_id, payload)
    except ActionNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ActionValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post(
    "/api/tasks/{action_id}/notes",
    response_model=ProgressNoteResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add Progress Note to Task",
)
def add_task_progress_note(
    action_id: str,
    payload: ProgressNoteCreateRequest,
    current_user: UserResponse = Depends(require_permissions([Permission.TASK_NOTE])),
):
    """Append a threaded progress update or observation to an active task."""
    try:
        action = default_action_service.get_action(action_id)
        if not check_task_resource_access(current_user, action.responsible_department, action.suggested_owner_role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access forbidden: You cannot add notes to tasks outside your department ('{current_user.department}')",
            )
        return default_action_service.add_progress_note(action_id, payload)
    except ActionNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get(
    "/api/tasks/{action_id}/history",
    response_model=ActionHistoryResponse,
    summary="View Task Audit History and Notes",
    dependencies=[Depends(require_permissions([Permission.TASK_VIEW]))],
)
def get_task_history(action_id: str):
    """Retrieve chronological audit log and progress notes for a task."""
    try:
        return default_action_service.get_action_history(action_id)
    except ActionNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get(
    "/api/actions/{action_id}/history",
    response_model=ActionHistoryResponse,
    summary="View Action Audit History and Notes (Alias)",
    dependencies=[Depends(require_permissions([Permission.TASK_VIEW]))],
)
def get_action_history(action_id: str):
    """Alias for /api/tasks/{action_id}/history."""
    return get_task_history(action_id)
