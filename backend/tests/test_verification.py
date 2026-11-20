import os
import tempfile
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient

from app.main import app
from app.actions.models import (
    ActionStatus,
    ActionPriority,
    ActionCreateRequest,
    ActionApproveRequest,
    ActionRejectRequest,
    TaskStatusUpdateRequest,
)
from app.actions.database import init_db
from app.actions.service import ActionService, ActionNotFoundError
from app.verification.models import (
    VerificationOutcome,
    VerificationStage,
    MetricComparisonDirection,
    BaselineMetric,
    BaselineCaptureRequest,
    VerificationTriggerRequest,
    VerificationNoteCreateRequest,
    ReopenInvestigationRequest,
)
from app.verification.evaluator import evaluate_metric_comparison
from app.verification.service import (
    VerificationService,
    VerificationNotFoundError,
    InvalidActionStateForVerificationError,
    ELIGIBLE_VERIFICATION_STATUSES,
)


@pytest.fixture
def temp_db():
    """Create an isolated SQLite database file for testing."""
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
    """ActionService connected to test database."""
    return ActionService(db_path=temp_db)


@pytest.fixture
def verification_service(temp_db, action_service):
    """VerificationService connected to test database."""
    return VerificationService(db_path=temp_db, action_service=action_service)


@pytest.fixture
def client(temp_db):
    """TestClient wired to isolated DB."""
    test_act_svc = ActionService(db_path=temp_db)
    test_ver_svc = VerificationService(db_path=temp_db, action_service=test_act_svc)
    with patch("app.actions.router.default_action_service", test_act_svc), \
         patch("app.actions.service.default_action_service", test_act_svc), \
         patch("app.verification.router.default_verification_service", test_ver_svc), \
         patch("app.verification.service.default_verification_service", test_ver_svc), \
         patch("app.verification.service.default_action_service", test_act_svc):
        yield TestClient(app)


SAMPLE_ACTION_PAYLOAD = {
    "investigation_id": "ORCH-TEST-001",
    "anomaly_id": "ANOMALY_FUNNEL_MOBILE_001",
    "problem_description": "Mobile payment completion plummeted 70.7% after website deployment.",
    "recommended_action": "Roll back mobile checkout sheet component to v2.3.9.",
    "responsible_department": "Engineering",
    "suggested_owner_role": "Checkout Frontend Lead",
    "priority": "Critical",
    "suggested_deadline": "2026-11-25",
    "expected_outcome": "Restore mobile payment completion rate to >= 74.00%",
    "verification_criteria": "Mobile payment completion rate recovers to >= 74.0% with zero payment 504 timeouts.",
}


# ============================================================================
# 1. Deterministic Python Evaluator Tests (Pure Math & Logic)
# ============================================================================

def test_evaluator_improved_and_target_met():
    """Baseline 21.95, Current 75.20, Target 74.00, Direction Increase -> Improved, target_met=True."""
    baseline = BaselineMetric(
        id="BASE-1",
        action_id="ACT-1",
        investigation_id="INV-1",
        anomaly_id="ANOMALY_FUNNEL_MOBILE_001",
        metric_name="mobile_payment_completion_rate",
        baseline_value=21.95,
        baseline_period="Week 2",
        expected_improvement=">= 74.00%",
        target_value=74.00,
        comparison_direction=MetricComparisonDirection.INCREASE,
        verification_criteria="Recovers to 74%",
        captured_at="2026-11-20T10:00:00Z",
    )
    res = evaluate_metric_comparison(baseline, current_value=75.20)
    assert res.outcome == VerificationOutcome.IMPROVED
    assert res.target_met is True
    assert res.absolute_change == round(75.20 - 21.95, 4)
    assert res.percentage_change == round(((75.20 - 21.95) / 21.95) * 100, 2)


