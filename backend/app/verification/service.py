import json
import uuid
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any

from ..actions.database import get_db_connection
from ..actions.models import ActionStatus, ActionPriority, ActionCreateRequest
from ..actions.service import ActionService, default_action_service, ActionNotFoundError
from ..services.gemini_service import generate_json, get_gemini_model_name, GeminiServiceError
from .models import (
    VerificationOutcome,
    VerificationStage,
    MetricComparisonDirection,
    BaselineMetric,
    BaselineCaptureRequest,
    VerificationComparison,
    GeminiFollowUpAnalysis,
    VerificationRunResponse,
    VerificationNoteCreateRequest,
    VerificationNoteResponse,
    VerificationHistoryResponse,
    VerificationTriggerRequest,
    ReopenInvestigationRequest,
)
from .evaluator import evaluate_metric_comparison
from .prompts import build_followup_prompt

logger = logging.getLogger("bizpulse.verification")


class VerificationError(Exception):
    """Base exception for Verification Engine operations."""
    pass


class VerificationNotFoundError(VerificationError):
    """Raised when a baseline or verification run is not found."""
    pass


class InvalidActionStateForVerificationError(VerificationError):
    """Raised when an action is not in an eligible lifecycle state (Approved, In Progress, Completed) for verification."""
    pass


ELIGIBLE_VERIFICATION_STATUSES = {
    ActionStatus.APPROVED,
    ActionStatus.IN_PROGRESS,
    ActionStatus.COMPLETED,
}


