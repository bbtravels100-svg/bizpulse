// ============================================================
// BizPulse Frontend — Action Management Types
// Matches backend/app/actions/models.py
// ============================================================

export type ActionStatus =
  | 'Pending Approval'
  | 'Approved'
  | 'In Progress'
  | 'Completed'
  | 'Rejected'
  | 'Overdue';

export type ActionPriority = 'Critical' | 'High' | 'Medium' | 'Low';

export const ALLOWED_TRANSITIONS: Record<ActionStatus, ActionStatus[]> = {
  'Pending Approval': ['Approved', 'Rejected'],
  'Approved': ['In Progress', 'Rejected', 'Overdue'],
  'In Progress': ['Completed', 'Overdue'],
  'Overdue': ['In Progress', 'Completed'],
  'Completed': [],
  'Rejected': [],
};

export interface ActionResponse {
  id: string;
  investigation_id: string;
  anomaly_id: string;
  problem_description: string;
  recommended_action: string;
  responsible_department: string;
  suggested_owner_role: string;
  priority: ActionPriority;
  suggested_deadline: string;
  expected_outcome: string;
  verification_criteria: string;
  status: ActionStatus;
  rejection_reason?: string | null;
  completion_details?: string | null;
  completed_at?: string | null;
  created_at: string;
  updated_at: string;
}

export interface ActionUpdateRequest {
  recommended_action?: string;
  responsible_department?: string;
  suggested_owner_role?: string;
  priority?: ActionPriority;
  suggested_deadline?: string;
  expected_outcome?: string;
  verification_criteria?: string;
}

export interface ActionApproveRequest {
  approver?: string;
  notes?: string;
}

export interface ActionRejectRequest {
  reason: string;
  rejected_by?: string;
}

export interface TaskStatusUpdateRequest {
  new_status: ActionStatus;
  notes?: string;
  completion_details?: string;
}

export interface TaskAssignmentUpdateRequest {
  responsible_department?: string;
  suggested_owner_role?: string;
  suggested_deadline?: string;
  reason?: string;
}

export interface ProgressNoteCreateRequest {
  note: string;
  author?: string;
}

export interface ProgressNoteResponse {
  id: number;
  action_id: string;
  note: string;
  author: string;
  created_at: string;
}

export interface AuditLogEntry {
  id: number;
  action_id: string;
  action_type: string;
  previous_value?: string | null;
  new_value?: string | null;
  details?: string | null;
  timestamp: string;
}

export interface ActionHistoryResponse {
  action: ActionResponse;
  notes: ProgressNoteResponse[];
  audit_log: AuditLogEntry[];
}
