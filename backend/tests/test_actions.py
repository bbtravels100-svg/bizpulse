import os
import tempfile
import pytest
import concurrent.futures
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from app.main import app
from app.actions.models import (
    ActionStatus,
    ActionPriority,
    ActionCreateRequest,
    ActionUpdateRequest,
    ActionApproveRequest,
    ActionRejectRequest,
    TaskStatusUpdateRequest,
    TaskAssignmentUpdateRequest,
    ProgressNoteCreateRequest,
)
from app.actions.database import init_db
from app.actions.service import (
    ActionService,
    ActionNotFoundError,
    InvalidStatusTransitionError,
    ActionValidationError,
    compute_action_fingerprint,
    normalize_action_text,
)
from app.agents.models import (
    OrchestrationResponse,
    OrchestrationStages,
    StageResult,
    RouterOutput,
    WriterOutput,
)
from app.services.investigation_service import InvestigationFacts


@pytest.fixture
def temp_db():
    """Create a temporary SQLite database for test isolation."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    init_db(path)
    yield path
    try:
        if os.path.exists(path):
            os.remove(path)
    except OSError:
        pass


@pytest.fixture
def action_service(temp_db):
    """Return an ActionService instance wired to the isolated temporary DB."""
    return ActionService(db_path=temp_db)


@pytest.fixture
def client(temp_db):
    """Return TestClient configured with isolated database."""
    with patch("app.actions.service.default_action_service.db_path", temp_db), \
         patch("app.actions.router.default_action_service.db_path", temp_db):
        yield TestClient(app)


# Sample Create Payload
SAMPLE_ACTION_PAYLOAD = {
    "investigation_id": "ORCH-5D957914",
    "anomaly_id": "ANOMALY_FUNNEL_MOBILE_001",
    "problem_description": "Mobile checkout conversion dropped 70.73% following v2.4.0 deploy.",
    "recommended_action": "Execute immediate rollback of checkout frontend to v2.3.9.",
    "responsible_department": "Engineering",
    "suggested_owner_role": "Checkout Frontend Engineering Team",
    "priority": "Critical",
    "suggested_deadline": "2026-11-22",
    "expected_outcome": "Restore mobile payment completion rate to >= 74%.",
    "verification_criteria": "Mobile payment completion returns to baseline ~75% within 24h.",
}


# ============================================================================
# 1. Action Creation & Validation Tests
# ============================================================================

def test_create_action_proposal(action_service):
    """Test manual creation of an action proposal in 'Pending Approval' status."""
    req = ActionCreateRequest(**SAMPLE_ACTION_PAYLOAD)
    action = action_service.create_action(req)

    assert action.id.startswith("ACT-")
    assert action.status == ActionStatus.PENDING_APPROVAL
    assert action.priority == ActionPriority.CRITICAL
    assert action.investigation_id == "ORCH-5D957914"
    assert action.suggested_owner_role == "Checkout Frontend Engineering Team"
    # Ensure no real employee names
    assert "John" not in action.suggested_owner_role

    # Verify audit log
    history = action_service.get_action_history(action.id)
    assert len(history.audit_log) == 1
    assert history.audit_log[0].action_type == "PROPOSAL_CREATED"


def test_edit_proposal_before_approval(action_service):
    """Managers can edit proposal fields prior to approval."""
    req = ActionCreateRequest(**SAMPLE_ACTION_PAYLOAD)
    action = action_service.create_action(req)

    update = ActionUpdateRequest(
        recommended_action="Hotfix validation script instead of full rollback",
        priority=ActionPriority.HIGH,
        suggested_deadline="2026-11-23",
    )
    edited = action_service.edit_proposal(action.id, update)

    assert edited.recommended_action == "Hotfix validation script instead of full rollback"
    assert edited.priority == ActionPriority.HIGH
    assert edited.suggested_deadline == "2026-11-23"
    assert edited.status == ActionStatus.PENDING_APPROVAL

    # Verify audit trail
    history = action_service.get_action_history(action.id)
    audit_types = [a.action_type for a in history.audit_log]
    assert "PROPOSAL_EDITED" in audit_types


def test_edit_disallowed_on_approved_or_active_tasks(action_service):
    """Disallow editing proposal core attributes once an action has been approved."""
    req = ActionCreateRequest(**SAMPLE_ACTION_PAYLOAD)
    action = action_service.create_action(req)
    action_service.approve_action(action.id, ActionApproveRequest())

    with pytest.raises(ActionValidationError, match="Only proposals in 'Pending Approval' status"):
        action_service.edit_proposal(action.id, ActionUpdateRequest(recommended_action="New text"))


# ============================================================================
# 2. Human Approval & Rejection Workflow Tests
# ============================================================================

def test_approve_action_proposal(action_service):
    """Test approval workflow: Pending Approval -> Approved."""
    req = ActionCreateRequest(**SAMPLE_ACTION_PAYLOAD)
    action = action_service.create_action(req)

    approved = action_service.approve_action(
        action.id, ActionApproveRequest(approver="Engineering Director", notes="Authorized rollback")
    )
    assert approved.status == ActionStatus.APPROVED

    # Verify audit log
    history = action_service.get_action_history(action.id)
    approved_entry = [a for a in history.audit_log if a.action_type == "ACTION_APPROVED"][0]
    assert approved_entry.previous_value == ActionStatus.PENDING_APPROVAL.value
    assert approved_entry.new_value == ActionStatus.APPROVED.value
    assert "Engineering Director" in approved_entry.details


def test_reject_action_proposal(action_service):
    """Test rejection workflow with mandatory reason."""
    req = ActionCreateRequest(**SAMPLE_ACTION_PAYLOAD)
    action = action_service.create_action(req)

    rejected = action_service.reject_action(
        action.id, ActionRejectRequest(reason="Issue resolved by network routing fix", rejected_by="VP Ops")
    )
    assert rejected.status == ActionStatus.REJECTED
    assert rejected.rejection_reason == "Issue resolved by network routing fix"

    history = action_service.get_action_history(action.id)
    rejected_entry = [a for a in history.audit_log if a.action_type == "ACTION_REJECTED"][0]
    assert rejected_entry.new_value == ActionStatus.REJECTED.value


def test_double_approval_raises_error(action_service):
    """Cannot approve an already approved action."""
    req = ActionCreateRequest(**SAMPLE_ACTION_PAYLOAD)
    action = action_service.create_action(req)
    action_service.approve_action(action.id, ActionApproveRequest())

    with pytest.raises(InvalidStatusTransitionError, match="Cannot approve action"):
        action_service.approve_action(action.id, ActionApproveRequest())


# ============================================================================
# 3. Status Transitions & Active Task Lifecycle
# ============================================================================

def test_valid_task_lifecycle_to_completion(action_service):
    """Verify full linear lifecycle: Pending Approval -> Approved -> In Progress -> Completed."""
    req = ActionCreateRequest(**SAMPLE_ACTION_PAYLOAD)
    action = action_service.create_action(req)

    # 1. Approve
    action = action_service.approve_action(action.id, ActionApproveRequest())
    assert action.status == ActionStatus.APPROVED

    # 2. In Progress
    action = action_service.update_task_status(
        action.id, TaskStatusUpdateRequest(new_status=ActionStatus.IN_PROGRESS, notes="Rollback PR #104 opened")
    )
    assert action.status == ActionStatus.IN_PROGRESS

    # 3. Completed
    action = action_service.update_task_status(
        action.id,
        TaskStatusUpdateRequest(
            new_status=ActionStatus.COMPLETED,
            completion_details="Rollback to v2.3.9 completed. Mobile payment conversion restored to 75.2%.",
        ),
    )
    assert action.status == ActionStatus.COMPLETED
    assert action.completed_at is not None
    assert "restored to 75.2%" in action.completion_details.lower()


def test_prevent_unapproved_proposal_entering_in_progress(action_service):
    """STRICT RULE: Cannot skip approval (Pending Approval -> In Progress is blocked)."""
    req = ActionCreateRequest(**SAMPLE_ACTION_PAYLOAD)
    action = action_service.create_action(req)
    assert action.status == ActionStatus.PENDING_APPROVAL

    with pytest.raises(InvalidStatusTransitionError, match="Cannot transition from 'Pending Approval' to 'In Progress'"):
        action_service.update_task_status(
            action.id, TaskStatusUpdateRequest(new_status=ActionStatus.IN_PROGRESS)
        )


def test_prevent_transition_from_completed_terminal(action_service):
    """Completed tasks are terminal and cannot be moved back to In Progress."""
    req = ActionCreateRequest(**SAMPLE_ACTION_PAYLOAD)
    action = action_service.create_action(req)
    action_service.approve_action(action.id, ActionApproveRequest())
    action_service.update_task_status(action.id, TaskStatusUpdateRequest(new_status=ActionStatus.IN_PROGRESS))
    action_service.update_task_status(action.id, TaskStatusUpdateRequest(new_status=ActionStatus.COMPLETED))

    with pytest.raises(InvalidStatusTransitionError, match="Cannot transition from 'Completed'"):
        action_service.update_task_status(
            action.id, TaskStatusUpdateRequest(new_status=ActionStatus.IN_PROGRESS)
        )


# ============================================================================
# 4. Persistence After Database Restart Test
# ============================================================================

def test_data_persistence_after_restart(temp_db):
    """Verify that all records, notes, and audit logs persist across service restarts."""
    service1 = ActionService(db_path=temp_db)
    req = ActionCreateRequest(**SAMPLE_ACTION_PAYLOAD)
    action = service1.create_action(req)
    service1.approve_action(action.id, ActionApproveRequest(approver="Manager A"))
    service1.add_progress_note(action.id, ProgressNoteCreateRequest(note="Testing persistence note", author="Dev 1"))

    # Simulate backend crash/restart by instantiating a completely new service instance
    service2 = ActionService(db_path=temp_db)
    reloaded = service2.get_action(action.id)

    assert reloaded.id == action.id
    assert reloaded.status == ActionStatus.APPROVED
    assert reloaded.problem_description == SAMPLE_ACTION_PAYLOAD["problem_description"]

    history = service2.get_action_history(action.id)
    assert len(history.notes) == 1
    assert history.notes[0].note == "Testing persistence note"
    assert len(history.audit_log) >= 2


# ============================================================================
# 5. Assignment Updates & Progress Notes Tests
# ============================================================================

def test_update_task_assignment_and_deadline(action_service):
    req = ActionCreateRequest(**SAMPLE_ACTION_PAYLOAD)
    action = action_service.create_action(req)
    action_service.approve_action(action.id, ActionApproveRequest())

    updated = action_service.update_task_assignment(
        action.id,
        TaskAssignmentUpdateRequest(
            responsible_department="Infrastructure & DevOps",
            suggested_deadline="2026-11-25",
            reason="Transferred to infra team for container rollback",
        ),
    )
    assert updated.responsible_department == "Infrastructure & DevOps"
    assert updated.suggested_deadline == "2026-11-25"

    history = action_service.get_action_history(action.id)
    audit = [a for a in history.audit_log if a.action_type == "ASSIGNMENT_UPDATED"]
    assert len(audit) == 1
    assert "Infrastructure & DevOps" in audit[0].details


def test_add_progress_notes_threaded(action_service):
    req = ActionCreateRequest(**SAMPLE_ACTION_PAYLOAD)
    action = action_service.create_action(req)

    note1 = action_service.add_progress_note(
        action.id, ProgressNoteCreateRequest(note="Initial triage completed", author="Tech Lead")
    )
    note2 = action_service.add_progress_note(
        action.id, ProgressNoteCreateRequest(note="Rollback branch staged", author="Release Engineer")
    )

    assert note1.id is not None
    assert note2.id > note1.id

    history = action_service.get_action_history(action.id)
    assert len(history.notes) == 2
    assert history.notes[0].note == "Initial triage completed"
    assert history.notes[1].author == "Release Engineer"


# ============================================================================
# 6. API Endpoint Integration Tests (HTTP Layer)
# ============================================================================

def test_api_propose_action(client):
    resp = client.post("/api/actions/propose", json=SAMPLE_ACTION_PAYLOAD)
    assert resp.status_code == 201
    data = resp.json()
    assert data["id"].startswith("ACT-")
    assert data["status"] == "Pending Approval"


def test_api_list_proposals_and_active_tasks(client):
    # Create proposal
    post_resp = client.post("/api/actions/propose", json=SAMPLE_ACTION_PAYLOAD)
    action_id = post_resp.json()["id"]

    # Check proposals endpoint
    prop_resp = client.get("/api/actions/proposals")
    assert prop_resp.status_code == 200
    assert any(a["id"] == action_id for a in prop_resp.json())

    # Active tasks should be empty before approval
    tasks_resp = client.get("/api/tasks")
    assert tasks_resp.status_code == 200
    assert not any(a["id"] == action_id for a in tasks_resp.json())

    # Approve action
    appr_resp = client.post(f"/api/actions/{action_id}/approve", json={"approver": "Manager"})
    assert appr_resp.status_code == 200
    assert appr_resp.json()["status"] == "Approved"

    # Now it should be present in /api/tasks
    tasks_resp2 = client.get("/api/tasks")
    assert any(a["id"] == action_id for a in tasks_resp2.json())


def test_api_update_task_status_and_completion(client):
    post_resp = client.post("/api/actions/propose", json=SAMPLE_ACTION_PAYLOAD)
    action_id = post_resp.json()["id"]

    # Must approve first
    client.post(f"/api/actions/{action_id}/approve")

    # Move to In Progress
    in_prog = client.patch(f"/api/tasks/{action_id}/status", json={"new_status": "In Progress", "notes": "Started work"})
    assert in_prog.status_code == 200
    assert in_prog.json()["status"] == "In Progress"

    # Move to Completed
    comp = client.patch(
        f"/api/tasks/{action_id}/status",
        json={"new_status": "Completed", "completion_details": "Fix verified in staging and production."},
    )
    assert comp.status_code == 200
    assert comp.json()["status"] == "Completed"
    assert comp.json()["completed_at"] is not None


def test_api_invalid_status_transition_returns_400(client):
    post_resp = client.post("/api/actions/propose", json=SAMPLE_ACTION_PAYLOAD)
    action_id = post_resp.json()["id"]

    # Try skipping approval straight to In Progress
    bad_resp = client.patch(f"/api/tasks/{action_id}/status", json={"new_status": "In Progress"})
    assert bad_resp.status_code == 400
    assert "Invalid status transition" in bad_resp.json()["detail"]


def test_api_nonexistent_action_returns_404(client):
    resp = client.get("/api/actions/ACT-NONEXISTENT")
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()


def test_api_task_history_endpoint(client):
    post_resp = client.post("/api/actions/propose", json=SAMPLE_ACTION_PAYLOAD)
    action_id = post_resp.json()["id"]

    client.post(f"/api/tasks/{action_id}/notes", json={"note": "Investigating logs", "author": "QA Lead"})
    client.post(f"/api/actions/{action_id}/approve", json={"approver": "Manager"})

    hist_resp = client.get(f"/api/tasks/{action_id}/history")
    assert hist_resp.status_code == 200
    hist = hist_resp.json()
    assert hist["action"]["id"] == action_id
    assert len(hist["notes"]) == 1
    assert hist["notes"][0]["author"] == "QA Lead"
    assert len(hist["audit_log"]) >= 3


# ============================================================================
# Phase 5 Step 2A: Idempotency & Duplicate Prevention Tests
# ============================================================================

def _build_mock_orchestration(
    anomaly_id: str = "ANOMALY_FUNNEL_MOBILE_001",
    action_plan: list = None,
    orchestration_id: str = "ORCH-TEST-IDEMPOTENCY-001",
    problem_statement: str = "Mobile checkout conversion dropped by 22% after release v2.1",
    primary_dept: str = "Engineering",
    role_or_team: str = "Frontend Engineering Team",
    priority: str = "High",
) -> OrchestrationResponse:
    if action_plan is None:
        action_plan = [
            "Roll back mobile checkout release v2.1 to restore baseline checkout conversion",
            "Establish automated integration tests for mobile cart and checkout flows",
        ]

    router_output = RouterOutput(
        primary_department=primary_dept,
        collaborating_departments=["Product", "QA"],
        recommended_role_or_team=role_or_team,
        priority=priority,
        suggested_next_action="Initiate production rollback of release v2.1",
        routing_justification="Regression directly traced to mobile bundle update in release v2.1",
    )

    writer_output = WriterOutput(
        executive_summary="Executive action required for mobile checkout drop.",
        problem_statement=problem_statement,
        confirmed_evidence=["Conversion dropped 22%", "Android devices affected 85%"],
        likely_causes=["Asset loading failure in checkout.bundle.js"],
        target_team_and_priority=f"{role_or_team} - {priority}",
        recommended_action_plan=action_plan,
        verification_and_success_criteria=[
            "Mobile checkout conversion restores to >= 3.2%",
            "Zero uncaught JavaScript exceptions in checkout funnel",
        ],
    )

    facts = InvestigationFacts(
        anomaly_id=anomaly_id,
        anomaly_title="Mobile Checkout Conversion Drop",
        metric_facts={"conversion_drop_pct": 22.0},
        timeline_events=[],
    )

    stages = OrchestrationStages(
        analyst=StageResult(agent_name="Analyst", status="completed", duration_ms=25.0),
        connector=StageResult(agent_name="Connector", status="completed", duration_ms=30.0),
        router=StageResult(agent_name="Router", status="completed", duration_ms=20.0, output=router_output),
        writer=StageResult(agent_name="Writer", status="completed", duration_ms=45.0, output=writer_output),
    )

    return OrchestrationResponse(
        orchestration_id=orchestration_id,
        anomaly_id=anomaly_id,
        status="completed",
        facts=facts,
        stages=stages,
        final_action_brief=writer_output,
        total_duration_ms=120.0,
        model_used="gemini-2.5-flash-mock",
        created_at=datetime.now(timezone.utc).isoformat(),
    )


def test_orchestration_proposals_idempotency_first_generation(action_service):
    """Test 1: First generation creates structured action proposals."""
    orch = _build_mock_orchestration()
    actions = action_service.generate_proposals_from_orchestration(orch)

    assert len(actions) == 2
    for act in actions:
        assert act.status == ActionStatus.PENDING_APPROVAL
        assert act.anomaly_id == orch.anomaly_id
        assert act.investigation_id == orch.orchestration_id
        assert act.problem_description == orch.final_action_brief.problem_statement
        assert act.responsible_department == "Engineering"
        assert act.suggested_owner_role == "Frontend Engineering Team"

    persisted = action_service.list_proposals()
    assert len(persisted) == 2
    persisted_ids = {p.id for p in persisted}
    assert {a.id for a in actions} == persisted_ids


def test_orchestration_proposals_idempotency_repeated_generation(action_service):
    """Test 2: Repeating the same generation does not create duplicate proposals."""
    orch = _build_mock_orchestration()

    res1 = action_service.generate_proposals_from_orchestration(orch)
    assert len(res1) == 2
    initial_ids = [a.id for a in res1]

    # Repeat exact same generation
    res2 = action_service.generate_proposals_from_orchestration(orch)
    assert len(res2) == 2
    repeat_ids = [a.id for a in res2]

    # Returned actions must reference the exact existing proposals
    assert initial_ids == repeat_ids

    # Total proposals in database must strictly remain 2
    persisted = action_service.list_proposals()
    assert len(persisted) == 2


def test_orchestration_proposals_idempotency_different_formatting(action_service):
    """Test 3: Slightly different formatting of the same action does not create a duplicate."""
    raw_action = "Roll back mobile checkout release v2.1 to restore baseline checkout conversion"
    orch1 = _build_mock_orchestration(action_plan=[raw_action])

    res1 = action_service.generate_proposals_from_orchestration(orch1)
    assert len(res1) == 1
    original_id = res1[0].id

    # Formatting variations: leading number bullet, extra whitespace, capitalization, trailing period
    variations = [
        "1. Roll back mobile checkout release v2.1 to restore baseline checkout conversion.",
        "   1)   ROLL BACK mobile checkout release v2.1 to restore baseline checkout conversion   ",
        "-  roll back   mobile checkout   release v2.1 to restore baseline checkout conversion;",
        "* Roll back mobile checkout release v2.1 to restore baseline checkout conversion!",
    ]

    for variant in variations:
        orch_var = _build_mock_orchestration(action_plan=[variant])
        res_var = action_service.generate_proposals_from_orchestration(orch_var)
        assert len(res_var) == 1
        assert res_var[0].id == original_id, f"Variant '{variant}' generated a duplicate ID instead of matching"

    # Only one proposal should exist in the database
    persisted = action_service.list_proposals()
    assert len(persisted) == 1


def test_orchestration_proposals_idempotency_genuinely_different_action(action_service):
    """Test 4: Genuinely different recommendations create distinct proposals."""
    orch1 = _build_mock_orchestration(
        action_plan=["Roll back mobile checkout release v2.1 to restore baseline checkout conversion"]
    )
    res1 = action_service.generate_proposals_from_orchestration(orch1)
    assert len(res1) == 1

    # Second orchestration with genuinely different action plan
    orch2 = _build_mock_orchestration(
        action_plan=["Deploy Redis caching layer for mobile product catalog responses"]
    )
    res2 = action_service.generate_proposals_from_orchestration(orch2)
    assert len(res2) == 1

    # Distinct action records
    assert res1[0].id != res2[0].id
    persisted = action_service.list_proposals()
    assert len(persisted) == 2


def test_orchestration_proposals_idempotency_lifecycle_approved_and_rejected(action_service):
    """Test 5: Existing approved or rejected proposals are handled consistently without duplicates."""
    orch = _build_mock_orchestration()
    res = action_service.generate_proposals_from_orchestration(orch)
    assert len(res) == 2
    act1_id = res[0].id
    act2_id = res[1].id

    # Transition act1 to Approved
    approved_act = action_service.approve_action(act1_id, ActionApproveRequest(approver="CEO"))
    assert approved_act.status == ActionStatus.APPROVED

    # Transition act2 to Rejected
    rejected_act = action_service.reject_action(
        act2_id, ActionRejectRequest(rejected_by="CEO", reason="Deferred to next sprint")
    )
    assert rejected_act.status == ActionStatus.REJECTED

    # Re-running orchestration generation must return the existing records in their current status
    res_repeat = action_service.generate_proposals_from_orchestration(orch)
    assert len(res_repeat) == 2

    # Map by ID
    repeat_map = {a.id: a for a in res_repeat}
    assert act1_id in repeat_map
    assert repeat_map[act1_id].status == ActionStatus.APPROVED

    assert act2_id in repeat_map
    assert repeat_map[act2_id].status == ActionStatus.REJECTED

    # Ensure no new pending proposals were spawned
    pending = action_service.list_proposals()
    assert len(pending) == 0


def test_orchestration_proposals_concurrent_requests(action_service):
    """Test 6: Concurrent duplicate requests do not create duplicate records."""
    orch = _build_mock_orchestration()
    num_threads = 10

    def run_worker():
        return action_service.generate_proposals_from_orchestration(orch)

    with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = [executor.submit(run_worker) for _ in range(num_threads)]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]

    # All threads must succeed and return exactly 2 action proposals
    assert len(results) == num_threads
    for res in results:
        assert len(res) == 2

    # Extract all generated IDs across all 10 concurrent executions
    all_returned_ids = {a.id for res in results for a in res}
    assert len(all_returned_ids) == 2, f"Expected 2 unique IDs across concurrent runs, got: {all_returned_ids}"

    # Database must contain exactly 2 actions
    persisted = action_service.list_proposals()
    assert len(persisted) == 2
