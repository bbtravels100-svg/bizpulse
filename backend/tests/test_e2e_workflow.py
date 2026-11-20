import os
import shutil
import tempfile
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from app.main import app
from app.actions.models import (
    ActionStatus,
    ActionPriority,
    ActionCreateRequest,
    ActionApproveRequest,
    ActionRejectRequest,
    TaskStatusUpdateRequest,
    TaskAssignmentUpdateRequest,
    ProgressNoteCreateRequest,
)
from app.actions.database import init_db
from app.actions.service import ActionService, ActionNotFoundError, InvalidStatusTransitionError
from app.verification.models import (
    VerificationOutcome,
    VerificationStage,
    VerificationTriggerRequest,
    ReopenInvestigationRequest,
)
from app.verification.service import (
    VerificationService,
    InvalidActionStateForVerificationError,
)
from app.agents.models import (
    AnalystOutput,
    ConnectorOutput,
    RouterOutput,
    WriterOutput,
    StageResult,
    OrchestrationStages,
    OrchestrationResponse,
)
from app.agents.orchestrator import run_agent_pipeline
from app.analytics.data_loader import get_data_path, load_sales_data
from app.analytics.sales_analytics import get_total_revenue
from app.analytics.dataset_tracker import default_dataset_tracker
from app.services.investigation_service import extract_mobile_payment_facts


# Deterministic Mock Outputs for 4-Agent Pipeline
MOCK_ANALYST_RAW = {
    "key_metrics_validated": [
        "Mobile payment completion crashed from 74.98% to 21.95% (-70.73% relative drop)",
        "Desktop payment completion steady at 74.97%",
        "Weekly revenue fell -$15,300 (-18.00%)",
    ],
    "patterns_identified": ["Isolated entirely to mobile user experience following Nov 8 deployment."],
    "analytical_summary": "Technical defect in checkout bundle specifically degrading mobile payments.",
    "severity_assessment": "critical",
}

MOCK_CONNECTOR_RAW = {
    "cross_department_connections": [
        {
            "departments_involved": ["Technology / Engineering", "Sales / Finance"],
            "connection_type": "evidence_backed",
            "finding": "Checkout deployment on Nov 8 coincides with 504 gateway timeouts.",
            "supporting_evidence": ["Deployment timestamp 2026-11-08T02:15:00Z"],
        }
    ],
    "collaboration_rationale": "Engineering must deploy hotfix; Support must assist affected buyers.",
}

MOCK_ROUTER_RAW = {
    "primary_department": "Engineering",
    "collaborating_departments": ["Customer Support"],
    "recommended_role_or_team": "Checkout Frontend Engineering Team",
    "priority": "Critical",
    "suggested_next_action": "Initiate immediate rollback of checkout frontend release v2.4.0.",
    "routing_justification": "Root cause isolated to client-side Javascript error in mobile bundle.",
}

MOCK_WRITER_RAW = {
    "executive_summary": "Mobile payment completion plummeted 70.73% after Nov 8 deployment.",
    "problem_statement": "Mobile checkout conversion collapsed from 74.98% to 21.95% in Week 2.",
    "confirmed_evidence": ["Mobile payment completion down to 21.95%", "Gateway 504 timeouts logged"],
    "likely_causes": ["Client-side Javascript crash in mobile payment sheet form validation"],
    "target_team_and_priority": "Checkout Frontend Engineering Team - Critical",
    "recommended_action_plan": [
        "Roll back mobile checkout sheet component to v2.3.9",
        "Purge mobile CDN asset cache and verify telemetry",
    ],
    "verification_and_success_criteria": [
        "Mobile payment completion returns to baseline >= 74.00%",
        "Zero payment gateway 504 errors in checkout funnel",
    ],
}

MOCK_GEMINI_FOLLOWUP_IMPROVED = {
    "what_changed": "Mobile payment completion rate surged from 21.95% to 75.20%, exceeding baseline target.",
    "did_metric_improve": True,
    "did_it_meet_target": True,
    "possible_explanations": ["Frontend rollback eliminated JavaScript auto-focus crash on iOS Safari."],
    "recommended_next_steps": ["Maintain 48h active monitoring on mobile checkout logs."],
    "causal_attribution_confidence": "high",
}