class VerificationService:
    """
    Follow-up and Verification Engine Service (Phase 3C).
    Enforces the principle that task completion != problem resolution.
    Performs deterministic Python comparison of post-action metrics against baselines,
    and leverages Gemini for qualitative follow-up interpretation and causal analysis.
    """

    def __init__(self, db_path: Optional[str] = None, action_service: Optional[ActionService] = None):
        self.db_path = db_path
        self._action_service = action_service

    @property
    def action_service(self) -> ActionService:
        if self._action_service:
            return self._action_service
        if self.db_path:
            return ActionService(db_path=self.db_path)
        return default_action_service

    def _get_conn(self):
        return get_db_connection(self.db_path)

    # ------------------------------------------------------------------------
    # 1. Baseline Capture (Immutable once recorded)
    # ------------------------------------------------------------------------

    def capture_baseline_for_action(
        self,
        action_id: str,
        custom_req: Optional[BaselineCaptureRequest] = None,
    ) -> BaselineMetric:
        """
        Capture and store the baseline metric for an approved business action.
        CRITICAL: Never overwrites an existing baseline. If one already exists,
        returns the existing baseline unchanged.
        """
        existing = self.get_baseline_for_action(action_id)
        if existing:
            logger.info(f"Baseline already captured for action {action_id} (ID: {existing.id}). Preserving original.")
            return existing

        action = self.action_service.get_action(action_id)
        anomaly_id = action.anomaly_id

        # Determine metric baseline defaults based on anomaly identifier or custom input
        req = custom_req or BaselineCaptureRequest(action_id=action_id)

        if req.metric_name and req.baseline_value is not None and req.target_value is not None:
            metric_name = req.metric_name
            baseline_val = float(req.baseline_value)
            target_val = float(req.target_value)
            direction = req.comparison_direction or MetricComparisonDirection.INCREASE
            period = req.baseline_period or "Pre-intervention window"
            expected = req.expected_improvement or f"Reach target: {target_val}"
            criteria = req.verification_criteria or action.verification_criteria
        elif anomaly_id == "ANOMALY_FUNNEL_MOBILE_001":
            metric_name = "mobile_payment_completion_rate"
            baseline_val = 21.95
            target_val = 74.00
            direction = MetricComparisonDirection.INCREASE
            period = "Week 2 (2026-11-08 to 2026-11-14)"
            expected = "Restore mobile payment completion rate to >= 74.00% (Week 1 pre-incident level)"
            criteria = "Mobile payment completion rate recovers to >= 74.0% with zero payment gateway 504 timeouts."
        elif anomaly_id == "ANOMALY_REV_001":
            metric_name = "weekly_revenue"
            baseline_val = 69700.00
            target_val = 84000.00
            direction = MetricComparisonDirection.INCREASE
            period = "Week 2 (2026-11-08 to 2026-11-14)"
            expected = "Restore weekly revenue to >= $84,000.00"
            criteria = "Weekly revenue recovers to >= $84,000 without negative gross margin degradation."
        elif anomaly_id.startswith("ANOMALY_PROFIT_"):
            metric_name = "gross_profit_margin_pct"
            baseline_val = 4.00
            target_val = 15.00
            direction = MetricComparisonDirection.INCREASE
            period = "14-day analysis period (2026-11-01 to 2026-11-14)"
            expected = "Raise gross profit margin to >= 15.00% threshold"
            criteria = "Gross profit margin reaches or exceeds 15.0% threshold."
        else:
            metric_name = "business_performance_index"
            baseline_val = 50.00
            target_val = 75.00
            direction = MetricComparisonDirection.INCREASE
            period = "Pre-intervention window"
            expected = "Achieve predefined target metric value"
            criteria = action.verification_criteria or "Verification criteria achieved"

        baseline_id = f"BASE-{uuid.uuid4().hex[:8].upper()}"
        now_iso = datetime.now(timezone.utc).isoformat()

        conn = self._get_conn()
        try:
            with conn:
                conn.execute(
                    """
                    INSERT INTO metric_baselines (
                        id, action_id, investigation_id, anomaly_id, metric_name,
                        baseline_value, baseline_period, expected_improvement, target_value,
                        comparison_direction, verification_criteria, captured_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        baseline_id,
                        action.id,
                        action.investigation_id,
                        action.anomaly_id,
                        metric_name,
                        baseline_val,
                        period,
                        expected,
                        target_val,
                        direction.value,
                        criteria,
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
                        action.id,
                        "BASELINE_CAPTURED",
                        None,
                        str(baseline_val),
                        f"Baseline captured for metric '{metric_name}': {baseline_val} (Target: {target_val}, ID: {baseline_id})",
                        now_iso,
                    ),
                )
        finally:
            conn.close()

        logger.info(f"Captured immutable baseline {baseline_id} for action {action_id}")
        return self.get_baseline_for_action(action_id)

    def get_baseline_for_action(self, action_id: str) -> Optional[BaselineMetric]:
        """Fetch the immutable baseline for a given action."""
        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT * FROM metric_baselines WHERE action_id = ? ORDER BY captured_at ASC LIMIT 1",
                (action_id,),
            ).fetchone()
            if not row:
                return None
            return BaselineMetric(
                id=row["id"],
                action_id=row["action_id"],
                investigation_id=row["investigation_id"],
                anomaly_id=row["anomaly_id"],
                metric_name=row["metric_name"],
                baseline_value=float(row["baseline_value"]),
                baseline_period=row["baseline_period"],
                expected_improvement=row["expected_improvement"],
                target_value=float(row["target_value"]),
                comparison_direction=MetricComparisonDirection(row["comparison_direction"]),
                verification_criteria=row["verification_criteria"],
                captured_at=row["captured_at"],
            )
        finally:
            conn.close()

    # ------------------------------------------------------------------------
    # 2. Verification Trigger & Execution
    # ------------------------------------------------------------------------

    def verify_action(
        self,
        req: VerificationTriggerRequest,
        model_name: Optional[str] = None,
    ) -> VerificationRunResponse:
        """
        Execute follow-up verification on a business action:
        1. Ensures baseline exists (capturing if needed).
        2. Obtains current measurement value (or simulated scenario).
        3. Deterministically computes numerical metrics via Python engine.
        4. Invokes Gemini to interpret findings and assess causal attribution.
        5. Persists verification record and logs audit trail.
        """
        action = self.action_service.get_action(req.action_id)
        if action.status not in ELIGIBLE_VERIFICATION_STATUSES:
            raise InvalidActionStateForVerificationError(
                f"Cannot verify action '{action.id}' with status '{action.status.value}'. "
                "Verification is only allowed for actions in 'Approved', 'In Progress', or 'Completed' status."
            )

        baseline = self.get_baseline_for_action(req.action_id)
        if not baseline:
            baseline = self.capture_baseline_for_action(req.action_id)

        # Determine current metric value
        current_val: Optional[float] = None
        data_source = "Direct Telemetry"

        if req.current_value is not None:
            current_val = float(req.current_value)
            data_source = "Direct Telemetry Input"
        elif req.simulated_data_scenario:
            data_source = f"Simulated Scenario ({req.simulated_data_scenario})"
            scenario = req.simulated_data_scenario.lower()
            if scenario == "improved":
                if baseline.metric_name == "mobile_payment_completion_rate":
                    current_val = 75.20
                elif baseline.metric_name == "weekly_revenue":
                    current_val = 85500.00
                elif baseline.metric_name == "gross_profit_margin_pct":
                    current_val = 16.50
                else:
                    current_val = baseline.target_value + 2.0
            elif scenario == "not_improved":
                if baseline.metric_name == "mobile_payment_completion_rate":
                    current_val = 22.10
                elif baseline.metric_name == "weekly_revenue":
                    current_val = 69850.00
                elif baseline.metric_name == "gross_profit_margin_pct":
                    current_val = 4.05
                else:
                    current_val = baseline.baseline_value
            elif scenario == "deteriorated":
                if baseline.metric_name == "mobile_payment_completion_rate":
                    current_val = 14.50
                elif baseline.metric_name == "weekly_revenue":
                    current_val = 58400.00
                elif baseline.metric_name == "gross_profit_margin_pct":
                    current_val = 1.80
                else:
                    current_val = baseline.baseline_value * 0.75
            elif scenario == "insufficient_data":
                current_val = None
                data_source = "Missing Telemetry Feed"

        # Deterministic Python comparison
        comparison = evaluate_metric_comparison(baseline, current_val)

        # Stage & Period
        stage = req.stage or VerificationStage.INITIAL
        eval_period = req.evaluation_period or f"Post-intervention {stage.value.capitalize()} Window"

        # Resolution status
        # Task completion is NOT problem resolution:
        # Only resolved if metric improved AND target was met!
        target_met = comparison.target_met
        is_resolved = target_met and (comparison.outcome == VerificationOutcome.IMPROVED)
        needs_reopening = not is_resolved

        # Gemini Follow-Up Interpretation
        gemini_analysis = self._run_gemini_analysis(
            baseline=baseline,
            comparison=comparison,
            evaluation_period=eval_period,
            action_dict=action.model_dump(),
            model_name=model_name,
        )

        ver_id = f"VER-{uuid.uuid4().hex[:8].upper()}"
        now_iso = datetime.now(timezone.utc).isoformat()

        conn = self._get_conn()
        try:
            with conn:
                conn.execute(
                    """
                    INSERT INTO verification_runs (
                        id, action_id, baseline_id, verification_stage, evaluation_period,
                        current_value, absolute_change, percentage_change, outcome,
                        target_met, is_resolved, needs_reopening, data_source,
                        gemini_analysis, executed_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        ver_id,
                        action.id,
                        baseline.id,
                        stage.value,
                        eval_period,
                        comparison.current_value if current_val is not None else None,
                        comparison.absolute_change,
                        comparison.percentage_change,
                        comparison.outcome.value,
                        1 if target_met else 0,
                        1 if is_resolved else 0,
                        1 if needs_reopening else 0,
                        data_source,
                        json.dumps(gemini_analysis.model_dump() if gemini_analysis else {}),
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
                        action.id,
                        "VERIFICATION_EVALUATED",
                        None,
                        comparison.outcome.value,
                        f"Run {ver_id} ({stage.value}): Target {'Met' if target_met else 'Unmet'}. "
                        f"Resolved: {is_resolved}. Needs Reopening: {needs_reopening}.",
                        now_iso,
                    ),
                )
        finally:
            conn.close()

        logger.info(f"Verification run {ver_id} completed for action {action.id} -> {comparison.outcome.value}")

        return VerificationRunResponse(
            id=ver_id,
            action_id=action.id,
            baseline_id=baseline.id,
            verification_stage=stage,
            evaluation_period=eval_period,
            comparison=comparison,
            outcome=comparison.outcome,
            target_met=target_met,
            is_resolved=is_resolved,
            needs_reopening=needs_reopening,
            data_source=data_source,
            gemini_analysis=gemini_analysis,
            executed_at=now_iso,
        )

    def _run_gemini_analysis(
        self,
        baseline: BaselineMetric,
        comparison: VerificationComparison,
        evaluation_period: str,
        action_dict: Dict[str, Any],
        model_name: Optional[str] = None,
    ) -> GeminiFollowUpAnalysis:
        """Call Gemini for qualitative interpretation of deterministic Python results."""
        prompt = build_followup_prompt(
            baseline=baseline,
            comparison=comparison,
            evaluation_period=evaluation_period,
            action_details=action_dict,
        )

        try:
            raw_json = generate_json(prompt=prompt, model_name=model_name)
            return GeminiFollowUpAnalysis(
                what_changed=raw_json.get("what_changed", comparison.calculation_summary),
                did_metric_improve=bool(raw_json.get("did_metric_improve", comparison.outcome == VerificationOutcome.IMPROVED)),
                did_it_meet_target=bool(raw_json.get("did_it_meet_target", comparison.target_met)),
                possible_explanations=raw_json.get("possible_explanations", ["Measurement observed post-action deployment."]),
                recommended_next_steps=raw_json.get("recommended_next_steps", ["Continue observation." if comparison.target_met else "Review diagnostics."]),
                causal_attribution_confidence=raw_json.get("causal_attribution_confidence", "high" if comparison.target_met else "unsubstantiated"),
            )
        except Exception as e:
            logger.warning(f"Gemini follow-up analysis fallback engaged due to: {e}")
            # Failsafe deterministic fallback
            is_improved = comparison.outcome == VerificationOutcome.IMPROVED
            return GeminiFollowUpAnalysis(
                what_changed=(
                    f"Metric '{comparison.metric_name}' moved from baseline {comparison.baseline_value} "
                    f"to {comparison.current_value} ({comparison.percentage_change:+}%), "
                    f"target ({comparison.target_value}) was {'met' if comparison.target_met else 'not met'}."
                ),
                did_metric_improve=is_improved,
                did_it_meet_target=comparison.target_met,
                possible_explanations=[
                    "Telemetry data captured after action implementation.",
                    "Outcome reflects direct operational impact and system telemetry stability."
                ],
                recommended_next_steps=[
                    "Maintain active telemetry monitoring and archive action." if comparison.target_met
                    else "Reopen investigation to determine why action did not remediate the anomaly."
                ],
                causal_attribution_confidence="high" if comparison.target_met else ("unsubstantiated" if comparison.outcome in (VerificationOutcome.DETERIORATED, VerificationOutcome.NOT_IMPROVED) else "low"),
            )

    # ------------------------------------------------------------------------
    # 3. Retrieval & History
    # ------------------------------------------------------------------------

    def get_latest_result(self, action_id: str) -> VerificationRunResponse:
        """Fetch the most recent verification run for a task."""
        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT * FROM verification_runs WHERE action_id = ? ORDER BY executed_at DESC LIMIT 1",
                (action_id,),
            ).fetchone()
            if not row:
                raise VerificationNotFoundError(f"No verification run found for action '{action_id}'.")
            return self._row_to_run_response(row)
        finally:
            conn.close()

    def get_verification_history(self, action_id: str) -> VerificationHistoryResponse:
        """Fetch complete verification history, baseline, and diagnostic notes."""
        baseline = self.get_baseline_for_action(action_id)
        if not baseline:
            raise VerificationNotFoundError(f"No baseline found for action '{action_id}'.")

        conn = self._get_conn()
        try:
            run_rows = conn.execute(
                "SELECT * FROM verification_runs WHERE action_id = ? ORDER BY executed_at ASC",
                (action_id,),
            ).fetchall()
            note_rows = conn.execute(
                "SELECT * FROM verification_notes WHERE action_id = ? ORDER BY created_at ASC",
                (action_id,),
            ).fetchall()

            runs = [self._row_to_run_response(r) for r in run_rows]
            notes = [
                VerificationNoteResponse(
                    id=n["id"],
                    verification_id=n["verification_id"],
                    action_id=n["action_id"],
                    note=n["note"],
                    author=n["author"],
                    created_at=n["created_at"],
                )
                for n in note_rows
            ]

            if runs:
                latest = runs[-1]
                if latest.is_resolved:
                    resolution_status = "Resolved - Predefined verification criteria fully met"
                elif latest.needs_reopening:
                    resolution_status = f"Unresolved - Verification outcome: {latest.outcome.value} (Action requires follow-up)"
                else:
                    resolution_status = f"In Progress - Verification status: {latest.outcome.value}"
            else:
                resolution_status = "Pending Verification - Baseline captured, no verification run executed yet"

            return VerificationHistoryResponse(
                action_id=action_id,
                baseline=baseline,
                verification_runs=runs,
                notes=notes,
                current_resolution_status=resolution_status,
            )
        finally:
            conn.close()

    # ------------------------------------------------------------------------
    # 4. Diagnostic Notes & Reopening
    # ------------------------------------------------------------------------

    def add_verification_note(self, req: VerificationNoteCreateRequest) -> VerificationNoteResponse:
        """Add a follow-up or diagnostic note to a verification attempt."""
        now_iso = datetime.now(timezone.utc).isoformat()
        author = req.author or "QA / Operations"

        conn = self._get_conn()
        try:
            with conn:
                cursor = conn.execute(
                    """
                    INSERT INTO verification_notes (verification_id, action_id, note, author, created_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (req.verification_id, req.action_id, req.note, author, now_iso),
                )
                note_id = cursor.lastrowid
                conn.execute(
                    """
                    INSERT INTO action_audit_log (
                        action_id, action_type, previous_value, new_value, details, timestamp
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        req.action_id,
                        "VERIFICATION_NOTE_ADDED",
                        None,
                        None,
                        f"Note on {req.verification_id} by {author}: {req.note[:120]}",
                        now_iso,
                    ),
                )
        finally:
            conn.close()

        return VerificationNoteResponse(
            id=note_id,
            verification_id=req.verification_id,
            action_id=req.action_id,
            note=req.note,
            author=author,
            created_at=now_iso,
        )

    def reopen_investigation(self, req: ReopenInvestigationRequest) -> Dict[str, Any]:
        """
        Reopen an investigation when verification fails to resolve the underlying problem.
        Creates a new structured action proposal targeted at secondary diagnostics and remediation.
        """
        action = self.action_service.get_action(req.action_id)
        now_iso = datetime.now(timezone.utc).isoformat()

        # Build secondary proposal
        target_deadline = (datetime.now(timezone.utc) + timedelta(days=3)).strftime("%Y-%m-%d")
        reopen_req = ActionCreateRequest(
            investigation_id=action.investigation_id,
            anomaly_id=action.anomaly_id,
            problem_description=f"[REOPENED] Follow-up for {action.id}: {req.reason}",
            recommended_action=(
                f"Perform secondary diagnostic & remediation for {action.anomaly_id}. "
                f"Prior action '{action.id}' failed verification. Reason: {req.reason}"
            ),
            responsible_department=action.responsible_department,
            suggested_owner_role=f"Senior {action.responsible_department} Lead",
            priority=ActionPriority.CRITICAL,
            suggested_deadline=target_deadline,
            expected_outcome=f"Identify residual failure modes and remediate {action.anomaly_id} to satisfy criteria.",
            verification_criteria=action.verification_criteria,
        )

        new_action = self.action_service.create_action(reopen_req)

        # Audit log on original action
        conn = self._get_conn()
        try:
            with conn:
                conn.execute(
                    """
                    INSERT INTO action_audit_log (
                        action_id, action_type, previous_value, new_value, details, timestamp
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        action.id,
                        "INVESTIGATION_REOPENED",
                        action.status.value,
                        "REOPENED",
                        f"Reopened by {req.requested_by or 'Manager'}. Reason: {req.reason}. New Action: {new_action.id}",
                        now_iso,
                    ),
                )
        finally:
            conn.close()

        return {
            "status": "reopened",
            "original_action_id": action.id,
            "new_action_id": new_action.id,
            "reopening_reason": req.reason,
            "requested_by": req.requested_by or "QA Lead",
            "new_action_proposal": new_action,
        }

    # ------------------------------------------------------------------------
    # Internal Helpers
    # ------------------------------------------------------------------------

    def _row_to_run_response(self, row) -> VerificationRunResponse:
        baseline = self.get_baseline_for_action(row["action_id"])
        base_val = baseline.baseline_value if baseline else 0.0
        target_val = baseline.target_value if baseline else 0.0
        direction = baseline.comparison_direction if baseline else MetricComparisonDirection.INCREASE

        curr_val = row["current_value"]
        abs_change = float(row["absolute_change"]) if row["absolute_change"] is not None else 0.0
        pct_change = float(row["percentage_change"]) if row["percentage_change"] is not None else 0.0

        comparison = VerificationComparison(
            metric_name=baseline.metric_name if baseline else "metric",
            baseline_value=base_val,
            current_value=curr_val if curr_val is not None else 0.0,
            absolute_change=abs_change,
            percentage_change=pct_change,
            target_value=target_val,
            comparison_direction=direction,
            target_met=bool(row["target_met"]),
            outcome=VerificationOutcome(row["outcome"]),
            calculation_summary=f"Calculated outcome: {row['outcome']}",
        )

        analysis = None
        if row["gemini_analysis"]:
            try:
                raw = json.loads(row["gemini_analysis"])
                if raw:
                    analysis = GeminiFollowUpAnalysis(**raw)
            except Exception:
                pass

        return VerificationRunResponse(
            id=row["id"],
            action_id=row["action_id"],
            baseline_id=row["baseline_id"],
            verification_stage=VerificationStage(row["verification_stage"]),
            evaluation_period=row["evaluation_period"],
            comparison=comparison,
            outcome=VerificationOutcome(row["outcome"]),
            target_met=bool(row["target_met"]),
            is_resolved=bool(row["is_resolved"]),
            needs_reopening=bool(row["needs_reopening"]),
            data_source=row["data_source"],
            gemini_analysis=analysis,
            executed_at=row["executed_at"],
        )


# Global singleton instance
default_verification_service = VerificationService()