def test_evaluator_improved_but_target_unmet():
    """Baseline 21.95, Current 35.00, Target 74.00, Direction Increase -> Improved, target_met=False."""
    baseline = BaselineMetric(
        id="BASE-2",
        action_id="ACT-2",
        investigation_id="INV-2",
        anomaly_id="ANOMALY_FUNNEL_MOBILE_001",
        metric_name="mobile_payment_completion_rate",
        baseline_value=21.95,
        baseline_period="Week 2",
        expected_improvement=">= 74.00%",
        target_value=74.00,
        comparison_direction=MetricComparisonDirection.INCREASE,
        verification_criteria="Recovers to 74%",
        captured_at="2026-11-20T10:00:00Z",
    )
    res = evaluate_metric_comparison(baseline, current_value=35.00)
    assert res.outcome == VerificationOutcome.IMPROVED
    assert res.target_met is False
    assert res.absolute_change > 0


def test_evaluator_not_improved_flat():
    """Baseline 21.95, Current 21.95 -> Not Improved."""
    baseline = BaselineMetric(
        id="BASE-3",
        action_id="ACT-3",
        investigation_id="INV-3",
        anomaly_id="ANOMALY_FUNNEL_MOBILE_001",
        metric_name="mobile_payment_completion_rate",
        baseline_value=21.95,
        baseline_period="Week 2",
        expected_improvement=">= 74.00%",
        target_value=74.00,
        comparison_direction=MetricComparisonDirection.INCREASE,
        verification_criteria="Recovers to 74%",
        captured_at="2026-11-20T10:00:00Z",
    )
    res = evaluate_metric_comparison(baseline, current_value=21.95)
    assert res.outcome == VerificationOutcome.NOT_IMPROVED
    assert res.target_met is False
    assert res.absolute_change == 0.0


def test_evaluator_deteriorated():
    """Baseline 21.95, Current 14.50 -> Deteriorated."""
    baseline = BaselineMetric(
        id="BASE-4",
        action_id="ACT-4",
        investigation_id="INV-4",
        anomaly_id="ANOMALY_FUNNEL_MOBILE_001",
        metric_name="mobile_payment_completion_rate",
        baseline_value=21.95,
        baseline_period="Week 2",
        expected_improvement=">= 74.00%",
        target_value=74.00,
        comparison_direction=MetricComparisonDirection.INCREASE,
        verification_criteria="Recovers to 74%",
        captured_at="2026-11-20T10:00:00Z",
    )
    res = evaluate_metric_comparison(baseline, current_value=14.50)
    assert res.outcome == VerificationOutcome.DETERIORATED
    assert res.target_met is False
    assert res.absolute_change < 0


def test_evaluator_insufficient_data():
    """Current value is None -> Insufficient Data."""
    baseline = BaselineMetric(
        id="BASE-5",
        action_id="ACT-5",
        investigation_id="INV-5",
        anomaly_id="ANOMALY_REV_001",
        metric_name="weekly_revenue",
        baseline_value=69700.00,
        baseline_period="Week 2",
        expected_improvement=">= $84,000",
        target_value=84000.00,
        comparison_direction=MetricComparisonDirection.INCREASE,
        verification_criteria="Revenue recovery",
        captured_at="2026-11-20T10:00:00Z",
    )
    res = evaluate_metric_comparison(baseline, current_value=None)
    assert res.outcome == VerificationOutcome.INSUFFICIENT_DATA
    assert res.target_met is False


def test_evaluator_direction_decrease():
    """Metric where decrease is improvement (e.g. error rate %, baseline 12.0%, target 2.0%)."""
    baseline = BaselineMetric(
        id="BASE-6",
        action_id="ACT-6",
        investigation_id="INV-6",
        anomaly_id="ANOMALY_ERROR_001",
        metric_name="checkout_error_rate_pct",
        baseline_value=12.00,
        baseline_period="Week 2",
        expected_improvement="<= 2.00%",
        target_value=2.00,
        comparison_direction=MetricComparisonDirection.DECREASE,
        verification_criteria="Error rate <= 2.0%",
        captured_at="2026-11-20T10:00:00Z",
    )
    # Case A: Dropped to 1.5% -> Improved and Target Met
    res_a = evaluate_metric_comparison(baseline, current_value=1.50)
    assert res_a.outcome == VerificationOutcome.IMPROVED
    assert res_a.target_met is True

    # Case B: Rose to 18.0% -> Deteriorated
    res_b = evaluate_metric_comparison(baseline, current_value=18.00)
    assert res_b.outcome == VerificationOutcome.DETERIORATED
    assert res_b.target_met is False