MOCK_GEMINI_FOLLOWUP_DETERIORATED = {
    "what_changed": "Mobile payment completion rate dropped further to 14.50%. Target unmet.",
    "did_metric_improve": False,
    "did_it_meet_target": False,
    "possible_explanations": ["Rollback failed to propagate or backend payment gateway outage persisted."],
    "recommended_next_steps": ["Escalate to platform engineering and reopen investigation."],
    "causal_attribution_confidence": "unsubstantiated",
}


@pytest.fixture
def temp_db():
    """Create isolated temporary SQLite database for testing."""
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
def e2e_client(temp_db):
    """TestClient wired to isolated database with mocked Gemini operations."""
    test_act_svc = ActionService(db_path=temp_db)
    test_ver_svc = VerificationService(db_path=temp_db, action_service=test_act_svc)

    with patch("app.actions.router.default_action_service", test_act_svc), \
         patch("app.actions.service.default_action_service", test_act_svc), \
         patch("app.verification.router.default_verification_service", test_ver_svc), \
         patch("app.verification.service.default_verification_service", test_ver_svc), \
         patch("app.verification.service.default_action_service", test_act_svc):
        yield TestClient(app)


# ============================================================================
# Scenario A: Successful Remediation (Detect -> Explain -> Recommend -> Approve -> Assign -> Follow Up -> Verify -> Close)
# ============================================================================

