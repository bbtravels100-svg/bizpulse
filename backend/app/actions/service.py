import uuid
import re
import hashlib
import sqlite3
import threading
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any

from .database import get_db_connection
from .models import (
    ActionStatus,
    ActionPriority,
    ALLOWED_TRANSITIONS,
    ActionCreateRequest,
    ActionUpdateRequest,
    ActionApproveRequest,
    ActionRejectRequest,
    TaskStatusUpdateRequest,
    TaskAssignmentUpdateRequest,
    ProgressNoteCreateRequest,
    ActionResponse,
    ProgressNoteResponse,
    AuditLogEntry,
    ActionHistoryResponse,
)
from ..agents.models import OrchestrationResponse


_orchestration_generation_lock = threading.Lock()


def normalize_action_text(text: str) -> str:
    """
    Normalize action text for robust duplicate comparison:
    1. Strip leading and trailing whitespace
    2. Lowercase all characters
    3. Remove leading markdown/numbered bullets like '1. ', '1) ', '- ', '* '
    4. Collapse all whitespace sequences (tabs, newlines, multiple spaces) to a single space
    5. Strip trailing punctuation (., ;, !, ?)
    """
    if not text:
        return ""
    s = text.strip().lower()
    s = re.sub(r"^(?:\d+[\.\)]|\-|\*)\s*", "", s)
    s = re.sub(r"\s+", " ", s)
    s = s.rstrip(".,;!?")
    return s.strip()


def compute_action_fingerprint(anomaly_id: str, recommended_action: str) -> str:
    """
    Compute a deterministic fingerprint from anomaly_id and normalized action text.
    """
    norm_anomaly = (anomaly_id or "").strip().lower()
    norm_action = normalize_action_text(recommended_action)
    raw = f"{norm_anomaly}::{norm_action}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class ActionServiceError(Exception):
    """Base exception for Action Service errors."""
    pass


class ActionNotFoundError(ActionServiceError):
    """Raised when an action or task is not found."""
    pass


class InvalidStatusTransitionError(ActionServiceError):
    """Raised when an invalid status transition is attempted."""
    pass


class ActionValidationError(ActionServiceError):
    """Raised when action payload or state validation fails."""
    pass