# ============================================================================
# 2. Baseline Immutability & Capture Tests
# ============================================================================

def test_baseline_capture_on_approval_and_immutability(action_service, verification_service):
    """
    Approving an action triggers automatic baseline capture.
    Calling capture again returns identical baseline without overwriting.
    """
    # 1. Create Proposal
    req = ActionCreateRequest(**SAMPLE_ACTION_PAYLOAD)
    action = action_service.create_action(req)
    assert action.status == ActionStatus.PENDING_APPROVAL

    # 2. Approve Action
    approved = action_service.approve_action(action.id, ActionApproveRequest(approver="Engineering Director"))
    assert approved.status == ActionStatus.APPROVED

    # 3. Check baseline was automatically recorded
    base1 = verification_service.get_baseline_for_action(action.id)
    assert base1 is not None
    assert base1.action_id == action.id
    assert base1.metric_name == "mobile_payment_completion_rate"
    assert base1.baseline_value == 21.95
    assert base1.target_value == 74.00

    # 4. Attempt to capture again with different values -> must be ignored and original preserved
    custom_req = BaselineCaptureRequest(
        action_id=action.id,
        metric_name="overwritten_metric",
        baseline_value=999.0,
        target_value=1000.0,
    )
    base2 = verification_service.capture_baseline_for_action(action.id, custom_req)
    assert base2.id == base1.id
    assert base2.baseline_value == 21.95
    assert base2.metric_name == "mobile_payment_completion_rate"


# ============================================================================
# 3. Verification Service & Causal Follow-Up Tests
# ============================================================================

@patch("app.verification.service.generate_json")
def test_verify_action_improved_scenario(mock_gemini, action_service, verification_service):
    """
    Trigger verification on an action with simulated 'improved' scenario.
    Verifies that Python arithmetic is accurate, target is met, is_resolved=True.
    """
    mock_gemini.return_value = {
        "what_changed": "Mobile payment completion rate surged from 21.95% to 75.20%, exceeding target.",
        "did_metric_improve": True,
        "did_it_meet_target": True,
        "possible_explanations": ["Frontend rollback eliminated JavaScript auto-focus crash on iOS Safari."],
        "recommended_next_steps": ["Maintain 48h active monitoring on mobile checkout logs."],
        "causal_attribution_confidence": "high",
    }

    req = ActionCreateRequest(**SAMPLE_ACTION_PAYLOAD)
    action = action_service.create_action(req)
    action_service.approve_action(action.id, ActionApproveRequest(approver="Engineering Director"))
    verification_service.capture_baseline_for_action(action.id)

    # Run verification with 'improved' scenario
    trig_req = VerificationTriggerRequest(
        action_id=action.id,
        stage=VerificationStage.INITIAL,
        simulated_data_scenario="improved",
    )
    run_res = verification_service.verify_action(trig_req)

    assert run_res.outcome == VerificationOutcome.IMPROVED
    assert run_res.target_met is True
    assert run_res.is_resolved is True
    assert run_res.needs_reopening is False
    assert run_res.comparison.current_value == 75.20
    assert run_res.comparison.percentage_change > 200.0
    assert run_res.gemini_analysis is not None
    assert run_res.gemini_analysis.causal_attribution_confidence == "high"


