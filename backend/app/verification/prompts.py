import json
from typing import Optional, Dict, Any
from .models import (
    BaselineMetric,
    VerificationComparison,
)


def build_followup_prompt(
    baseline: BaselineMetric,
    comparison: VerificationComparison,
    evaluation_period: str,
    action_details: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Construct prompt for Gemini follow-up verification analysis.
    Instructs Gemini to interpret Python-calculated verification results,
    clearly separating measured facts from AI hypotheses, and assessing
    causal attribution without claiming unsubstantiated certainty.
    """
    act = action_details or {}
    act_desc = act.get("recommended_action", "Business remediation action")
    act_dept = act.get("responsible_department", "Operations")
    act_role = act.get("suggested_owner_role", "Task Owner")
    act_outcome = act.get("expected_outcome", "Metric remediation")
    act_completion = act.get("completion_details", "Action marked completed by team")

    prompt = f"""You are the Follow-Up and Verification Evaluator for BizPulse, an enterprise AI business intelligence and operational execution platform.

Your mission is to perform an objective, evidence-based follow-up evaluation of whether a completed business action actually resolved the targeted business problem.

CRITICAL RULES:
1. All numerical calculations have ALREADY been computed deterministically by Python. NEVER recalculate, override, or invent numbers.
2. TASK COMPLETION DOES NOT EQUAL PROBLEM RESOLUTION: Even if an operational task was marked "Completed", the underlying business problem is only resolved if the business metrics objectively improved and met the verification target.
3. SEPARATE FACTS FROM HYPOTHESES: Clearly distinguish between measured, observed data points (facts) and plausible explanations or forward-looking projections (hypotheses).
4. CAUSAL ATTRIBUTION CONFIDENCE: Assess causal confidence strictly:
   - "high": Metric clearly improved/met target, timing aligns with action completion, and known failure mechanisms (e.g. gateway errors) vanished.
   - "medium": Metric improved towards target, but confounding factors (e.g. seasonality, partial rollback, external traffic) may also play a role.
   - "low": Metric changed minimally or ambiguously; causal link between the action and metric change is weak.
   - "unsubstantiated": Metric did not improve or deteriorated; claiming the action solved the problem is unjustified.

======================================================================
1. BUSINESS ACTION UNDER EVALUATION
======================================================================
- Action ID: {baseline.action_id}
- Recommended Action: {act_desc}
- Responsible Department: {act_dept}
- Suggested Owner Role: {act_role}
- Expected Outcome: {act_outcome}
- Completion Report: {act_completion}
- Predefined Verification Criteria: {baseline.verification_criteria}

======================================================================
2. BASELINE & DETERMINISTIC PYTHON EVALUATION RESULTS
======================================================================
- Evaluation Period: {evaluation_period}
- Metric Name: {comparison.metric_name}
- Direction of Improvement: Higher is better if 'increase', Lower is better if 'decrease' ({comparison.comparison_direction.value})
- Baseline Value ({baseline.baseline_period}): {comparison.baseline_value}
- Current Measured Value: {comparison.current_value}
- Absolute Change: {comparison.absolute_change:+}
- Relative / Percentage Change: {comparison.percentage_change:+}%
- Predefined Target Value: {comparison.target_value}
- Target Met: {"YES" if comparison.target_met else "NO"}
- Deterministic Python Classification: {comparison.outcome.value}
- Calculation Summary: {comparison.calculation_summary}

======================================================================
3. OUTPUT REQUIREMENTS
======================================================================
Produce a valid JSON object matching the following structure:
{{
  "what_changed": "A factual, objective 1-2 sentence description of the exact metric movement from baseline to current value.",
  "did_metric_improve": true or false,
  "did_it_meet_target": true or false,
  "possible_explanations": [
    "Plausible explanation 1 for why the metric changed or failed to reach target",
    "Plausible explanation 2 relating to implementation quality or residual issues"
  ],
  "recommended_next_steps": [
    "Concrete, actionable next step 1 (e.g. ongoing monitoring, re-investigation, secondary rollback)",
    "Concrete, actionable next step 2"
  ],
  "causal_attribution_confidence": "high" | "medium" | "low" | "unsubstantiated"
}}

Output ONLY the JSON object. Do not include markdown code block formatting or conversational preamble.
"""
    return prompt.strip()