class ActionService:
    """
    Action Management Service (Phase 3B).
    Transforms AI agent recommendations into structured, persistent, and auditable business tasks.
    Enforces manager approval workflows and strictly controls task status transitions.
    """

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path

    def _get_conn(self):
        return get_db_connection(self.db_path)

    # ------------------------------------------------------------------------
    # 1. Action Creation & Proposal Generation
    # ------------------------------------------------------------------------

    def find_existing_proposal_by_fingerprint(
        self, anomaly_id: str, recommended_action: str
    ) -> Optional[ActionResponse]:
        """
        Find an existing action record for the same anomaly and recommended action.
        Uses fingerprint lookup first, and falls back to normalized text comparison for backwards compatibility.
        """
        fp = compute_action_fingerprint(anomaly_id, recommended_action)
        target_norm = normalize_action_text(recommended_action)

        conn = self._get_conn()
        try:
            # 1. Direct indexed fingerprint lookup
            row = conn.execute(
                "SELECT * FROM actions WHERE action_fingerprint = ?", (fp,)
            ).fetchone()
            if row:
                return self._row_to_action_response(row)

            # 2. Fallback: inspect any actions associated with this anomaly
            norm_anomaly = (anomaly_id or "").strip().lower()
            rows = conn.execute(
                "SELECT * FROM actions WHERE lower(trim(anomaly_id)) = ?", (norm_anomaly,)
            ).fetchall()
            for r in rows:
                if normalize_action_text(r["recommended_action"]) == target_norm:
                    # Backfill fingerprint if it was NULL
                    try:
                        with conn:
                            conn.execute(
                                "UPDATE actions SET action_fingerprint = ? WHERE id = ?",
                                (fp, r["id"]),
                            )
                    except sqlite3.IntegrityError:
                        pass
                    return self._row_to_action_response(r)

            return None
        finally:
            conn.close()

    def create_action(
        self, req: ActionCreateRequest, action_fingerprint: Optional[str] = None
    ) -> ActionResponse:
        """Create a new action proposal in 'Pending Approval' status."""
        action_id = f"ACT-{uuid.uuid4().hex[:8].upper()}"
        now_iso = datetime.now(timezone.utc).isoformat()
        fp = action_fingerprint or compute_action_fingerprint(req.anomaly_id, req.recommended_action)

        conn = self._get_conn()
        try:
            with conn:
                conn.execute(
                    """
                    INSERT INTO actions (
                        id, investigation_id, anomaly_id, problem_description,
                        recommended_action, responsible_department, suggested_owner_role,
                        priority, suggested_deadline, expected_outcome, verification_criteria,
                        status, rejection_reason, completion_details, completed_at,
                        action_fingerprint, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        action_id,
                        req.investigation_id,
                        req.anomaly_id,
                        req.problem_description,
                        req.recommended_action,
                        req.responsible_department,
                        req.suggested_owner_role,
                        req.priority.value,
                        req.suggested_deadline,
                        req.expected_outcome,
                        req.verification_criteria,
                        ActionStatus.PENDING_APPROVAL.value,
                        None,
                        None,
                        None,
                        fp,
                        now_iso,
                        now_iso,
                    ),
                )
                conn.execute(
                    """
                    INSERT INTO action_audit_log (
                        action_id, action_type, previous_value, new_value, details, timestamp
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        action_id,
                        "PROPOSAL_CREATED",
                        None,
                        ActionStatus.PENDING_APPROVAL.value,
                        f"Action proposal generated from investigation {req.investigation_id}",
                        now_iso,
                    ),
                )
        finally:
            conn.close()

        return self.get_action(action_id)

    def generate_proposals_from_orchestration(
        self, orchestration: OrchestrationResponse
    ) -> List[ActionResponse]:
        """
        Generate structured action proposals from the output of the 4-agent orchestrator.
        Idempotent: prevents creating duplicate proposals for the same anomaly and recommended action.
        Extracts recommended actions from Agent 4 (Writer) and routing metadata from Agent 3 (Router).
        """
        if not orchestration.final_action_brief:
            raise ActionValidationError("Orchestration has no final action brief to generate actions from.")

        brief = orchestration.final_action_brief
        router_out = orchestration.stages.router.output
        router_dict = router_out.model_dump() if hasattr(router_out, "model_dump") else router_out

        primary_dept = router_dict.get("primary_department", "Cross-Functional") if isinstance(router_dict, dict) else "Cross-Functional"
        owner_role = router_dict.get("recommended_role_or_team", "Remediation Team") if isinstance(router_dict, dict) else "Remediation Team"
        raw_prio = router_dict.get("priority", "High") if isinstance(router_dict, dict) else "High"

        # Map priority string
        prio_map = {
            "critical": ActionPriority.CRITICAL,
            "high": ActionPriority.HIGH,
            "medium": ActionPriority.MEDIUM,
            "low": ActionPriority.LOW,
        }
        priority = prio_map.get(raw_prio.lower(), ActionPriority.HIGH)

        # Calculate deadline based on urgency
        days_offset = 2 if priority == ActionPriority.CRITICAL else (5 if priority == ActionPriority.HIGH else 10)
        target_deadline = (datetime.now(timezone.utc) + timedelta(days=days_offset)).strftime("%Y-%m-%d")

        verification_text = "; ".join(brief.verification_and_success_criteria)
        created_actions: List[ActionResponse] = []

        anomaly_id = orchestration.anomaly_id

        with _orchestration_generation_lock:
            for act_str in brief.recommended_action_plan:
                if not act_str or not act_str.strip():
                    continue

                clean_act = act_str.strip()
                fp = compute_action_fingerprint(anomaly_id, clean_act)

                # Check if proposal or action already exists for this anomaly
                existing = self.find_existing_proposal_by_fingerprint(anomaly_id, clean_act)
                if existing:
                    created_actions.append(existing)
                    continue

                req = ActionCreateRequest(
                    investigation_id=orchestration.orchestration_id,
                    anomaly_id=anomaly_id,
                    problem_description=brief.problem_statement,
                    recommended_action=clean_act,
                    responsible_department=primary_dept,
                    suggested_owner_role=owner_role,
                    priority=priority,
                    suggested_deadline=target_deadline,
                    expected_outcome=f"Remediate anomaly: {brief.problem_statement[:120]}...",
                    verification_criteria=verification_text,
                )
                try:
                    action_resp = self.create_action(req, action_fingerprint=fp)
                    created_actions.append(action_resp)
                except sqlite3.IntegrityError:
                    # Concurrency safety: if another thread/process inserted simultaneously, return existing record
                    existing_race = self.find_existing_proposal_by_fingerprint(anomaly_id, clean_act)
                    if existing_race:
                        created_actions.append(existing_race)
                    else:
                        raise

        return created_actions

    # ------------------------------------------------------------------------
    # 2. Retrieval & Listing
    # ------------------------------------------------------------------------

    def get_action(self, action_id: str) -> ActionResponse:
        """Fetch a single action record by ID."""
        conn = self._get_conn()
        try:
            row = conn.execute("SELECT * FROM actions WHERE id = ?", (action_id,)).fetchone()
            if not row:
                raise ActionNotFoundError(f"Action '{action_id}' not found.")
            return self._row_to_action_response(row)
        finally:
            conn.close()

    def list_actions(
        self,
        status: Optional[ActionStatus] = None,
        active_only: bool = False,
        department: Optional[str] = None,
        investigation_id: Optional[str] = None,
    ) -> List[ActionResponse]:
        """
        List actions with optional filtering:
        - status: specific ActionStatus
        - active_only: True returns Approved, In Progress, Overdue, and Completed
        - department: filter by responsible department
        - investigation_id: filter by investigation/orchestration ID
        """
        conn = self._get_conn()
        try:
            query = "SELECT * FROM actions WHERE 1=1"
            params: List[Any] = []

            if status:
                query += " AND status = ?"
                params.append(status.value)
            elif active_only:
                query += " AND status IN (?, ?, ?, ?)"
                params.extend([
                    ActionStatus.APPROVED.value,
                    ActionStatus.IN_PROGRESS.value,
                    ActionStatus.OVERDUE.value,
                    ActionStatus.COMPLETED.value,
                ])

            if department:
                query += " AND responsible_department LIKE ?"
                params.append(f"%{department}%")

            if investigation_id:
                query += " AND investigation_id = ?"
                params.append(investigation_id)

            query += " ORDER BY created_at DESC"
            rows = conn.execute(query, params).fetchall()

            # Auto-check and flag overdue tasks
            results: List[ActionResponse] = []
            now_iso = datetime.now(timezone.utc).isoformat()

            for r in rows:
                act = self._row_to_action_response(r)
                # Overdue check: if deadline is past and status is Approved or In Progress
                if act.status in (ActionStatus.APPROVED, ActionStatus.IN_PROGRESS):
                    if act.suggested_deadline < now_iso[:10]:
                        act = self._mark_overdue(act.id)
                results.append(act)

            return results
        finally:
            conn.close()

    def list_proposals(self) -> List[ActionResponse]:
        """Convenience method returning all actions pending human manager approval."""
        return self.list_actions(status=ActionStatus.PENDING_APPROVAL)

    def list_active_tasks(self) -> List[ActionResponse]:
        """Convenience method returning only approved, in progress, overdue, or completed tasks."""
        return self.list_actions(active_only=True)

    # ------------------------------------------------------------------------
    # 3. Human Approval Workflow
    # ------------------------------------------------------------------------

    def edit_proposal(self, action_id: str, update: ActionUpdateRequest) -> ActionResponse:
        """
        Edit proposal attributes prior to approval.
        Only allowed when action is in 'Pending Approval' status.
        """
        action = self.get_action(action_id)
        if action.status != ActionStatus.PENDING_APPROVAL:
            raise ActionValidationError(
                f"Cannot edit action '{action_id}' because its status is '{action.status.value}'. "
                "Only proposals in 'Pending Approval' status can be modified before approval."
            )

        conn = self._get_conn()
        now_iso = datetime.now(timezone.utc).isoformat()
        try:
            with conn:
                updates = []
                params = []
                audit_changes = []

                if update.recommended_action is not None:
                    new_fp = compute_action_fingerprint(action.anomaly_id, update.recommended_action)
                    updates.append("recommended_action = ?")
                    params.append(update.recommended_action)
                    updates.append("action_fingerprint = ?")
                    params.append(new_fp)
                    audit_changes.append(f"recommended_action: '{action.recommended_action}' -> '{update.recommended_action}'")

                if update.responsible_department is not None:
                    updates.append("responsible_department = ?")
                    params.append(update.responsible_department)
                    audit_changes.append(f"responsible_department: '{action.responsible_department}' -> '{update.responsible_department}'")

                if update.suggested_owner_role is not None:
                    updates.append("suggested_owner_role = ?")
                    params.append(update.suggested_owner_role)
                    audit_changes.append(f"suggested_owner_role: '{action.suggested_owner_role}' -> '{update.suggested_owner_role}'")

                if update.priority is not None:
                    updates.append("priority = ?")
                    params.append(update.priority.value)
                    audit_changes.append(f"priority: '{action.priority.value}' -> '{update.priority.value}'")

                if update.suggested_deadline is not None:
                    updates.append("suggested_deadline = ?")
                    params.append(update.suggested_deadline)
                    audit_changes.append(f"suggested_deadline: '{action.suggested_deadline}' -> '{update.suggested_deadline}'")

                if update.expected_outcome is not None:
                    updates.append("expected_outcome = ?")
                    params.append(update.expected_outcome)
                    audit_changes.append("expected_outcome updated")

                if update.verification_criteria is not None:
                    updates.append("verification_criteria = ?")
                    params.append(update.verification_criteria)
                    audit_changes.append("verification_criteria updated")

                if not updates:
                    return action

                updates.append("updated_at = ?")
                params.append(now_iso)
                params.append(action_id)

                sql = f"UPDATE actions SET {', '.join(updates)} WHERE id = ?"
                conn.execute(sql, params)

                conn.execute(
                    """
                    INSERT INTO action_audit_log (
                        action_id, action_type, previous_value, new_value, details, timestamp
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        action_id,
                        "PROPOSAL_EDITED",
                        None,
                        None,
                        "; ".join(audit_changes),
                        now_iso,
                    ),
                )
        finally:
            conn.close()

        return self.get_action(action_id)

    def approve_action(self, action_id: str, req: ActionApproveRequest) -> ActionResponse:
        """
        Approve an action proposal, transitioning it into the active task workflow ('Approved').
        Strict check: Must currently be in 'Pending Approval'.
        """
        action = self.get_action(action_id)
        if action.status != ActionStatus.PENDING_APPROVAL:
            raise InvalidStatusTransitionError(
                f"Cannot approve action '{action_id}' in status '{action.status.value}'. "
                "Only actions in 'Pending Approval' can be approved."
            )

        now_iso = datetime.now(timezone.utc).isoformat()
        conn = self._get_conn()
        try:
            with conn:
                conn.execute(
                    "UPDATE actions SET status = ?, updated_at = ? WHERE id = ?",
                    (ActionStatus.APPROVED.value, now_iso, action_id),
                )
                conn.execute(
                    """
                    INSERT INTO action_audit_log (
                        action_id, action_type, previous_value, new_value, details, timestamp
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        action_id,
                        "ACTION_APPROVED",
                        ActionStatus.PENDING_APPROVAL.value,
                        ActionStatus.APPROVED.value,
                        f"Approved by {req.approver or 'Manager'}. Notes: {req.notes or 'None'}",
                        now_iso,
                    ),
                )
        finally:
            conn.close()

        # Phase 3C: Automatically capture baseline metrics upon approval
        try:
            from ..verification.service import VerificationService
            ver_svc = VerificationService(db_path=self.db_path, action_service=self)
            ver_svc.capture_baseline_for_action(action_id)
        except Exception:
            pass

        return self.get_action(action_id)

    def reject_action(self, action_id: str, req: ActionRejectRequest) -> ActionResponse:
        """
        Reject an action proposal or approved task with a mandatory reason.
        Sets status to 'Rejected'.
        """
        action = self.get_action(action_id)
        if action.status not in (ActionStatus.PENDING_APPROVAL, ActionStatus.APPROVED):
            raise InvalidStatusTransitionError(
                f"Cannot reject action '{action_id}' in status '{action.status.value}'. "
                "Only proposals in 'Pending Approval' or 'Approved' status can be rejected."
            )

        now_iso = datetime.now(timezone.utc).isoformat()
        conn = self._get_conn()
        try:
            with conn:
                conn.execute(
                    "UPDATE actions SET status = ?, rejection_reason = ?, updated_at = ? WHERE id = ?",
                    (ActionStatus.REJECTED.value, req.reason, now_iso, action_id),
                )
                conn.execute(
                    """
                    INSERT INTO action_audit_log (
                        action_id, action_type, previous_value, new_value, details, timestamp
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        action_id,
                        "ACTION_REJECTED",
                        action.status.value,
                        ActionStatus.REJECTED.value,
                        f"Rejected by {req.rejected_by or 'Manager'}. Reason: {req.reason}",
                        now_iso,
                    ),
                )
        finally:
            conn.close()

        return self.get_action(action_id)

    # ------------------------------------------------------------------------
    # 4. Task Management & Status Transitions
    # ------------------------------------------------------------------------

    def update_task_status(self, action_id: str, req: TaskStatusUpdateRequest) -> ActionResponse:
        """
        Update the execution status of an active task:
        Validates transition through ALLOWED_TRANSITIONS.
        Strict rule: Unapproved proposals cannot transition directly to 'In Progress' or 'Completed'.
        """
        action = self.get_action(action_id)
        current_status = action.status
        new_status = req.new_status

        # Validate transition
        allowed = ALLOWED_TRANSITIONS.get(current_status, [])
        if new_status not in allowed:
            raise InvalidStatusTransitionError(
                f"Invalid status transition for task '{action_id}': "
                f"Cannot transition from '{current_status.value}' to '{new_status.value}'. "
                f"Allowed transitions: {[s.value for s in allowed]}"
            )

        now_iso = datetime.now(timezone.utc).isoformat()
        completed_at = now_iso if new_status == ActionStatus.COMPLETED else None
        completion_details = req.completion_details if new_status == ActionStatus.COMPLETED else None

        conn = self._get_conn()
        try:
            with conn:
                conn.execute(
                    """
                    UPDATE actions SET
                        status = ?,
                        completion_details = COALESCE(?, completion_details),
                        completed_at = COALESCE(?, completed_at),
                        updated_at = ?
                    WHERE id = ?
                    """,
                    (new_status.value, completion_details, completed_at, now_iso, action_id),
                )
                conn.execute(
                    """
                    INSERT INTO action_audit_log (
                        action_id, action_type, previous_value, new_value, details, timestamp
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        action_id,
                        "STATUS_UPDATED",
                        current_status.value,
                        new_status.value,
                        f"Notes: {req.notes or 'None'}. Completion: {completion_details or 'N/A'}",
                        now_iso,
                    ),
                )
        finally:
            conn.close()

        return self.get_action(action_id)

    def update_task_assignment(self, action_id: str, req: TaskAssignmentUpdateRequest) -> ActionResponse:
        """Update department, role, or deadline on an action/task."""
        action = self.get_action(action_id)
        if action.status in (ActionStatus.COMPLETED, ActionStatus.REJECTED):
            raise ActionValidationError(
                f"Cannot update assignment on task '{action_id}' because it is in terminal state '{action.status.value}'."
            )

        now_iso = datetime.now(timezone.utc).isoformat()
        conn = self._get_conn()
        try:
            with conn:
                updates = []
                params = []
                audit_parts = []

                if req.responsible_department is not None:
                    updates.append("responsible_department = ?")
                    params.append(req.responsible_department)
                    audit_parts.append(f"department: '{action.responsible_department}' -> '{req.responsible_department}'")

                if req.suggested_owner_role is not None:
                    updates.append("suggested_owner_role = ?")
                    params.append(req.suggested_owner_role)
                    audit_parts.append(f"role: '{action.suggested_owner_role}' -> '{req.suggested_owner_role}'")

                if req.suggested_deadline is not None:
                    updates.append("suggested_deadline = ?")
                    params.append(req.suggested_deadline)
                    audit_parts.append(f"deadline: '{action.suggested_deadline}' -> '{req.suggested_deadline}'")

                if not updates:
                    return action

                updates.append("updated_at = ?")
                params.append(now_iso)
                params.append(action_id)

                conn.execute(f"UPDATE actions SET {', '.join(updates)} WHERE id = ?", params)
                conn.execute(
                    """
                    INSERT INTO action_audit_log (
                        action_id, action_type, previous_value, new_value, details, timestamp
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        action_id,
                        "ASSIGNMENT_UPDATED",
                        None,
                        None,
                        f"Updates: {'; '.join(audit_parts)}. Reason: {req.reason or 'None'}",
                        now_iso,
                    ),
                )
        finally:
            conn.close()

        return self.get_action(action_id)

    def add_progress_note(self, action_id: str, req: ProgressNoteCreateRequest) -> ProgressNoteResponse:
        """Append a progress note to a task record and log to audit."""
        action = self.get_action(action_id)
        now_iso = datetime.now(timezone.utc).isoformat()

        conn = self._get_conn()
        try:
            with conn:
                cursor = conn.execute(
                    """
                    INSERT INTO action_notes (action_id, note, author, created_at)
                    VALUES (?, ?, ?, ?)
                    """,
                    (action_id, req.note, req.author or "Manager", now_iso),
                )
                note_id = cursor.lastrowid
                conn.execute(
                    """
                    INSERT INTO action_audit_log (
                        action_id, action_type, previous_value, new_value, details, timestamp
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        action_id,
                        "PROGRESS_NOTE_ADDED",
                        None,
                        None,
                        f"Note by {req.author or 'Manager'}: {req.note[:100]}",
                        now_iso,
                    ),
                )
        finally:
            conn.close()

        return ProgressNoteResponse(
            id=note_id,
            action_id=action_id,
            note=req.note,
            author=req.author or "Manager",
            created_at=now_iso,
        )

    def get_action_history(self, action_id: str) -> ActionHistoryResponse:
        """Retrieve complete audit history and progress notes for a task."""
        action = self.get_action(action_id)
        conn = self._get_conn()
        try:
            notes_rows = conn.execute(
                "SELECT * FROM action_notes WHERE action_id = ? ORDER BY created_at ASC",
                (action_id,),
            ).fetchall()
            audit_rows = conn.execute(
                "SELECT * FROM action_audit_log WHERE action_id = ? ORDER BY timestamp ASC",
                (action_id,),
            ).fetchall()

            notes = [
                ProgressNoteResponse(
                    id=r["id"],
                    action_id=r["action_id"],
                    note=r["note"],
                    author=r["author"],
                    created_at=r["created_at"],
                )
                for r in notes_rows
            ]

            audit_log = [
                AuditLogEntry(
                    id=r["id"],
                    action_id=r["action_id"],
                    action_type=r["action_type"],
                    previous_value=r["previous_value"],
                    new_value=r["new_value"],
                    details=r["details"],
                    timestamp=r["timestamp"],
                )
                for r in audit_rows
            ]

            return ActionHistoryResponse(
                action=action,
                notes=notes,
                audit_log=audit_log,
            )
        finally:
            conn.close()

    def _mark_overdue(self, action_id: str) -> ActionResponse:
        """Internal helper to mark an expired approved/in-progress task as Overdue."""
        conn = self._get_conn()
        now_iso = datetime.now(timezone.utc).isoformat()
        try:
            with conn:
                conn.execute(
                    "UPDATE actions SET status = ?, updated_at = ? WHERE id = ?",
                    (ActionStatus.OVERDUE.value, now_iso, action_id),
                )
                conn.execute(
                    """
                    INSERT INTO action_audit_log (
                        action_id, action_type, previous_value, new_value, details, timestamp
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        action_id,
                        "MARKED_OVERDUE",
                        None,
                        ActionStatus.OVERDUE.value,
                        "Task automatically flagged as Overdue based on suggested deadline",
                        now_iso,
                    ),
                )
        finally:
            conn.close()
        return self.get_action(action_id)

    @staticmethod
    def _row_to_action_response(row) -> ActionResponse:
        return ActionResponse(
            id=row["id"],
            investigation_id=row["investigation_id"],
            anomaly_id=row["anomaly_id"],
            problem_description=row["problem_description"],
            recommended_action=row["recommended_action"],
            responsible_department=row["responsible_department"],
            suggested_owner_role=row["suggested_owner_role"],
            priority=ActionPriority(row["priority"]),
            suggested_deadline=row["suggested_deadline"],
            expected_outcome=row["expected_outcome"],
            verification_criteria=row["verification_criteria"],
            status=ActionStatus(row["status"]),
            rejection_reason=row["rejection_reason"],
            completion_details=row["completion_details"],
            completed_at=row["completed_at"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )


# Global singleton instance
default_action_service = ActionService()