@patch("app.verification.service.generate_json")
def test_verify_action_deteriorated_scenario_requires_reopening(mock_gemini, action_service, verification_service):
    """
    Trigger verification with 'deteriorated' scenario.
    Ensures is_resolved=False, needs_reopening=True.
    """
    mock_gemini.return_value = {
        "what_changed": "Mobile payment completion rate dropped further to 14.50%.",
        "did_metric_improve": False,
        "did_it_meet_target": False,
        "possible_explanations": ["Rollback failed or backend gateway timeout cascaded."],
        "recommended_next_steps": ["Escalate to platform engineering and reopen investigation."],
        "causal_attribution_confidence": "unsubstantiated",
    }

    req = ActionCreateRequest(**SAMPLE_ACTION_PAYLOAD)
    action = action_service.create_action(req)
    action_service.approve_action(action.id, ActionApproveRequest(approver="Engineering Director"))
    verification_service.capture_baseline_for_action(action.id)

    trig_req = VerificationTriggerRequest(
        action_id=action.id,
        stage=VerificationStage.INITIAL,
        simulated_data_scenario="deteriorated",
    )
    run_res = verification_service.verify_action(trig_req)

    assert run_res.outcome == VerificationOutcome.DETERIORATED
    assert run_res.target_met is False
    assert run_res.is_resolved is False
    assert run_res.needs_reopening is True
    assert run_res.gemini_analysis.causal_attribution_confidence == "unsubstantiated"


MOCK_GEMINI_FOLLOWUP_PAYLOAD = {
    "what_changed": "Mobile payment completion rate surged to 75.20%, exceeding target.",
    "did_metric_improve": True,
    "did_it_meet_target": True,
    "possible_explanations": ["Frontend rollback eliminated JavaScript auto-focus crash on iOS Safari."],
    "recommended_next_steps": ["Maintain 48h active monitoring on mobile checkout logs."],
    "causal_attribution_confidence": "high",
}


# ============================================================================
# 4. Multi-Stage Verification, Diagnostic Notes & History
# ============================================================================

@patch("app.verification.service.generate_json", return_value=MOCK_GEMINI_FOLLOWUP_PAYLOAD)
def test_multi_stage_verification_and_notes(mock_gemini, action_service, verification_service):
    """
    Test initial, follow-up, and final stages, plus attaching diagnostic notes.
    """
    req = ActionCreateRequest(**SAMPLE_ACTION_PAYLOAD)
    action = action_service.create_action(req)
    action_service.approve_action(action.id, ActionApproveRequest(approver="Engineering Director"))
    verification_service.capture_baseline_for_action(action.id)

    # 1. Run Initial stage (e.g. current 65.0 - improved but target 74 unmet)
    run1 = verification_service.verify_action(
        VerificationTriggerRequest(
            action_id=action.id,
            stage=VerificationStage.INITIAL,
            current_value=65.0,
            evaluation_period="24-Hour Post-Fix Telemetry",
        )
    )
    assert run1.outcome == VerificationOutcome.IMPROVED
    assert run1.target_met is False
    assert run1.verification_stage == VerificationStage.INITIAL

    # 2. Add diagnostic note
    note = verification_service.add_verification_note(
        VerificationNoteCreateRequest(
            verification_id=run1.id,
            action_id=action.id,
            note="Partial recovery observed after component rollback. Waiting for CDN cache purge.",
            author="DevOps Lead",
        )
    )
    assert note.id is not None
    assert "CDN cache" in note.note

    # 3. Run Follow-up stage (e.g. current 75.5 - target met!)
    run2 = verification_service.verify_action(
        VerificationTriggerRequest(
            action_id=action.id,
            stage=VerificationStage.FOLLOW_UP,
            current_value=75.5,
            evaluation_period="7-Day Sustained Telemetry",
        )
    )
    assert run2.outcome == VerificationOutcome.IMPROVED
    assert run2.target_met is True
    assert run2.is_resolved is True

    # 4. Fetch complete history
    history = verification_service.get_verification_history(action.id)
    assert len(history.verification_runs) == 2
    assert len(history.notes) == 1
    assert "Resolved" in history.current_resolution_status


# ============================================================================
# 5. Failed Verification & Reopening Workflow
# ============================================================================