def test_scenario_a_successful_remediation_lifecycle(e2e_client, temp_db):
    """
    Complete end-to-end business remediation lifecycle:
    1. Detect anomaly from analytics engine
    2. Run 4-agent orchestration (Analyst -> Connector -> Router -> Writer)
    3. Generate action proposals
    4. Approve proposal (captures immutable baseline)
    5. Reassign task and update suggested deadline
    6. Transition task to In Progress and add progress notes
    7. Complete task with remediation details
    8. Run verification with improved metrics
    9. Confirm problem resolved, target met, and audit history recorded
    """
    # 1. Detect Anomaly
    anomalies_resp = e2e_client.get("/api/anomalies")
    assert anomalies_resp.status_code == 200
    anomalies_data = anomalies_resp.json()
    anomalies = anomalies_data.get("anomalies", [])
    assert len(anomalies) > 0
    funnel_anomaly = next((a for a in anomalies if a.get("anomaly_id") == "ANOMALY_FUNNEL_MOBILE_001"), None)
    assert funnel_anomaly is not None
    assert funnel_anomaly["severity"] == "critical"

    # 2. Run 4-Agent Orchestration & 3. Generate Recommendations
    with patch("app.agents.roles.generate_json", side_effect=[
        MOCK_ANALYST_RAW, MOCK_CONNECTOR_RAW, MOCK_ROUTER_RAW, MOCK_WRITER_RAW
    ]):
        orch_resp = e2e_client.post("/api/agents/run", json={"anomaly_id": "ANOMALY_FUNNEL_MOBILE_001"})
        assert orch_resp.status_code == 200
        orch_data = orch_resp.json()
        assert orch_data["status"] == "completed"
        assert len(orch_data["final_action_brief"]["recommended_action_plan"]) == 2

    # 4. Generate Proposals from Orchestration
    # Mock orchestrator inside /api/actions/generate
    mock_orch_obj = OrchestrationResponse(
        orchestration_id=orch_data["orchestration_id"],
        anomaly_id="ANOMALY_FUNNEL_MOBILE_001",
        status="completed",
        facts=extract_mobile_payment_facts(),
        stages=OrchestrationStages(
            analyst=StageResult(agent_name="Analyst", status="completed", duration_ms=20),
            connector=StageResult(agent_name="Connector", status="completed", duration_ms=25),
            router=StageResult(agent_name="Router", status="completed", duration_ms=15, output=RouterOutput(**MOCK_ROUTER_RAW)),
            writer=StageResult(agent_name="Writer", status="completed", duration_ms=30, output=WriterOutput(**MOCK_WRITER_RAW)),
        ),
        final_action_brief=WriterOutput(**MOCK_WRITER_RAW),
        total_duration_ms=90,
        model_used="gemini-mock",
        created_at="2026-11-20T10:00:00Z",
    )

    with patch("app.actions.router.default_orchestrator.run", return_value=mock_orch_obj):
        gen_resp = e2e_client.post("/api/actions/generate", json={"anomaly_id": "ANOMALY_FUNNEL_MOBILE_001"})
        assert gen_resp.status_code == 201
        proposals = gen_resp.json()
        assert len(proposals) == 2
        for p in proposals:
            assert p["status"] == ActionStatus.PENDING_APPROVAL.value
            assert p["anomaly_id"] == "ANOMALY_FUNNEL_MOBILE_001"

    action_id = proposals[0]["id"]

    # 5. Approve Proposal
    approve_resp = e2e_client.post(
        f"/api/actions/{action_id}/approve",
        json={"approver": "VP Engineering", "notes": "Authorized emergency rollback."},
    )
    assert approve_resp.status_code == 200
    assert approve_resp.json()["status"] == ActionStatus.APPROVED.value

    # Verify baseline was automatically recorded upon approval
    hist_resp = e2e_client.get(f"/api/verification/history/{action_id}")
    assert hist_resp.status_code == 200
    hist_data = hist_resp.json()
    assert hist_data["baseline"] is not None
    assert hist_data["baseline"]["metric_name"] == "mobile_payment_completion_rate"
    assert hist_data["baseline"]["baseline_value"] == 21.95
    assert hist_data["baseline"]["target_value"] == 74.00

    # 6. Assign Task & Update Deadline
    assign_resp = e2e_client.patch(
        f"/api/tasks/{action_id}/assignment",
        json={
            "responsible_department": "Core Platform Engineering",
            "suggested_owner_role": "Release Incident Commander",
            "suggested_deadline": "2026-11-22",
            "reason": "Escalated for immediate staging verification",
        },
    )
    assert assign_resp.status_code == 200
    assert assign_resp.json()["responsible_department"] == "Core Platform Engineering"

    # 7. Move Task to In Progress & Add Progress Notes
    status_resp = e2e_client.patch(
        f"/api/tasks/{action_id}/status",
        json={"new_status": "In Progress"},
    )
    assert status_resp.status_code == 200
    assert status_resp.json()["status"] == "In Progress"

    note_resp = e2e_client.post(
        f"/api/tasks/{action_id}/notes",
        json={"note": "Rollback PR merged; deploying to cluster.", "author": "Commander Dave"},
    )
    assert note_resp.status_code == 201

    # 8. Complete Task
    comp_resp = e2e_client.patch(
        f"/api/tasks/{action_id}/status",
        json={
            "new_status": "Completed",
            "completion_details": "Rollback completed. Invalidation sent to edge proxies.",
        },
    )
    assert comp_resp.status_code == 200
    assert comp_resp.json()["status"] == "Completed"

    # 9. Run Verification (Simulated improved scenario)
    with patch("app.verification.service.generate_json", return_value=MOCK_GEMINI_FOLLOWUP_IMPROVED):
        ver_resp = e2e_client.post(
            "/api/verification/verify",
            json={
                "action_id": action_id,
                "stage": "initial",
                "simulated_data_scenario": "improved",
            },
        )
        assert ver_resp.status_code == 200
        ver_data = ver_resp.json()

        # 10. Confirm outcome correctly recorded
        assert ver_data["outcome"] == "Improved"
        assert ver_data["target_met"] is True
        assert ver_data["is_resolved"] is True
        assert ver_data["needs_reopening"] is False
        assert ver_data["comparison"]["current_value"] == 75.20

    # Verify audit history
    audit_resp = e2e_client.get(f"/api/tasks/{action_id}/history")
    assert audit_resp.status_code == 200
    full_history = audit_resp.json()
    action_types = [entry["action_type"] for entry in full_history["audit_log"]]
    assert "PROPOSAL_CREATED" in action_types
    assert "ACTION_APPROVED" in action_types
    assert "BASELINE_CAPTURED" in action_types
    assert "STATUS_UPDATED" in action_types
    assert "PROGRESS_NOTE_ADDED" in action_types
    assert "VERIFICATION_EVALUATED" in action_types


# ============================================================================
# Scenario B: Rejected Proposal (Rejection & State Protection)
# ============================================================================

