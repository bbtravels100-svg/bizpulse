import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from app.main import app
from app.agents.models import (
    AnalystOutput,
    ConnectorOutput,
    RouterOutput,
    WriterOutput,
    DepartmentConnection,
    StageResult,
    OrchestrationResponse,
)
from app.agents.roles import (
    AnalystAgent,
    ConnectorAgent,
    RouterAgent,
    WriterAgent,
)
from app.agents.orchestrator import (
    AgentOrchestrator,
    get_facts_for_anomaly,
    run_agent_pipeline,
)
from app.services.investigation_service import extract_mobile_payment_facts
from app.services.gemini_service import GeminiAuthError, GeminiServiceError


@pytest.fixture
def client():
    return TestClient(app)


# Sample Mock Responses for the 4 Roles
MOCK_ANALYST_RAW = {
    "key_metrics_validated": [
        "Mobile payment completion crashed from 74.98% in Week 1 down to 21.95% in Week 2 (-70.73% relative drop)",
        "Desktop payment completion held perfectly constant at 74.97% (0.00% change, control group)",
        "Overall revenue declined by -18.00% (-$15,300.00)"
    ],
    "patterns_identified": [
        "Failure is isolated entirely to the mobile user experience.",
        "Sharp onset begins on Nov 8 directly following system deployments."
    ],
    "analytical_summary": "A critical technical defect specifically impacted mobile checkout starting Nov 8, reducing mobile payment completions by over 70% while desktop checkout remained completely normal.",
    "severity_assessment": "critical"
}

MOCK_CONNECTOR_RAW = {
    "cross_department_connections": [
        {
            "departments_involved": ["Technology / Engineering", "Sales / Finance"],
            "connection_type": "evidence_backed",
            "finding": "Deployment of checkout frontend v2.4.0 on Nov 8 at 02:15 UTC triggered HTTP 504 timeouts and JS exceptions, depressing completed orders and company revenue by $15,300.",
            "supporting_evidence": [
                "Deployment timestamp 2026-11-08T02:15:00Z",
                "Spike in payment gateway timeouts at 2026-11-08T06:45:00Z",
                "Weekly revenue loss of -$15,300.00"
            ]
        },
        {
            "departments_involved": ["Customer Support", "Technology / Engineering"],
            "connection_type": "evidence_backed",
            "finding": "Customer support received surge of 90+ tickets reporting frozen payment on mobile devices on Nov 9 directly validating client-side engineering errors.",
            "supporting_evidence": [
                "Support alert on 2026-11-09T10:30:00Z with 90+ tickets"
            ]
        }
    ],
    "collaboration_rationale": "Engineering must diagnose and patch the mobile payment sheet, while Customer Support handles affected buyers and Finance accounts for lost transaction volume."
}

MOCK_ROUTER_RAW = {
    "primary_department": "Engineering",
    "collaborating_departments": ["Customer Support", "Product / Checkout"],
    "recommended_role_or_team": "Checkout Frontend Engineering Team",
    "priority": "Critical",
    "suggested_next_action": "Initiate emergency rollback of checkout frontend v2.4.0 or deploy hotfix for mobile payment sheet validation.",
    "routing_justification": "The root cause is a client-side Javascript exception and gateway timeout stemming directly from frontend release v2.4.0."
}

MOCK_WRITER_RAW = {
    "executive_summary": "Following the Nov 8 deployment of checkout frontend v2.4.0, mobile payment completion plunged by 70.73%, driving an estimated $15,300 revenue loss and 90+ support tickets.",
    "problem_statement": "Mobile checkout conversion dropped from 74.98% to 21.95% while desktop held steady at 74.97%, resulting in an 18.00% overall revenue decline in Week 2.",
    "confirmed_evidence": [
        "Mobile payment completion fell from 74.98% (Week 1) to 21.95% (Week 2).",
        "Frontend release v2.4.0 deployed at 2026-11-08T02:15:00Z.",
        "Payment gateway HTTP 504 timeouts logged starting 2026-11-08T06:45:00Z.",
        "Customer support logged 90+ tickets reporting frozen payment screens on iOS/Android."
    ],
    "likely_causes": [
        "Incompatible mobile payment sheet form validation logic in v2.4.0 causing uncaught Javascript exceptions and payment processor timeouts."
    ],
    "target_team_and_priority": "[Priority: Critical] Recommended for: Checkout Frontend Engineering Team (collaborating with Customer Support)",
    "recommended_action_plan": [
        "Immediately roll back checkout frontend to v2.3.9 or deploy hotfix.",
        "Inspect client-side error telemetry across iOS Safari and Android Chrome.",
        "Reach out to customers with abandoned carts during the failure window."
    ],
    "verification_and_success_criteria": [
        "Mobile payment completion returns to baseline >= 74.00% within 24 hours of fix.",
        "Zero new customer support tickets regarding frozen mobile checkout."
    ]
}


# ============================================================================
# 1. Independent Agent Unit Tests
# ============================================================================

