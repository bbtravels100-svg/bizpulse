import uuid
import time
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any

from ..services.gemini_service import get_gemini_model_name
from ..services.investigation_service import (
    extract_revenue_decline_facts,
    extract_low_profitability_facts,
    extract_mobile_payment_facts,
    SUPPORTED_ANOMALY_ROUTING,
    InvestigationFacts,
)
from .models import (
    OrchestrationResponse,
    OrchestrationStages,
    StageResult,
    AnalystOutput,
    ConnectorOutput,
    RouterOutput,
    WriterOutput,
)
from .roles import (
    AnalystAgent,
    ConnectorAgent,
    RouterAgent,
    WriterAgent,
)

logger = logging.getLogger("bizpulse.orchestrator")


def get_facts_for_anomaly(anomaly_id: str) -> InvestigationFacts:
    """
    Retrieve deterministic verified facts and event timeline from the Python analytics engine
    for any supported anomaly or alias.
    """
    norm_id = (anomaly_id or "ANOMALY_FUNNEL_MOBILE_001").strip().upper()
    category = SUPPORTED_ANOMALY_ROUTING.get(norm_id)

    if not category:
        if "REV" in norm_id:
            category = "revenue"
        elif "PROFIT" in norm_id or "PROD_005" in norm_id:
            category = "profitability"
        elif "MOBILE" in norm_id or "FUNNEL" in norm_id:
            category = "mobile_payment"
        else:
            raise ValueError(
                f"Unsupported anomaly_id '{anomaly_id}'. Supported anomalies: "
                "ANOMALY_REV_001 (Revenue Decline), "
                "ANOMALY_PROFIT_PROD_005 (Low Product Profitability), "
                "ANOMALY_FUNNEL_MOBILE_001 (Mobile Payment Deterioration)."
            )

    if category == "revenue":
        return extract_revenue_decline_facts()
    elif category == "profitability":
        return extract_low_profitability_facts()
    else:
        return extract_mobile_payment_facts()


