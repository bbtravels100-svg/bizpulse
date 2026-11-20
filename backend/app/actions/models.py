from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator


class ActionStatus(str, Enum):
    PENDING_APPROVAL = "Pending Approval"
    APPROVED = "Approved"
    IN_PROGRESS = "In Progress"
    COMPLETED = "Completed"
    REJECTED = "Rejected"
    OVERDUE = "Overdue"


class ActionPriority(str, Enum):
    CRITICAL = "Critical"
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


# Allowed status transitions
ALLOWED_TRANSITIONS: Dict[ActionStatus, List[ActionStatus]] = {
    ActionStatus.PENDING_APPROVAL: [ActionStatus.APPROVED, ActionStatus.REJECTED],
    ActionStatus.APPROVED: [ActionStatus.IN_PROGRESS, ActionStatus.REJECTED, ActionStatus.OVERDUE],
    ActionStatus.IN_PROGRESS: [ActionStatus.COMPLETED, ActionStatus.OVERDUE],
    ActionStatus.OVERDUE: [ActionStatus.IN_PROGRESS, ActionStatus.COMPLETED],
    ActionStatus.COMPLETED: [],  # Terminal
    ActionStatus.REJECTED: [],   # Terminal
}


class ActionBase(BaseModel):
    problem_description: str = Field(description="Description of the diagnosed business problem")
    recommended_action: str = Field(description="Concrete recommended action step")
    responsible_department: str = Field(description="Department accountable for remediation")
    suggested_owner_role: str = Field(description="Functional team or role title (no personal employee names)")
    priority: ActionPriority = Field(default=ActionPriority.MEDIUM, description="Task urgency level")
    suggested_deadline: str = Field(description="Target completion deadline (ISO timestamp or YYYY-MM-DD)")
    expected_outcome: str = Field(description="Business outcome expected upon successful resolution")
    verification_criteria: str = Field(description="Measurable criteria or metric used to verify success")


class ActionCreateRequest(ActionBase):
    investigation_id: str = Field(description="Traceable investigation or orchestration ID")
    anomaly_id: str = Field(description="Source anomaly identifier")


class ActionUpdateRequest(BaseModel):
    recommended_action: Optional[str] = None
    responsible_department: Optional[str] = None
    suggested_owner_role: Optional[str] = None
    priority: Optional[ActionPriority] = None
    suggested_deadline: Optional[str] = None
    expected_outcome: Optional[str] = None
    verification_criteria: Optional[str] = None


class ActionApproveRequest(BaseModel):
    approver: Optional[str] = "Business Manager"
    notes: Optional[str] = None


class ActionRejectRequest(BaseModel):
    reason: str = Field(min_length=3, description="Mandatory reason explaining why the action was rejected")
    rejected_by: Optional[str] = "Business Manager"


class TaskStatusUpdateRequest(BaseModel):
    new_status: ActionStatus
    notes: Optional[str] = None
    completion_details: Optional[str] = None


class TaskAssignmentUpdateRequest(BaseModel):
    responsible_department: Optional[str] = None
    suggested_owner_role: Optional[str] = None
    suggested_deadline: Optional[str] = None
    reason: Optional[str] = None


class ProgressNoteCreateRequest(BaseModel):
    note: str = Field(min_length=1, description="Progress update or observation")
    author: Optional[str] = "Manager"


class ProgressNoteResponse(BaseModel):
    id: int
    action_id: str
    note: str
    author: str
    created_at: str


class AuditLogEntry(BaseModel):
    id: int
    action_id: str
    action_type: str
    previous_value: Optional[str] = None
    new_value: Optional[str] = None
    details: Optional[str] = None
    timestamp: str


class ActionResponse(BaseModel):
    id: str
    investigation_id: str
    anomaly_id: str
    problem_description: str
    recommended_action: str
    responsible_department: str
    suggested_owner_role: str
    priority: ActionPriority
    suggested_deadline: str
    expected_outcome: str
    verification_criteria: str
    status: ActionStatus
    rejection_reason: Optional[str] = None
    completion_details: Optional[str] = None
    completed_at: Optional[str] = None
    created_at: str
    updated_at: str


class ActionHistoryResponse(BaseModel):
    action: ActionResponse
    notes: List[ProgressNoteResponse]
    audit_log: List[AuditLogEntry]


class ActionGenerateRequest(BaseModel):
    anomaly_id: Optional[str] = "ANOMALY_FUNNEL_MOBILE_001"
    investigation_id: Optional[str] = None
