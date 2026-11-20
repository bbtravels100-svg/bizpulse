import sys
import json
import time
from pathlib import Path
from dotenv import load_dotenv

# Set pythonpath to backend root
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

load_dotenv(backend_dir / ".env")

from fastapi.testclient import TestClient
from app.main import app
from app.actions.models import ActionCreateRequest
from app.actions.service import default_action_service

client = TestClient(app)


def print_step(title: str):
    print("\n" + "=" * 80)
    print(f"STEP: {title}")
    print("=" * 80)


def main():
    print("=" * 80)
    print("BIZPULSE PHASE 3B: ACTION MANAGEMENT FULL LIFECYCLE DEMONSTRATION")
    print("=" * 80)

    # ------------------------------------------------------------------------
    # Step 1: Investigation & Multi-Agent Findings
    # ------------------------------------------------------------------------
    print_step("1. MULTI-AGENT ORCHESTRATION FINDINGS (ANOMALY_FUNNEL_MOBILE_001)")

    # Check if live or saved results are available
    saved_results_file = backend_dir / "scripts" / "live_multi_agent_results.json"
    orch_data = None

    # Try live endpoint first with a short timeout
    try:
        agent_resp = client.post("/api/agents/run", json={"anomaly_id": "ANOMALY_FUNNEL_MOBILE_001"})
        if agent_resp.status_code == 200:
            res_json = agent_resp.json()
            if res_json.get("status") == "completed" and res_json.get("final_action_brief"):
                orch_data = res_json
                print(f"✅ Live Multi-Agent Pipeline Completed (ID: {orch_data['orchestration_id']})")
    except Exception as e:
        print(f"Live API notice: {e}")

    # Fallback to verified saved results from previous live execution if DNS hiccup occurs
    if not orch_data and saved_results_file.exists():
        with open(saved_results_file, "r", encoding="utf-8") as f:
            saved = json.load(f)
            orch_data = saved.get("ANOMALY_FUNNEL_MOBILE_001")
            print(f"✅ Loaded Verified Multi-Agent Execution Results (ID: {orch_data['orchestration_id']})")

    assert orch_data is not None, "Could not obtain orchestration data."

    orch_id = orch_data["orchestration_id"]
    brief = orch_data["final_action_brief"]

    print(f"   Executive Summary: {brief['executive_summary']}")
    print(f"   Recommended Actions ({len(brief['recommended_action_plan'])} proposed by Writer Agent):")
    for idx, act in enumerate(brief["recommended_action_plan"], 1):
        print(f"     {idx}. {act}")

    # ------------------------------------------------------------------------
    # Step 2: Action Proposal Generation in SQLite
    # ------------------------------------------------------------------------
    print_step("2. TRANSFORMING AI RECOMMENDATIONS INTO STRUCTURED ACTION PROPOSALS")

    proposals = []
    for act_str in brief["recommended_action_plan"]:
        p_resp = client.post(
            "/api/actions/propose",
            json={
                "investigation_id": orch_id,
                "anomaly_id": "ANOMALY_FUNNEL_MOBILE_001",
                "problem_description": brief["problem_statement"],
                "recommended_action": act_str,
                "responsible_department": "Engineering",
                "suggested_owner_role": "Checkout Frontend Engineering Team",
                "priority": "Critical",
                "suggested_deadline": "2026-11-22",
                "expected_outcome": "Restore mobile payment completion rate to >= 74%.",
                "verification_criteria": "; ".join(brief["verification_and_success_criteria"]),
            }
        )
        assert p_resp.status_code == 201, f"Failed to propose action: {p_resp.text}"
        proposals.append(p_resp.json())

    print(f"✅ Generated {len(proposals)} persistent action proposals in SQLite database:")
    for p in proposals:
        print(f"   • Action ID: {p['id']} | Status: [{p['status'].upper()}] | Priority: {p['priority']}")
        print(f"     Action: {p['recommended_action']}")
        print(f"     Target Role: {p['suggested_owner_role']} ({p['responsible_department']})")
        print(f"     Suggested Deadline: {p['suggested_deadline']}")

    selected_action = proposals[0]
    action_id = selected_action["id"]

    # ------------------------------------------------------------------------
    # Step 3: Human Approval Workflow (Review & Edit Proposal)
    # ------------------------------------------------------------------------
    print_step(f"3. MANAGER REVIEW & EDIT PROPOSAL BEFORE APPROVAL ({action_id})")
    edit_resp = client.patch(
        f"/api/actions/{action_id}",
        json={
            "priority": "Critical",
            "suggested_deadline": "2026-11-21",
            "recommended_action": "Emergency Rollback: Revert checkout frontend to stable release v2.3.9 immediately."
        }
    )
    assert edit_resp.status_code == 200, f"Edit failed: {edit_resp.text}"
    edited_data = edit_resp.json()
    print(f"✅ Manager updated proposal before approval:")
    print(f"   Updated Action: {edited_data['recommended_action']}")
    print(f"   Updated Deadline: {edited_data['suggested_deadline']} (Priority: {edited_data['priority']})")
    print(f"   Status remains: {edited_data['status']} (Protected until approved)")

    # ------------------------------------------------------------------------
    # Step 4: Manager Approval Gate
    # ------------------------------------------------------------------------
    print_step(f"4. MANAGER APPROVAL GATE ({action_id})")
    approve_resp = client.post(
        f"/api/actions/{action_id}/approve",
        json={"approver": "Director of Engineering", "notes": "Authorized for emergency maintenance window"}
    )
    assert approve_resp.status_code == 200, f"Approval failed: {approve_resp.text}"
    approved_data = approve_resp.json()
    print(f"✅ Action Approved by Manager:")
    print(f"   Status: [{approved_data['status'].upper()}] (Transitioned from Pending Approval -> Approved)")

    # Verify that it now shows up in active tasks list
    active_tasks = client.get("/api/tasks").json()
    assert any(t["id"] == action_id for t in active_tasks)
    print(f"   Verified: Action '{action_id}' is now officially in active workflow tasks.")

    # ------------------------------------------------------------------------
    # Step 5: Transition to Active Task (In Progress)
    # ------------------------------------------------------------------------
    print_step(f"5. ENTERING ACTIVE TASK EXECUTION (IN PROGRESS)")
    in_prog_resp = client.patch(
        f"/api/tasks/{action_id}/status",
        json={"new_status": "In Progress", "notes": "Frontend team initiated container rollback to release v2.3.9"}
    )
    assert in_prog_resp.status_code == 200, f"Status update failed: {in_prog_resp.text}"
    in_prog_data = in_prog_resp.json()
    print(f"✅ Task is now actively executing:")
    print(f"   Status: [{in_prog_data['status'].upper()}]")

    # ------------------------------------------------------------------------
    # Step 6: Logging Progress Notes
    # ------------------------------------------------------------------------
    print_step(f"6. LOGGING THREADED PROGRESS NOTES & OBSERVATIONS")
    note1_resp = client.post(
        f"/api/tasks/{action_id}/notes",
        json={"note": "Canary traffic switched to v2.3.9. Mobile 504 timeouts dropping to zero.", "author": "Site Reliability Engineer"}
    )
    note2_resp = client.post(
        f"/api/tasks/{action_id}/notes",
        json={"note": "100% production traffic restored to v2.3.9. Monitoring real-time telemetry.", "author": "Checkout Tech Lead"}
    )
    assert note1_resp.status_code == 201
    assert note2_resp.status_code == 201
    print(f"✅ Appended 2 progress notes:")
    print(f"   Note 1: {note1_resp.json()['note']} (by {note1_resp.json()['author']})")
    print(f"   Note 2: {note2_resp.json()['note']} (by {note2_resp.json()['author']})")

    # ------------------------------------------------------------------------
    # Step 7: Completion of Active Task
    # ------------------------------------------------------------------------
    print_step(f"7. COMPLETING TASK & RECORDING COMPLETION DETAILS")
    comp_resp = client.patch(
        f"/api/tasks/{action_id}/status",
        json={
            "new_status": "Completed",
            "completion_details": "Rollback to v2.3.9 completed successfully. Mobile payment completion rate returned to baseline 75.1% across iOS & Android devices. Zero new 504 timeouts logged in past 6 hours.",
            "notes": "Verified by QA Lead and Operations Director"
        }
    )
    assert comp_resp.status_code == 200, f"Completion failed: {comp_resp.text}"
    comp_data = comp_resp.json()
    print(f"✅ Task Completed:")
    print(f"   Status: [{comp_data['status'].upper()}]")
    print(f"   Completed At: {comp_data['completed_at']}")
    print(f"   Completion Details: {comp_data['completion_details']}")

    # Verify invalid transition: Completed is terminal
    invalid_resp = client.patch(
        f"/api/tasks/{action_id}/status",
        json={"new_status": "In Progress"}
    )
    assert invalid_resp.status_code == 400
    print(f"   Verified: Attempting to move Completed task back to In Progress correctly blocked with HTTP 400.")

    # ------------------------------------------------------------------------
    # Step 8: Complete Audit History & Persistence Verification
    # ------------------------------------------------------------------------
    print_step(f"8. COMPLETE AUDIT TRAIL VERIFICATION")
    hist_resp = client.get(f"/api/tasks/{action_id}/history")
    assert hist_resp.status_code == 200
    hist = hist_resp.json()
    print(f"✅ Audit Log for Action {action_id} ({len(hist['audit_log'])} historical events):")
    for idx, event in enumerate(hist["audit_log"], 1):
        prev = f" (from {event['previous_value']})" if event['previous_value'] else ""
        new = f" -> {event['new_value']}" if event['new_value'] else ""
        print(f"   {idx}. [{event['timestamp']}] {event['action_type']}{prev}{new}")
        if event['details']:
            print(f"      Details: {event['details']}")

    print("\n" + "=" * 80)
    print("🎉 FULL LIFECYCLE DEMONSTRATION VERIFIED SUCCESSFULLY IN SQLITE!")
    print("=" * 80)


if __name__ == "__main__":
    main()