def test_scenario_b_rejected_proposal_cannot_be_verified(e2e_client):
    """
    Proposal rejected by management cannot enter execution or verification:
    1. Create action proposal
    2. Reject proposal with mandatory reason
    3. Verify status is Rejected
    4. Attempt to verify -> Blocked with HTTP 409 Conflict
    5. Verify no baseline or verification runs exist
    """
    create_resp = e2e_client.post(
        "/api/actions/propose",
        json={
            "investigation_id": "ORCH-REJECT-001",
            "anomaly_id": "ANOMALY_FUNNEL_MOBILE_001",
            "problem_description": "Mobile conversion dropped.",
            "recommended_action": "Disable mobile cart checkout completely.",
            "responsible_department": "Engineering",
            "suggested_owner_role": "Backend Lead",
            "priority": "Low",
            "suggested_deadline": "2026-11-30",
            "expected_outcome": "Prevent orders",
            "verification_criteria": "Orders drop to zero",
        },
    )
    assert create_resp.status_code == 201
    action_id = create_resp.json()["id"]

    # Reject proposal
    reject_resp = e2e_client.post(
        f"/api/actions/{action_id}/reject",
        json={"rejected_by": "Director Ops", "reason": "Disabling checkout harms the business."},
    )
    assert reject_resp.status_code == 200
    assert reject_resp.json()["status"] == ActionStatus.REJECTED.value
    assert reject_resp.json()["rejection_reason"] == "Disabling checkout harms the business."

    # Verification must be blocked
    verify_resp = e2e_client.post(
        "/api/verification/verify",
        json={"action_id": action_id, "simulated_data_scenario": "improved"},
    )
    assert verify_resp.status_code == 409
    assert "Rejected" in verify_resp.json()["detail"]

    # History must show 0 baselines and 0 verification runs
    hist_resp = e2e_client.get(f"/api/verification/history/{action_id}")
    assert hist_resp.status_code == 404  # Baseline never created


# ============================================================================
# Scenario C: Duplicate Investigation Idempotency
# ============================================================================

def test_scenario_c_duplicate_investigation_idempotency(e2e_client):
    """
    Running the same investigation or proposal generation repeatedly does not create duplicates.
    """
    mock_orch = OrchestrationResponse(
        orchestration_id="ORCH-IDEM-001",
        anomaly_id="ANOMALY_FUNNEL_MOBILE_001",
        status="completed",
        facts=extract_mobile_payment_facts(),
        stages=OrchestrationStages(
            analyst=StageResult(agent_name="Analyst", status="completed", duration_ms=20),
            connector=StageResult(agent_name="Connector", status="completed", duration_ms=25),
            router=StageResult(agent_name="Router", status="completed", duration_ms=15, output=RouterOutput(**MOCK_ROUTER_RAW)),
            writer=StageResult(agent_name="Writer", status="completed", duration_ms=30, output=WriterOutput(**MOCK_WRITER_RAW)),
        ),
        final_action_brief=WriterOutput(**MOCK_WRITER_RAW),
        total_duration_ms=90,
        model_used="gemini-mock",
        created_at="2026-11-20T10:00:00Z",
    )

    with patch("app.actions.router.default_orchestrator.run", return_value=mock_orch):
        # Call 1
        res1 = e2e_client.post("/api/actions/generate")
        assert res1.status_code == 201
        ids1 = [a["id"] for a in res1.json()]

        # Call 2
        res2 = e2e_client.post("/api/actions/generate")
        assert res2.status_code == 201
        ids2 = [a["id"] for a in res2.json()]

        # IDs must match
        assert ids1 == ids2

        # Proposals in database must remain exactly 2
        proposals = e2e_client.get("/api/actions/proposals").json()
        assert len(proposals) == 2


# ============================================================================
# Scenario D: Failed Remediation & Reopening
# ============================================================================

