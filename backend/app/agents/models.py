from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Literal
from pydantic import BaseModel, Field

from ..services.investigation_service import InvestigationFacts


# ============================================================================
# Role 1: Analyst Output Model
# ============================================================================

class AnalystOutput(BaseModel):
    """
    Structured analytical output from Agent 1 (Analyst).
    Synthesizes only verified numerical metrics from the Python engine.
    """
    key_metrics_validated: List[str] = Field(
        description="List of verified quantitative metrics deemed most critical to the problem."
    )
    patterns_identified: List[str] = Field(
        description="Patterns and anomalies observed in the validated data (e.g., timing, device skew, product drop)."
    )
    analytical_summary: str = Field(
        description="Concise analytical synthesis of the situation based strictly on verified data."
    )
    severity_assessment: Literal["critical", "high", "medium", "low"] = Field(
        description="Assessed severity level based on financial and operational impact."
    )


# ============================================================================
# Role 2: Connector Output Model
# ============================================================================

class DepartmentConnection(BaseModel):
    departments_involved: List[str] = Field(
        description="Departments linked by this finding (e.g. ['Engineering', 'Marketing', 'Finance'])."
    )
    connection_type: Literal["evidence_backed", "hypothesis"] = Field(
        description="Whether this connection is directly backed by recorded data/events or is a logical hypothesis."
    )
    finding: str = Field(
        description="Explanation of the cross-departmental dependency or interaction."
    )
    supporting_evidence: List[str] = Field(
        description="Specific events or metrics that support this connection."
    )


class ConnectorOutput(BaseModel):
    """
    Structured output from Agent 2 (Connector).
    Connects evidence across sales, finance, marketing, technology, and operations.
    """
    cross_department_connections: List[DepartmentConnection] = Field(
        description="Inter-departmental linkages, dependencies, and causal chains identified."
    )
    collaboration_rationale: str = Field(
        description="Detailed explanation of why the involved departments must collaborate to resolve the problem."
    )


# ============================================================================
# Role 3: Router Output Model
# ============================================================================

class RouterOutput(BaseModel):
    """
    Structured output from Agent 3 (Router).
    Identifies responsible department, recommended team/role, and next action.
    Strictly avoids inventing personal employee names or claiming actions have been completed.
    """
    primary_department: str = Field(
        description="Primary department accountable for leading remediation."
    )
    collaborating_departments: List[str] = Field(
        description="Other departments that must support the remediation."
    )
    recommended_role_or_team: str = Field(
        description="Functional role or team recommended to take ownership (e.g. 'Checkout Frontend Engineering Team')."
    )
    priority: Literal["Critical", "High", "Medium", "Low"] = Field(
        description="Execution priority for remediation."
    )
    suggested_next_action: str = Field(
        description="Recommended immediate first step for the responsible team."
    )
    routing_justification: str = Field(
        description="Explanation of why this team/department is recommended based on the Connector findings."
    )


# ============================================================================
# Role 4: Writer Output Model
# ============================================================================

class WriterOutput(BaseModel):
    """
    Structured output from Agent 4 (Writer).
    A professional, concise business action brief synthesizing the entire investigation.
    """
    executive_summary: str = Field(
        description="High-level executive overview of the situation and recommendation."
    )
    problem_statement: str = Field(
        description="Concise description of the business problem with specific metrics."
    )
    confirmed_evidence: List[str] = Field(
        description="Bullet-point list of verified factual findings and timeline evidence."
    )
    likely_causes: List[str] = Field(
        description="Bullet-point list of the most probable root causes."
    )
    target_team_and_priority: str = Field(
        description="Summary of recommended team assignment and urgency level."
    )
    recommended_action_plan: List[str] = Field(
        description="Sequential list of recommended remediation steps."
    )
    verification_and_success_criteria: List[str] = Field(
        description="Measurable success metrics and verification tests to confirm the issue is resolved."
    )


# ============================================================================
# Stage & Orchestration Models
# ============================================================================

class StageResult(BaseModel):
    """Execution outcome for a single agent stage."""
    agent_name: str
    status: Literal["completed", "failed", "skipped"]
    duration_ms: float
    output: Optional[Any] = None
    error: Optional[str] = None


class OrchestrationStages(BaseModel):
    """Collection of results from all 4 agent stages."""
    analyst: StageResult
    connector: StageResult
    router: StageResult
    writer: StageResult


class OrchestrationResponse(BaseModel):
    """
    Complete end-to-end response returned by the multi-agent orchestrator.
    """
    orchestration_id: str
    anomaly_id: str
    status: Literal["completed", "failed", "partial"]
    facts: InvestigationFacts = Field(description="Deterministic verified facts from Python engine")
    stages: OrchestrationStages = Field(description="Execution details and outputs for each of the 4 roles")
    final_action_brief: Optional[WriterOutput] = Field(
        default=None,
        description="Final synthesized business action brief produced by Agent 4 (Writer)"
    )
    total_duration_ms: float
    model_used: str
    created_at: str


class AgentRunRequest(BaseModel):
    """Request payload for POST /api/agents/run."""
    anomaly_id: Optional[str] = "ANOMALY_FUNNEL_MOBILE_001"
