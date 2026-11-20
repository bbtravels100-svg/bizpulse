"""
BizPulse Multi-Agent Orchestration Package (Phase 3A)
Coordinates four AI roles:
1. Analyst (Validates facts, patterns, and analytical summary)
2. Connector (Identifies cross-departmental dependencies & collaboration rationale)
3. Router (Recommends responsible department, role/team, priority, next actions)
4. Writer (Produces the final executive-ready business action brief)
"""

from .models import (
    AnalystOutput,
    DepartmentConnection,
    ConnectorOutput,
    RouterOutput,
    WriterOutput,
    StageResult,
    OrchestrationStages,
    OrchestrationResponse,
    AgentRunRequest,
)
from .roles import (
    AnalystAgent,
    ConnectorAgent,
    RouterAgent,
    WriterAgent,
)
from .orchestrator import (
    AgentOrchestrator,
    run_agent_pipeline,
    default_orchestrator,
    get_facts_for_anomaly,
)

__all__ = [
    "AnalystOutput",
    "DepartmentConnection",
    "ConnectorOutput",
    "RouterOutput",
    "WriterOutput",
    "StageResult",
    "OrchestrationStages",
    "OrchestrationResponse",
    "AgentRunRequest",
    "AnalystAgent",
    "ConnectorAgent",
    "RouterAgent",
    "WriterAgent",
    "AgentOrchestrator",
    "run_agent_pipeline",
    "default_orchestrator",
    "get_facts_for_anomaly",
]