def test_scenario_d_failed_remediation_and_reopening(e2e_client):
    """
    Task completion does not equal problem resolution:
    1. Complete action
    2. Verification detects deteriorated metrics (target unmet)
    3. Reopen investigation creates secondary diagnostic proposal
    """
    # 1. Propose, approve, complete
    create_resp = e2e_client.post(
        "/api/actions/propose",
        json={
            "investigation_id": "ORCH-FAIL-001",
            "anomaly_id": "ANOMALY_FUNNEL_MOBILE_001",
            "problem_description": "Mobile payment timeout surge.",
            "recommended_action": "Tune server keep-alive timeouts.",
            "responsible_department": "Engineering",
            "suggested_owner_role": "DevOps",
            "priority": "High",
            "suggested_deadline": "2026-11-24",
            "expected_outcome": "Reduce timeouts",
            "verification_criteria": "Mobile payment completion >= 74%",
        },
    )
    action_id = create_resp.json()["id"]
    e2e_client.post(f"/api/actions/{action_id}/approve", json={"approver": "Director Alice"})
    e2e_client.patch(f"/api/tasks/{action_id}/status", json={"new_status": "In Progress"})
    e2e_client.patch(
        f"/api/tasks/{action_id}/status",
        json={"new_status": "Completed", "completion_details": "Keep-alive parameters adjusted."},
    )

    # 2. Run verification with deteriorated scenario
    with patch("app.verification.service.generate_json", return_value=MOCK_GEMINI_FOLLOWUP_DETERIORATED):
        ver_resp = e2e_client.post(
            "/api/verification/verify",
            json={"action_id": action_id, "simulated_data_scenario": "deteriorated"},
        )
        assert ver_resp.status_code == 200
        ver_data = ver_resp.json()
        assert ver_data["outcome"] == "Deteriorated"
        assert ver_data["is_resolved"] is False
        assert ver_data["needs_reopening"] is True

    # 3. Reopen investigation
    reopen_resp = e2e_client.post(
        "/api/verification/reopen",
        json={
            "action_id": action_id,
            "reason": "Keep-alive adjustment failed to resolve gateway timeouts. Investigating database lock contention.",
            "requested_by": "Incident Manager",
        },
    )
    assert reopen_resp.status_code == 200
    reopen_data = reopen_resp.json()
    assert reopen_data["status"] == "reopened"
    new_act_id = reopen_data["new_action_id"]

    # Verify new proposal
    new_act = e2e_client.get(f"/api/actions/{new_act_id}").json()
    assert new_act["status"] == ActionStatus.PENDING_APPROVAL.value
    assert new_act["priority"] == ActionPriority.CRITICAL.value
    assert "[REOPENED]" in new_act["problem_description"]


# ============================================================================
# Scenario E: Dataset Changes & Invalidation
# ============================================================================

def test_scenario_e_dataset_replacement_and_freshness(e2e_client):
    """
    Dataset upload updates version, notifies tracker, and updates downstream calculations:
    1. Check initial version
    2. Upload valid replacement
    3. Verify version increments and reload timestamp recorded
    4. Confirm subsequent analytics use updated numbers
    5. Verify failed upload leaves dataset untouched
    """
    sales_path = get_data_path("sales.csv")
    backup_path = sales_path + ".e2e_bak"
    shutil.copyfile(sales_path, backup_path)

    try:
        init_summary = e2e_client.get("/api/datasets/sales").json()
        init_ver = init_summary.get("version", 1)

        # 1. Successful upload
        new_content = """date,product_id,product_name,units_sold,revenue
2026-11-01,PROD_001,Ultra Ergonomic Desk Chair,5,1750.00
2026-11-02,PROD_002,Noise-Cancelling Headphones,10,1800.00"""

        up_resp = e2e_client.post(
            "/api/datasets/sales/upload",
            json={"filename": "sales.csv", "content": new_content},
        )
        assert up_resp.status_code == 200
        up_data = up_resp.json()
        assert up_data["version"] == init_ver + 1
        assert up_data["reloaded_at"] is not None

        # 2. Subsequent analytics reflect new data
        df_new = load_sales_data(sales_path)
        assert get_total_revenue(df_new) == 3550.00

        # 3. Failed upload leaves version and file unchanged
        bad_csv = "date,units_sold\n2026-11-01,5"
        fail_resp = e2e_client.post(
            "/api/datasets/sales/upload",
            json={"filename": "sales.csv", "content": bad_csv},
        )
        assert fail_resp.status_code == 400

        curr_ver = default_dataset_tracker.get_version_info("sales").version
        assert curr_ver == init_ver + 1
    finally:
        shutil.copyfile(backup_path, sales_path)
        if os.path.exists(backup_path):
            os.remove(backup_path)
        if os.path.exists(sales_path + ".bak"):
            os.remove(sales_path + ".bak")


