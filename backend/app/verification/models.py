from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field


class VerificationOutcome(str, Enum):
    IMPROVED = "Improved"
    NOT_IMPROVED = "Not Improved"
    DETERIORATED = "Deteriorated"
    INCONCLUSIVE = "Inconclusive"
    INSUFFICIENT_DATA = "Insufficient Data"


class VerificationStage(str, Enum):
    INITIAL = "initial"          # e.g., 24-48h post-fix
    FOLLOW_UP = "follow_up"      # e.g., 7 days post-fix
    FINAL = "final"              # e.g., 14-30 days post-fix
    MANUAL = "manual"            # on-demand evaluation


class MetricComparisonDirection(str, Enum):
    INCREASE = "increase"  # higher is better (e.g. conversion %, revenue $, profit margin %)
    DECREASE = "decrease"  # lower is better (e.g. error rate %, latency ms, bounce rate %)


# ============================================================================
# Baseline Models
# ============================================================================

class BaselineMetric(BaseModel):
    id: str = Field(description="Unique baseline identifier (e.g., BASE-XXXXXXXX)")
    action_id: str = Field(description="Associated business action ID")
    investigation_id: str = Field(description="Originating investigation or orchestration ID")
    anomaly_id: str = Field(description="Planting/anomaly identifier")
    metric_name: str = Field(description="Standardized metric key (e.g. mobile_payment_completion_rate)")
    baseline_value: float = Field(description="Deterministic numerical baseline value before action")
    baseline_period: str = Field(description="Time window when baseline was measured")
    expected_improvement: str = Field(description="Target description (e.g. '>= 74.00%')")
    target_value: float = Field(description="Numerical success threshold")
    comparison_direction: MetricComparisonDirection = Field(default=MetricComparisonDirection.INCREASE)
    verification_criteria: str = Field(description="Qualitative criteria for verification")
    captured_at: str = Field(description="UTC ISO timestamp of initial capture")


class BaselineCaptureRequest(BaseModel):
    action_id: str
    metric_name: Optional[str] = None
    baseline_value: Optional[float] = None
    baseline_period: Optional[str] = None
    expected_improvement: Optional[str] = None
    target_value: Optional[float] = None
    comparison_direction: Optional[MetricComparisonDirection] = None
    verification_criteria: Optional[str] = None


# ============================================================================
# Numerical Comparison & Outcome Models (Python Engine)
# ============================================================================

class VerificationComparison(BaseModel):
    metric_name: str
    baseline_value: float
    current_value: float
    absolute_change: float
    percentage_change: float
    target_value: float
    comparison_direction: MetricComparisonDirection
    target_met: bool
    outcome: VerificationOutcome
    calculation_summary: str


# ============================================================================
# AI Follow-Up Analysis Models (Google Gemini)
# ============================================================================

class GeminiFollowUpAnalysis(BaseModel):
    what_changed: str = Field(description="Clear factual explanation of observed metric movements")
    did_metric_improve: bool = Field(description="Whether the quantitative trajectory is positive")
    did_it_meet_target: bool = Field(description="Whether the predefined verification target was met")
    possible_explanations: List[str] = Field(description="Plausible causal factors explaining the outcome")
    recommended_next_steps: List[str] = Field(description="Actionable next business steps")
    causal_attribution_confidence: Literal["high", "medium", "low", "unsubstantiated"] = Field(
        description="Confidence in whether the completed action directly produced the outcome"
    )


# ============================================================================
# Verification Run & Response Models
# ============================================================================

class VerificationRunResponse(BaseModel):
    id: str = Field(description="Verification run identifier (e.g., VER-XXXXXXXX)")
    action_id: str
    baseline_id: str
    verification_stage: VerificationStage
    evaluation_period: str
    comparison: VerificationComparison
    outcome: VerificationOutcome
    target_met: bool
    is_resolved: bool
    needs_reopening: bool
    data_source: str
    gemini_analysis: Optional[GeminiFollowUpAnalysis] = None
    executed_at: str


class VerificationNoteCreateRequest(BaseModel):
    verification_id: str
    action_id: str
    note: str = Field(min_length=1, description="Follow-up diagnostic or manager note")
    author: Optional[str] = "QA / Operations"


class VerificationNoteResponse(BaseModel):
    id: int
    verification_id: str
    action_id: str
    note: str
    author: str
    created_at: str


class VerificationHistoryResponse(BaseModel):
    action_id: str
    baseline: BaselineMetric
    verification_runs: List[VerificationRunResponse]
    notes: List[VerificationNoteResponse]
    current_resolution_status: str


class VerificationTriggerRequest(BaseModel):
    action_id: str
    stage: Optional[VerificationStage] = VerificationStage.INITIAL
    current_value: Optional[float] = None
    evaluation_period: Optional[str] = None
    simulated_data_scenario: Optional[Literal["improved", "not_improved", "deteriorated", "insufficient_data"]] = None


class ReopenInvestigationRequest(BaseModel):
    action_id: str
    reason: str = Field(min_length=5, description="Justification for reopening after failed verification")
    requested_by: Optional[str] = "QA Lead"
    suggested_additional_actions: Optional[List[str]] = None
