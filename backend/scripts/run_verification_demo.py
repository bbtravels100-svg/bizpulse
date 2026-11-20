import os
import sys
import json
from pathlib import Path
from dotenv import load_dotenv

# Ensure backend root is in sys.path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))
load_dotenv(backend_dir / ".env")

from app.actions.database import init_db
from app.actions.models import ActionCreateRequest, ActionApproveRequest, ActionPriority
from app.actions.service import default_action_service
from app.verification.models import (
    VerificationStage,
    VerificationTriggerRequest,
    VerificationNoteCreateRequest,
    ReopenInvestigationRequest,
)
from app.verification.service import default_verification_service


def print_header(title: str):
    print("\n" + "=" * 80)
    print(f" {title}")
    print("=" * 80)


def print_section(title: str):
    print(f"\n--- {title} ---")


def main():
    print_header("BIZPULSE PHASE 3C: FOLLOW-UP AND VERIFICATION ENGINE LIVE DEMO")
    print("Objective: Verify whether completed business actions actually improve business problems.")
    print("Rule: Task completion != Problem resolution. Deterministic Python math + Gemini interpretation.")

    # 1. Initialize SQLite Store
    init_db()

    # 2. Planted Business Problem: Mobile Payment Funnel Deterioration
    print_section("STEP 1: Create Action Proposal for Planted Anomaly")
    anomaly_id = "ANOMALY_FUNNEL_MOBILE_001"
    create_req = ActionCreateRequest(
        investigation_id="ORCH-DEMO-3C-001",
        anomaly_id=anomaly_id,
        problem_description=(
            "Mobile payment completion plummeted from 75.2% to 21.95% after website update v2.4.0. "
            "Desktop conversion remained steady at 81.3%."
        ),
        recommended_action=(
            "Roll back frontend mobile payment sheet component from v2.4.0 to v2.3.9 "
            "and fix iOS Safari touch event listener memory leak."
        ),
        responsible_department="Engineering",
        suggested_owner_role="Mobile Frontend Lead",
        priority=ActionPriority.CRITICAL,
        suggested_deadline="2026-11-25",
        expected_outcome="Restore mobile payment completion rate to >= 74.00% without timeouts.",
        verification_criteria="Mobile payment completion recovers to >= 74.0% with zero payment gateway 504 timeouts.",
    )
    action = default_action_service.create_action(create_req)
    print(f" Action Proposal Created: {action.id}")
    print(f"   - Anomaly: {action.anomaly_id}")
    print(f"   - Status:  {action.status.value}")
    print(f"   - Action:  {action.recommended_action}")

    # 3. Manager Approval & Automatic Baseline Capture
    print_section("STEP 2: Manager Approval & Automatic Baseline Capture")
    approved_action = default_action_service.approve_action(
        action.id,
        ActionApproveRequest(approver="VP of Engineering", notes="Approved for immediate staging deploy and verification."),
    )
    print(f" Action Approved: {approved_action.id} -> Status: {approved_action.status.value}")

    baseline = default_verification_service.get_baseline_for_action(action.id)
    assert baseline is not None, "Baseline should be captured automatically upon approval"
    print(f" Immutable Baseline Captured: {baseline.id}")
    print(f"   - Metric:       {baseline.metric_name}")
    print(f"   - Baseline Val: {baseline.baseline_value}% ({baseline.baseline_period})")
    print(f"   - Target Val:   >= {baseline.target_value}%")
    print(f"   - Captured At:  {baseline.captured_at}")

    # 4. Stage 1: Initial Verification (Partial Recovery, Target Unmet)
    print_section("STEP 3: Stage 1 - Initial Verification (24h Post-Action)")
    print("Simulated telemetry scenario: Metric improved to 58.40%, but target (74.00%) not yet met.")
    run_initial = default_verification_service.verify_action(
        VerificationTriggerRequest(
            action_id=action.id,
            stage=VerificationStage.INITIAL,
            current_value=58.40,
            evaluation_period="Post-Fix 24-Hour Telemetry",
        )
    )
    comp1 = run_initial.comparison
    print(f" Verification Run: {run_initial.id}")
    print(f"   - Stage:          {run_initial.verification_stage.value}")
    print(f"   - Baseline:       {comp1.baseline_value}% -> Current: {comp1.current_value}%")
    print(f"   - Absolute Move:  {comp1.absolute_change:+0.2f}%")
    print(f"   - Relative Move:  {comp1.percentage_change:+0.2f}%")
    print(f"   - Target Met:     {run_initial.target_met} (Target: {comp1.target_value}%)")
    print(f"   - Outcome:        {run_initial.outcome.value}")
    print(f"   - Resolved?:      {run_initial.is_resolved} (Task Completed != Resolved!)")
    print(f"   - Needs Reopen?:  {run_initial.needs_reopening}")

    if run_initial.gemini_analysis:
        print(f"   - Gemini Insight: {run_initial.gemini_analysis.what_changed}")
        print(f"   - Attribution:    Confidence={run_initial.gemini_analysis.causal_attribution_confidence}")

    # 5. Add Diagnostic Note
    print_section("STEP 4: Attach Diagnostic Operations Note")
    note = default_verification_service.add_verification_note(
        VerificationNoteCreateRequest(
            verification_id=run_initial.id,
            action_id=action.id,
            note="Partial recovery observed after component rollback. Waiting for CDN cache TTL expiry.",
            author="DevOps Lead",
        )
    )
    print(f" Diagnostic Note Logged: ID={note.id} by {note.author}")
    print(f"   Note: '{note.note}'")

    # 6. Stage 2: Handling Deterioration / Reopening Workflow
    print_section("STEP 5: Handling Failed Verification & Investigation Reopening")
    print("Simulating a temporary regression where telemetry slips to 18.20% (Deteriorated)...")
    run_failed = default_verification_service.verify_action(
        VerificationTriggerRequest(
            action_id=action.id,
            stage=VerificationStage.MANUAL,
            current_value=18.20,
            evaluation_period="Mid-Week Diagnostic Probe",
        )
    )
    print(f" Run Outcome: {run_failed.outcome.value} (Needs Reopening: {run_failed.needs_reopening})")
    print(" Triggering formal reopening workflow...")
    reopen_result = default_verification_service.reopen_investigation(
        ReopenInvestigationRequest(
            action_id=action.id,
            reason="Telemetry deteriorated to 18.20%. Mobile payment gateway timeout persisted on legacy webview.",
            requested_by="QA Director",
        )
    )
    print(f" Investigation Reopened: Status={reopen_result['status']}")
    print(f"   - New Proposal ID: {reopen_result['new_action_id']}")
    print(f"   - Priority:        {reopen_result['new_action_proposal'].priority.value}")
    print(f"   - Description:     {reopen_result['new_action_proposal'].problem_description}")

    # 7. Stage 3: Final Follow-up Verification (Full Resolution)
    print_section("STEP 6: Final Verification Run (Target Fully Met)")
    print("Simulating final verified recovery telemetry: Current = 76.10%...")
    run_final = default_verification_service.verify_action(
        VerificationTriggerRequest(
            action_id=action.id,
            stage=VerificationStage.FINAL,
            current_value=76.10,
            evaluation_period="Post-Fix 7-Day Sustained Telemetry",
        )
    )
    comp3 = run_final.comparison
    print(f" Verification Run: {run_final.id}")
    print(f"   - Stage:          {run_final.verification_stage.value}")
    print(f"   - Baseline:       {comp3.baseline_value}% -> Current: {comp3.current_value}%")
    print(f"   - Absolute Move:  {comp3.absolute_change:+0.2f}%")
    print(f"   - Relative Move:  {comp3.percentage_change:+0.2f}%")
    print(f"   - Target Met:     {run_final.target_met} (Target: {comp3.target_value}%)")
    print(f"   - Outcome:        {run_final.outcome.value}")
    print(f"   - Resolved?:      {run_final.is_resolved} -> PROBLEM FULLY RESOLVED!")

    if run_final.gemini_analysis:
        print(f"   - Gemini Summary: {run_final.gemini_analysis.what_changed}")
        print(f"   - Next Steps:     {run_final.gemini_analysis.recommended_next_steps}")
        print(f"   - Attribution:    Confidence={run_final.gemini_analysis.causal_attribution_confidence}")

    # 8. Complete Verification History
    print_section("STEP 7: Complete Verification History & Audit Trail")
    history = default_verification_service.get_verification_history(action.id)
    print(f" Action ID:           {history.action_id}")
    print(f" Original Baseline:   {history.baseline.metric_name} = {history.baseline.baseline_value}% (Target: {history.baseline.target_value}%)")
    print(f" Total Runs Executed: {len(history.verification_runs)}")
    for i, r in enumerate(history.verification_runs, 1):
        print(f"   Run #{i} [{r.verification_stage.value}]: Value={r.comparison.current_value}% | Outcome={r.outcome.value} | Target Met={r.target_met}")
    print(f" Total Notes:         {len(history.notes)}")
    print(f" Resolution Status:   {history.current_resolution_status}")

    print_header("BIZPULSE PHASE 3C VERIFICATION DEMO COMPLETED SUCCESSFULLY")


if __name__ == "__main__":
    main()
