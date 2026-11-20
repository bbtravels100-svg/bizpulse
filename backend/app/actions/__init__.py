"""
BizPulse Action Management Package (Phase 3B)
Handles action proposal generation from multi-agent orchestration,
human manager approval workflows, task state transitions, and persistent audit logs.
"""

from .models import (
    ActionStatus,
    ActionPriority,
    ALLOWED_TRANSITIONS,
    ActionBase,
    ActionCreateRequest,
    ActionUpdateRequest,
    ActionApproveRequest,
    ActionRejectRequest,
    TaskStatusUpdateRequest,
    TaskAssignmentUpdateRequest,
    ProgressNoteCreateRequest,
    ProgressNoteResponse,
    AuditLogEntry,
    ActionResponse,
    ActionHistoryResponse,
    ActionGenerateRequest,
)
from .database import get_db_connection, init_db, get_db_path
from .service import (
    ActionService,
    default_action_service,
    ActionServiceError,
    ActionNotFoundError,
    InvalidStatusTransitionError,
    ActionValidationError,
)
from .router import router as actions_router

__all__ = [
    "ActionStatus",
    "ActionPriority",
    "ALLOWED_TRANSITIONS",
    "ActionBase",
    "ActionCreateRequest",
    "ActionUpdateRequest",
    "ActionApproveRequest",
    "ActionRejectRequest",
    "TaskStatusUpdateRequest",
    "TaskAssignmentUpdateRequest",
    "ProgressNoteCreateRequest",
    "ProgressNoteResponse",
    "AuditLogEntry",
    "ActionResponse",
    "ActionHistoryResponse",
    "ActionGenerateRequest",
    "get_db_connection",
    "init_db",
    "get_db_path",
    "ActionService",
    "default_action_service",
    "ActionServiceError",
    "ActionNotFoundError",
    "InvalidStatusTransitionError",
    "ActionValidationError",
    "actions_router",
]