def test_analyst_agent_success():
    facts = extract_mobile_payment_facts()
    agent = AnalystAgent()
    with patch("app.agents.roles.generate_json", return_value=MOCK_ANALYST_RAW):
        res = agent.run(facts)
        assert res.agent_name == "Analyst"
        assert res.status == "completed"
        assert isinstance(res.output, AnalystOutput)
        assert res.output.severity_assessment == "critical"
        assert len(res.output.key_metrics_validated) == 3
        assert "74.98%" in res.output.key_metrics_validated[0]
        assert res.error is None


def test_connector_agent_success():
    facts = extract_mobile_payment_facts()
    analyst_output = AnalystOutput(**MOCK_ANALYST_RAW)
    agent = ConnectorAgent()
    with patch("app.agents.roles.generate_json", return_value=MOCK_CONNECTOR_RAW):
        res = agent.run(facts, analyst_output)
        assert res.agent_name == "Connector"
        assert res.status == "completed"
        assert isinstance(res.output, ConnectorOutput)
        assert len(res.output.cross_department_connections) == 2
        assert res.output.cross_department_connections[0].connection_type == "evidence_backed"
        assert "Engineering" in res.output.cross_department_connections[0].departments_involved[0]


def test_router_agent_success():
    facts = extract_mobile_payment_facts()
    analyst_output = AnalystOutput(**MOCK_ANALYST_RAW)
    connector_output = ConnectorOutput(**MOCK_CONNECTOR_RAW)
    agent = RouterAgent()
    with patch("app.agents.roles.generate_json", return_value=MOCK_ROUTER_RAW):
        res = agent.run(facts, analyst_output, connector_output)
        assert res.agent_name == "Router"
        assert res.status == "completed"
        assert isinstance(res.output, RouterOutput)
        assert res.output.primary_department == "Engineering"
        assert res.output.priority == "Critical"
        assert "Checkout Frontend Engineering Team" in res.output.recommended_role_or_team
        # Verify no fake individual employee names
        assert "assigned to" not in res.output.recommended_role_or_team.lower()


def test_writer_agent_success():
    facts = extract_mobile_payment_facts()
    analyst_output = AnalystOutput(**MOCK_ANALYST_RAW)
    connector_output = ConnectorOutput(**MOCK_CONNECTOR_RAW)
    router_output = RouterOutput(**MOCK_ROUTER_RAW)
    agent = WriterAgent()
    with patch("app.agents.roles.generate_json", return_value=MOCK_WRITER_RAW):
        res = agent.run(facts, analyst_output, connector_output, router_output)
        assert res.agent_name == "Writer"
        assert res.status == "completed"
        assert isinstance(res.output, WriterOutput)
        assert "70.73%" in res.output.executive_summary
        assert len(res.output.confirmed_evidence) >= 3
        assert len(res.output.recommended_action_plan) >= 2


# ============================================================================
# 2. Complete Orchestration Pipeline Tests
# ============================================================================

def test_full_orchestration_pipeline_success():
    orchestrator = AgentOrchestrator()

    def mock_generate_json(prompt: str, model_name=None):
        if "ANALYST AGENT" in prompt:
            return MOCK_ANALYST_RAW
        elif "CONNECTOR AGENT" in prompt:
            return MOCK_CONNECTOR_RAW
        elif "ROUTER AGENT" in prompt:
            return MOCK_ROUTER_RAW
        elif "WRITER AGENT" in prompt:
            return MOCK_WRITER_RAW
        return {}

    with patch("app.agents.roles.generate_json", side_effect=mock_generate_json):
        res = orchestrator.run("ANOMALY_FUNNEL_MOBILE_001")
        assert isinstance(res, OrchestrationResponse)
        assert res.status == "completed"
        assert res.orchestration_id.startswith("ORCH-")

        # Check all 4 stages ran and completed
        assert res.stages.analyst.status == "completed"
        assert res.stages.connector.status == "completed"
        assert res.stages.router.status == "completed"
        assert res.stages.writer.status == "completed"

        # Evidence preservation
        assert res.facts.anomaly_id == "ANOMALY_FUNNEL_MOBILE_001"
        assert "74.98%" in res.facts.metric_facts["mobile_week1_payment_completion_rate"]
        assert len(res.facts.timeline_events) >= 3

        # Final action brief
        assert res.final_action_brief is not None
        assert "70.73%" in res.final_action_brief.executive_summary
        assert res.total_duration_ms > 0


def test_orchestration_preserves_evidence_for_revenue_and_profitability():
    orchestrator = AgentOrchestrator()

    def mock_generate_json(prompt: str, model_name=None):
        if "ANALYST AGENT" in prompt:
            return MOCK_ANALYST_RAW
        elif "CONNECTOR AGENT" in prompt:
            return MOCK_CONNECTOR_RAW
        elif "ROUTER AGENT" in prompt:
            return MOCK_ROUTER_RAW
        elif "WRITER AGENT" in prompt:
            return MOCK_WRITER_RAW
        return {}

    with patch("app.agents.roles.generate_json", side_effect=mock_generate_json):
        # Revenue decline
        res_rev = orchestrator.run("ANOMALY_REV_001")
        assert res_rev.facts.anomaly_id == "ANOMALY_REV_001"
        assert res_rev.facts.metric_facts["revenue_percentage_change"] == "-18.00%"

        # Profitability
        res_profit = orchestrator.run("ANOMALY_PROFIT_PROD_005")
        assert res_profit.facts.anomaly_id == "ANOMALY_PROFIT_PROD_005"
        assert res_profit.facts.metric_facts["gross_profit_margin_pct"] == "4.00%"