class AgentOrchestrator:
    """
    Central orchestration service coordinating the four AI roles in sequence:
    ANALYST -> CONNECTOR -> ROUTER -> WRITER
    """

    def __init__(
        self,
        analyst: Optional[AnalystAgent] = None,
        connector: Optional[ConnectorAgent] = None,
        router: Optional[RouterAgent] = None,
        writer: Optional[WriterAgent] = None,
    ):
        self.analyst = analyst or AnalystAgent()
        self.connector = connector or ConnectorAgent()
        self.router = router or RouterAgent()
        self.writer = writer or WriterAgent()

    def run(
        self,
        anomaly_id: str = "ANOMALY_FUNNEL_MOBILE_001",
        model_name: Optional[str] = None,
    ) -> OrchestrationResponse:
        """
        Execute the full 4-agent orchestration workflow:
        1. Fetch deterministic Python analytics facts.
        2. Run Analyst Agent (validates key metrics and patterns).
        3. Run Connector Agent (cross-department evidence and dependencies).
        4. Run Router Agent (identifies responsible team and priority).
        5. Run Writer Agent (synthesizes the final business action brief).
        """
        t_start = time.perf_counter()
        orch_id = f"ORCH-{uuid.uuid4().hex[:8].upper()}"
        model = model_name or get_gemini_model_name()

        logger.info(f"[{orch_id}] Initializing multi-agent orchestration for anomaly '{anomaly_id}'")

        # 1. Retrieve verified Python facts
        facts = get_facts_for_anomaly(anomaly_id)

        # Stage placeholders
        analyst_res = StageResult(agent_name="Analyst", status="skipped", duration_ms=0.0)
        connector_res = StageResult(agent_name="Connector", status="skipped", duration_ms=0.0)
        router_res = StageResult(agent_name="Router", status="skipped", duration_ms=0.0)
        writer_res = StageResult(agent_name="Writer", status="skipped", duration_ms=0.0)

        # -------------------------------------------------------------
        # Stage 1: Analyst Agent
        # -------------------------------------------------------------
        analyst_res = self.analyst.run(facts, model_name=model)
        if analyst_res.status != "completed" or not isinstance(analyst_res.output, AnalystOutput):
            total_duration_ms = round((time.perf_counter() - t_start) * 1000, 2)
            logger.error(f"[{orch_id}] Analyst stage failed: {analyst_res.error}")
            return OrchestrationResponse(
                orchestration_id=orch_id,
                anomaly_id=facts.anomaly_id,
                status="failed",
                facts=facts,
                stages=OrchestrationStages(
                    analyst=analyst_res,
                    connector=connector_res,
                    router=router_res,
                    writer=writer_res,
                ),
                final_action_brief=None,
                total_duration_ms=total_duration_ms,
                model_used=model,
                created_at=datetime.now(timezone.utc).isoformat(),
            )

        analyst_output: AnalystOutput = analyst_res.output

        # -------------------------------------------------------------
        # Stage 2: Connector Agent
        # -------------------------------------------------------------
        connector_res = self.connector.run(facts, analyst_output, model_name=model)
        if connector_res.status != "completed" or not isinstance(connector_res.output, ConnectorOutput):
            total_duration_ms = round((time.perf_counter() - t_start) * 1000, 2)
            logger.error(f"[{orch_id}] Connector stage failed: {connector_res.error}")
            return OrchestrationResponse(
                orchestration_id=orch_id,
                anomaly_id=facts.anomaly_id,
                status="failed",
                facts=facts,
                stages=OrchestrationStages(
                    analyst=analyst_res,
                    connector=connector_res,
                    router=router_res,
                    writer=writer_res,
                ),
                final_action_brief=None,
                total_duration_ms=total_duration_ms,
                model_used=model,
                created_at=datetime.now(timezone.utc).isoformat(),
            )

        connector_output: ConnectorOutput = connector_res.output

        # -------------------------------------------------------------
        # Stage 3: Router Agent
        # -------------------------------------------------------------
        router_res = self.router.run(facts, analyst_output, connector_output, model_name=model)
        if router_res.status != "completed" or not isinstance(router_res.output, RouterOutput):
            total_duration_ms = round((time.perf_counter() - t_start) * 1000, 2)
            logger.error(f"[{orch_id}] Router stage failed: {router_res.error}")
            return OrchestrationResponse(
                orchestration_id=orch_id,
                anomaly_id=facts.anomaly_id,
                status="failed",
                facts=facts,
                stages=OrchestrationStages(
                    analyst=analyst_res,
                    connector=connector_res,
                    router=router_res,
                    writer=writer_res,
                ),
                final_action_brief=None,
                total_duration_ms=total_duration_ms,
                model_used=model,
                created_at=datetime.now(timezone.utc).isoformat(),
            )

        router_output: RouterOutput = router_res.output

        # -------------------------------------------------------------
        # Stage 4: Writer Agent
        # -------------------------------------------------------------
        writer_res = self.writer.run(
            facts, analyst_output, connector_output, router_output, model_name=model
        )
        if writer_res.status != "completed" or not isinstance(writer_res.output, WriterOutput):
            total_duration_ms = round((time.perf_counter() - t_start) * 1000, 2)
            logger.error(f"[{orch_id}] Writer stage failed: {writer_res.error}")
            return OrchestrationResponse(
                orchestration_id=orch_id,
                anomaly_id=facts.anomaly_id,
                status="partial",
                facts=facts,
                stages=OrchestrationStages(
                    analyst=analyst_res,
                    connector=connector_res,
                    router=router_res,
                    writer=writer_res,
                ),
                final_action_brief=None,
                total_duration_ms=total_duration_ms,
                model_used=model,
                created_at=datetime.now(timezone.utc).isoformat(),
            )

        writer_output: WriterOutput = writer_res.output
        total_duration_ms = round((time.perf_counter() - t_start) * 1000, 2)
        logger.info(f"[{orch_id}] Multi-agent pipeline completed successfully in {total_duration_ms}ms")

        return OrchestrationResponse(
            orchestration_id=orch_id,
            anomaly_id=facts.anomaly_id,
            status="completed",
            facts=facts,
            stages=OrchestrationStages(
                analyst=analyst_res,
                connector=connector_res,
                router=router_res,
                writer=writer_res,
            ),
            final_action_brief=writer_output,
            total_duration_ms=total_duration_ms,
            model_used=model,
            created_at=datetime.now(timezone.utc).isoformat(),
        )


# Global singleton instance for easy import
default_orchestrator = AgentOrchestrator()


def run_agent_pipeline(
    anomaly_id: str = "ANOMALY_FUNNEL_MOBILE_001",
    model_name: Optional[str] = None,
) -> OrchestrationResponse:
    """Convenience functional wrapper around the default orchestrator."""
    return default_orchestrator.run(anomaly_id=anomaly_id, model_name=model_name)