@patch("app.verification.service.generate_json", return_value=MOCK_GEMINI_FOLLOWUP_PAYLOAD)
def test_reopen_investigation_workflow(mock_gemini, action_service, verification_service):
    """
    When verification fails, reopening the investigation automatically creates
    a secondary action proposal with CRITICAL priority and diagnostic details.
    """
    req = ActionCreateRequest(**SAMPLE_ACTION_PAYLOAD)
    action = action_service.create_action(req)
    action_service.approve_action(action.id, ActionApproveRequest(approver="Engineering Director"))
    verification_service.capture_baseline_for_action(action.id)

    # Trigger failed verification
    run = verification_service.verify_action(
        VerificationTriggerRequest(
            action_id=action.id,
            simulated_data_scenario="not_improved",
        )
    )
    assert run.needs_reopening is True

    # Reopen investigation
    reopen_res = verification_service.reopen_investigation(
        ReopenInvestigationRequest(
            action_id=action.id,
            reason="Mobile completion remained flat at 22.1%. Secondary diagnosis required for backend gateway.",
            requested_by="Operations Director",
        )
    )

    assert reopen_res["status"] == "reopened"
    assert reopen_res["original_action_id"] == action.id
    new_act_id = reopen_res["new_action_id"]

    # Verify newly created follow-up proposal
    new_action = action_service.get_action(new_act_id)
    assert new_action.status == ActionStatus.PENDING_APPROVAL
    assert new_action.priority == ActionPriority.CRITICAL
    assert "[REOPENED]" in new_action.problem_description
    assert new_action.anomaly_id == action.anomaly_id


# ============================================================================
# 6. REST API Endpoints Integration Tests (TestClient)
# ============================================================================

@patch("app.verification.service.generate_json", return_value=MOCK_GEMINI_FOLLOWUP_PAYLOAD)
def test_api_verification_full_cycle(mock_gemini, client):
    """
    Test full HTTP API lifecycle:
    1. Create Proposal
    2. Approve Action -> Captures Baseline
    3. POST /api/verification/verify
    4. GET /api/verification/results/{action_id}
    5. POST /api/verification/notes
    6. GET /api/verification/history/{action_id}
    7. POST /api/verification/reopen
    """
    # 1. Create Proposal
    create_resp = client.post("/api/actions/propose", json=SAMPLE_ACTION_PAYLOAD)
    assert create_resp.status_code == 201
    action_id = create_resp.json()["id"]

    # 2. Approve Action
    approve_resp = client.post(f"/api/actions/{action_id}/approve", json={"approver": "Manager Dave"})
    assert approve_resp.status_code == 200

    # Check baseline capture endpoint
    base_resp = client.post("/api/verification/baseline", json={"action_id": action_id})
    assert base_resp.status_code == 201
    base_data = base_resp.json()
    assert base_data["action_id"] == action_id
    assert base_data["metric_name"] == "mobile_payment_completion_rate"
    assert base_data["baseline_value"] == 21.95

    # 3. Trigger Verification via API
    verify_resp = client.post(
        "/api/verification/verify",
        json={
            "action_id": action_id,
            "stage": "initial",
            "simulated_data_scenario": "improved",
        },
    )
    assert verify_resp.status_code == 200
    ver_data = verify_resp.json()
    assert ver_data["outcome"] == "Improved"
    assert ver_data["target_met"] is True
    assert ver_data["is_resolved"] is True
    ver_id = ver_data["id"]

    # 4. Get Latest Result
    result_resp = client.get(f"/api/verification/results/{action_id}")
    assert result_resp.status_code == 200
    assert result_resp.json()["id"] == ver_id

    # 5. Add Note
    note_resp = client.post(
        "/api/verification/notes",
        json={
            "verification_id": ver_id,
            "action_id": action_id,
            "note": "Payment success rates verified against Stripe gateway logs.",
            "author": "Billing Engineer",
        },
    )
    assert note_resp.status_code == 201

    # 6. Get History
    hist_resp = client.get(f"/api/verification/history/{action_id}")
    assert hist_resp.status_code == 200
    hist_data = hist_resp.json()
    assert len(hist_data["verification_runs"]) == 1
    assert len(hist_data["notes"]) == 1

    # 7. Reopen Investigation
    reopen_resp = client.post(
        "/api/verification/reopen",
        json={
            "action_id": action_id,
            "reason": "Secondary diagnostic validation requested by audit team.",
            "requested_by": "Audit Lead",
        },
    )
    assert reopen_resp.status_code == 200
    assert reopen_resp.json()["status"] == "reopened"
    assert reopen_resp.json()["new_action_id"].startswith("ACT-")