# ============================================================================
# 3. Stage Failure & Error Handling Tests
# ============================================================================

def test_orchestration_handles_analyst_failure_gracefully():
    orchestrator = AgentOrchestrator()
    # Analyst returns invalid schema missing key_metrics_validated
    invalid_analyst = {"invalid_key": "bad"}

    with patch("app.agents.roles.generate_json", return_value=invalid_analyst):
        res = orchestrator.run("ANOMALY_FUNNEL_MOBILE_001")
        assert res.status == "failed"
        assert res.stages.analyst.status == "failed"
        assert "validation failed" in res.stages.analyst.error.lower()
        # Downstream stages should be skipped
        assert res.stages.connector.status == "skipped"
        assert res.stages.router.status == "skipped"
        assert res.stages.writer.status == "skipped"
        assert res.final_action_brief is None


def test_orchestration_handles_connector_failure_gracefully():
    orchestrator = AgentOrchestrator()

    def mock_generate_json(prompt: str, model_name=None):
        if "ANALYST AGENT" in prompt:
            return MOCK_ANALYST_RAW
        elif "CONNECTOR AGENT" in prompt:
            return {"bad_schema": 123}
        return {}

    with patch("app.agents.roles.generate_json", side_effect=mock_generate_json):
        res = orchestrator.run("ANOMALY_FUNNEL_MOBILE_001")
        assert res.status == "failed"
        assert res.stages.analyst.status == "completed"
        assert res.stages.connector.status == "failed"
        assert res.stages.router.status == "skipped"
        assert res.stages.writer.status == "skipped"


def test_orchestration_handles_gemini_service_error():
    agent = AnalystAgent()
    facts = extract_mobile_payment_facts()
    with patch("app.agents.roles.generate_json", side_effect=GeminiServiceError("Quota exceeded")):
        res = agent.run(facts)
        assert res.status == "failed"
        assert "Quota exceeded" in res.error


# ============================================================================
# 4. API Endpoint Tests: POST /api/agents/run
# ============================================================================

def test_api_agents_run_endpoint_success(client):
    def mock_generate_json(prompt: str, model_name=None):
        if "ANALYST AGENT" in prompt:
            return MOCK_ANALYST_RAW
        elif "CONNECTOR AGENT" in prompt:
            return MOCK_CONNECTOR_RAW
        elif "ROUTER AGENT" in prompt:
            return MOCK_ROUTER_RAW
        elif "WRITER AGENT" in prompt:
            return MOCK_WRITER_RAW
        return {}

    with patch("app.agents.roles.generate_json", side_effect=mock_generate_json):
        resp = client.post("/api/agents/run", json={"anomaly_id": "ANOMALY_FUNNEL_MOBILE_001"})
        assert resp.status_code == 200
        data = resp.json()

        assert "orchestration_id" in data
        assert data["status"] == "completed"
        assert data["anomaly_id"] == "ANOMALY_FUNNEL_MOBILE_001"

        # Verify all 4 agent stages present in JSON
        stages = data["stages"]
        assert stages["analyst"]["status"] == "completed"
        assert stages["connector"]["status"] == "completed"
        assert stages["router"]["status"] == "completed"
        assert stages["writer"]["status"] == "completed"

        # Verify final action brief
        brief = data["final_action_brief"]
        assert brief is not None
        assert "executive_summary" in brief
        assert "recommended_action_plan" in brief


def test_api_agents_run_unsupported_anomaly(client):
    resp = client.post("/api/agents/run", json={"anomaly_id": "ANOMALY_UNKNOWN_INVALID"})
    assert resp.status_code == 400
    assert "Unsupported anomaly_id" in resp.json()["detail"]


def test_api_agents_run_auth_error(client):
    with patch(
        "app.main.run_agent_pipeline",
        side_effect=GeminiAuthError("GEMINI_API_KEY is not configured"),
    ):
        resp = client.post("/api/agents/run", json={})
        assert resp.status_code == 401
        assert "GEMINI_API_KEY is not configured" in resp.json()["detail"]


def test_api_investigate_endpoint_still_preserved(client):
    """Ensure Phase 2B/2C /api/investigate endpoint remains fully functional and intact."""
    from app.services.investigation_service import InvestigationResponse
    with patch("app.services.investigation_service.generate_json", return_value={
        "what_happened": "Issue occurred",
        "why_important": "Impact is high",
        "hypotheses": [{"cause": "Deployment bug", "supporting_evidence": ["Log 1"], "confidence_level": "high"}],
        "responsible_department": "Engineering",
        "recommended_actions": ["Rollback"],
        "verification_steps": ["Check conversion"]
    }):
        resp = client.post("/api/investigate", json={"anomaly_id": "ANOMALY_REV_001"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["facts"]["anomaly_id"] == "ANOMALY_REV_001"