# ============================================================================
# Scenario F: Persistence Across Re-initialization
# ============================================================================

def test_scenario_f_database_persistence_across_restarts(temp_db):
    """
    Verify actions, tasks, notes, baselines, and verifications persist across service restarts:
    1. Service Instance 1 creates and progresses action
    2. Service Instance 2 re-opens database and verifies records are intact
    """
    # Instance 1
    svc1_act = ActionService(db_path=temp_db)
    svc1_ver = VerificationService(db_path=temp_db, action_service=svc1_act)

    act = svc1_act.create_action(
        ActionCreateRequest(
            investigation_id="ORCH-PERSIST-001",
            anomaly_id="ANOMALY_FUNNEL_MOBILE_001",
            problem_description="Persistence test problem.",
            recommended_action="Deploy DB persistence check.",
            responsible_department="Engineering",
            suggested_owner_role="Lead Architect",
            priority=ActionPriority.HIGH,
            suggested_deadline="2026-11-25",
            expected_outcome="All records persist",
            verification_criteria="Queries return identical data",
        )
    )
    svc1_act.approve_action(act.id, ActionApproveRequest(approver="CTO"))
    svc1_act.add_progress_note(act.id, ProgressNoteCreateRequest(note="Service running smoothly.", author="Architect"))

    # Instance 2 (simulate process restart)
    svc2_act = ActionService(db_path=temp_db)
    svc2_ver = VerificationService(db_path=temp_db, action_service=svc2_act)

    loaded_act = svc2_act.get_action(act.id)
    assert loaded_act.status == ActionStatus.APPROVED
    assert loaded_act.suggested_owner_role == "Lead Architect"

    history = svc2_act.get_action_history(act.id)
    assert len(history.notes) == 1
    assert history.notes[0].note == "Service running smoothly."
    assert len(history.audit_log) >= 2

    # Baseline persists
    baseline = svc2_ver.get_baseline_for_action(act.id)
    assert baseline is not None
    assert baseline.metric_name == "mobile_payment_completion_rate"


# ============================================================================
# Failure Handling & Negative Path Testing
# ============================================================================

def test_failure_handling_invalid_status_transitions(e2e_client):
    """Proposals in Pending Approval cannot skip approval to In Progress or Completed."""
    create_resp = e2e_client.post(
        "/api/actions/propose",
        json={
            "investigation_id": "ORCH-FAIL-TRANS-001",
            "anomaly_id": "ANOMALY_FUNNEL_MOBILE_001",
            "problem_description": "Direct transition test.",
            "recommended_action": "Invalid jump.",
            "responsible_department": "Engineering",
            "suggested_owner_role": "Tester",
            "priority": "Low",
            "suggested_deadline": "2026-11-30",
            "expected_outcome": "Fail",
            "verification_criteria": "Fail",
        },
    )
    action_id = create_resp.json()["id"]

    # Attempt to jump straight to In Progress -> 400
    jump_resp = e2e_client.patch(
        f"/api/tasks/{action_id}/status",
        json={"new_status": "In Progress"},
    )
    assert jump_resp.status_code == 400
    assert "Invalid status transition" in jump_resp.json()["detail"]

    # Attempt to jump straight to Completed -> 400
    comp_resp = e2e_client.patch(
        f"/api/tasks/{action_id}/status",
        json={"new_status": "Completed"},
    )
    assert comp_resp.status_code == 400


def test_failure_handling_nonexistent_records(e2e_client):
    """Querying or verifying non-existent action returns 404."""
    fake_id = "ACT-DOES-NOT-EXIST-000"
    assert e2e_client.get(f"/api/actions/{fake_id}").status_code == 404
    assert e2e_client.get(f"/api/tasks/{fake_id}/history").status_code == 404
    assert e2e_client.post(
        "/api/verification/verify", json={"action_id": fake_id, "simulated_data_scenario": "improved"}
    ).status_code == 404