# ============================================================================
# 7. Phase 5 Step 2B: Verification Approval State Gate Tests
# ============================================================================


@patch("app.verification.service.generate_json", return_value=MOCK_GEMINI_FOLLOWUP_PAYLOAD)
def test_verification_gate_approved_action_can_be_verified(mock_gemini, client):
    """Test 1: Actions in 'Approved' status are eligible for verification."""
    # 1. Propose and approve action
    create_resp = client.post("/api/actions/propose", json=SAMPLE_ACTION_PAYLOAD)
    assert create_resp.status_code == 201
    action_id = create_resp.json()["id"]

    approve_resp = client.post(f"/api/actions/{action_id}/approve", json={"approver": "Director Alice"})
    assert approve_resp.status_code == 200
    assert approve_resp.json()["status"] == "Approved"

    # 2. Trigger verification
    verify_resp = client.post(
        "/api/verification/verify",
        json={"action_id": action_id, "simulated_data_scenario": "improved"},
    )
    assert verify_resp.status_code == 200
    ver_data = verify_resp.json()
    assert ver_data["action_id"] == action_id
    assert ver_data["outcome"] == "Improved"


@patch("app.verification.service.generate_json", return_value=MOCK_GEMINI_FOLLOWUP_PAYLOAD)
def test_verification_gate_in_progress_action_can_be_verified(mock_gemini, client):
    """Test 2: Actions in 'In Progress' status are eligible for verification."""
    # 1. Propose, approve, and move to In Progress
    create_resp = client.post("/api/actions/propose", json=SAMPLE_ACTION_PAYLOAD)
    action_id = create_resp.json()["id"]
    client.post(f"/api/actions/{action_id}/approve", json={"approver": "Director Alice"})

    patch_resp = client.patch(
        f"/api/tasks/{action_id}/status",
        json={"new_status": "In Progress"},
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["status"] == "In Progress"

    # 2. Trigger verification
    verify_resp = client.post(
        "/api/verification/verify",
        json={"action_id": action_id, "simulated_data_scenario": "improved"},
    )
    assert verify_resp.status_code == 200
    ver_data = verify_resp.json()
    assert ver_data["action_id"] == action_id
    assert ver_data["outcome"] == "Improved"


@patch("app.verification.service.generate_json", return_value=MOCK_GEMINI_FOLLOWUP_PAYLOAD)
def test_verification_gate_completed_action_can_be_verified(mock_gemini, client):
    """Test 3: Actions in 'Completed' status are eligible for verification."""
    # 1. Propose, approve, progress, and complete
    create_resp = client.post("/api/actions/propose", json=SAMPLE_ACTION_PAYLOAD)
    action_id = create_resp.json()["id"]
    client.post(f"/api/actions/{action_id}/approve", json={"approver": "Director Alice"})
    client.patch(f"/api/tasks/{action_id}/status", json={"new_status": "In Progress"})

    comp_resp = client.patch(
        f"/api/tasks/{action_id}/status",
        json={"new_status": "Completed", "completion_details": "Rollback completed and tested in staging."},
    )
    assert comp_resp.status_code == 200
    assert comp_resp.json()["status"] == "Completed"

    # 2. Trigger verification
    verify_resp = client.post(
        "/api/verification/verify",
        json={"action_id": action_id, "simulated_data_scenario": "improved"},
    )
    assert verify_resp.status_code == 200
    ver_data = verify_resp.json()
    assert ver_data["action_id"] == action_id
    assert ver_data["outcome"] == "Improved"


def test_verification_gate_pending_approval_rejected(client, action_service, verification_service):
    """Test 4: Actions in 'Pending Approval' are strictly rejected from verification."""
    # 1. Create proposal without approving
    req = ActionCreateRequest(**SAMPLE_ACTION_PAYLOAD)
    action = action_service.create_action(req)
    assert action.status == ActionStatus.PENDING_APPROVAL

    # 2. Attempt verification via HTTP API -> Expect 409 Conflict
    resp = client.post(
        "/api/verification/verify",
        json={"action_id": action.id, "simulated_data_scenario": "improved"},
    )
    assert resp.status_code == 409
    err_detail = resp.json()["detail"]
    assert "Pending Approval" in err_detail
    assert "Approved" in err_detail

    # 3. Direct service call raises InvalidActionStateForVerificationError
    with pytest.raises(InvalidActionStateForVerificationError, match="Pending Approval"):
        verification_service.verify_action(
            VerificationTriggerRequest(action_id=action.id, simulated_data_scenario="improved")
        )


def test_verification_gate_rejected_action_rejected(client, action_service, verification_service):
    """Test 5: Actions in 'Rejected' status are strictly rejected from verification."""
    # 1. Create proposal and reject it
    req = ActionCreateRequest(**SAMPLE_ACTION_PAYLOAD)
    action = action_service.create_action(req)
    rejected = action_service.reject_action(
        action.id, ActionRejectRequest(rejected_by="VP Operations", reason="Out of budget")
    )
    assert rejected.status == ActionStatus.REJECTED

    # 2. Attempt verification via HTTP API -> Expect 409 Conflict
    resp = client.post(
        "/api/verification/verify",
        json={"action_id": action.id, "simulated_data_scenario": "improved"},
    )
    assert resp.status_code == 409
    assert "Rejected" in resp.json()["detail"]

    # 3. Direct service call raises InvalidActionStateForVerificationError
    with pytest.raises(InvalidActionStateForVerificationError, match="Rejected"):
        verification_service.verify_action(
            VerificationTriggerRequest(action_id=action.id, simulated_data_scenario="improved")
        )


def test_verification_gate_invalid_action_id_returns_404(client, verification_service):
    """Test 6: Verifying a nonexistent action ID returns 404 Not Found."""
    fake_id = "ACT-DOES-NOT-EXIST-999"

    # HTTP API
    resp = client.post(
        "/api/verification/verify",
        json={"action_id": fake_id, "simulated_data_scenario": "improved"},
    )
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()

    # Direct service call
    with pytest.raises(ActionNotFoundError):
        verification_service.verify_action(
            VerificationTriggerRequest(action_id=fake_id, simulated_data_scenario="improved")
        )


def test_verification_gate_rejected_verification_creates_no_records(client, action_service, verification_service):
    """Test 7: A rejected verification attempt leaves no baseline or verification records."""
    # 1. Create proposal in Pending Approval
    req = ActionCreateRequest(**SAMPLE_ACTION_PAYLOAD)
    action = action_service.create_action(req)
    assert action.status == ActionStatus.PENDING_APPROVAL

    # 2. Attempt verification (rejected with 409)
    resp = client.post(
        "/api/verification/verify",
        json={"action_id": action.id, "simulated_data_scenario": "improved"},
    )
    assert resp.status_code == 409

    # 3. Assert baseline is None
    assert verification_service.get_baseline_for_action(action.id) is None

    # 4. Assert zero database records exist in metric_baselines and verification_runs
    conn = verification_service._get_conn()
    try:
        baselines = conn.execute(
            "SELECT * FROM metric_baselines WHERE action_id = ?", (action.id,)
        ).fetchall()
        assert len(baselines) == 0

        runs = conn.execute(
            "SELECT * FROM verification_runs WHERE action_id = ?", (action.id,)
        ).fetchall()
        assert len(runs) == 0

        verif_audits = conn.execute(
            "SELECT * FROM action_audit_log WHERE action_id = ? AND action_type IN ('BASELINE_CAPTURED', 'VERIFICATION_EXECUTED')",
            (action.id,),
        ).fetchall()
        assert len(verif_audits) == 0
    finally:
        conn.close()
