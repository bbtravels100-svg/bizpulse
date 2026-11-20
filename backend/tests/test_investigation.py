import pytest
import pandas as pd
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from app.main import app
from app.services.investigation_service import (
    extract_mobile_payment_facts,
    extract_revenue_decline_facts,
    extract_low_profitability_facts,
    build_investigation_prompt,
    run_investigation,
    run_mobile_payment_investigation,
    run_revenue_decline_investigation,
    run_low_profitability_investigation,
    InvestigationFacts,
    InvestigationAnalysis,
    InvestigationResponse,
    Hypothesis,
)
from app.services.gemini_service import GeminiAuthError, GeminiServiceError


@pytest.fixture
def client():
    return TestClient(app)


MOCK_MOBILE_ANALYSIS_JSON = {
    "what_happened": "Mobile payment completion crashed from 74.98% down to 21.95% after checkout frontend v2.4.0 was deployed.",
    "why_important": "Mobile accounts for the majority of visitors, resulting in an estimated 18.00% drop in total company revenue ($15,300 lost).",
    "hypotheses": [
        {
            "cause": "Frontend checkout v2.4.0 mobile payment sheet contains Javascript bug causing payment processor timeouts.",
            "supporting_evidence": [
                "Deploys at 2026-11-08T02:15:00Z immediately preceded 504 timeouts at 06:45:00Z.",
                "Customer support logged 90+ tickets reporting frozen screens on iOS/Android.",
                "Desktop checkout completion remained steady at 74.97%."
            ],
            "confidence_level": "high"
        }
    ],
    "responsible_department": "Engineering (Checkout & Mobile Frontend)",
    "recommended_actions": [
        "Roll back or hotfix checkout frontend v2.4.0 mobile payment sheet.",
        "Inspect payment gateway HTTP 504 timeout logs."
    ],
    "verification_steps": [
        "Monitor mobile payment completion rate in real time until it returns to ~75%.",
        "Verify 0 new customer support tickets regarding frozen mobile checkout."
    ]
}

MOCK_REVENUE_ANALYSIS_JSON = {
    "what_happened": "Company revenue declined by 18.00% (-$15,300.00) from $85,000.00 in Week 1 to $69,700.00 in Week 2, driven by sharp declines across all five product categories.",
    "why_important": "A sustained $15,300 weekly run-rate loss impacts operating cash flow and profitability, led by Ultra Ergonomic Desk Chair which alone lost $7,350.00.",
    "hypotheses": [
        {
            "cause": "The catastrophic failure in mobile checkout completion (collapsed from 75% to 22%) blocked high-intent buyers from completing orders starting Nov 8.",
            "supporting_evidence": [
                "Daily revenue abruptly fell from ~$12,142/day to ~$9,957/day starting on Nov 8.",
                "Checkout frontend v2.4.0 was deployed on Nov 8 at 02:15 UTC followed by gateway 504 timeouts.",
                "All 5 products exhibited ~16-19% volume drops, indicating a systemic platform issue rather than product-specific demand loss."
            ],
            "confidence_level": "high"
        }
    ],
    "responsible_department": "Cross-Functional (Engineering & Product Sales)",
    "recommended_actions": [
        "Resolve mobile payment gateway timeouts to restore checkout conversion.",
        "Launch targeted retargeting campaign for customers with abandoned carts during Week 2."
    ],
    "verification_steps": [
        "Verify daily revenue recovers to baseline >= $12,000.00/day.",
        "Confirm weekly sales exceed $84,000.00."
    ]
}

MOCK_PROFIT_ANALYSIS_JSON = {
    "what_happened": "Heavy Duty Gaming Monitor Stand (PROD_005) operates at an unsustainably low gross profit margin of 4.00%, generating only $1.80 profit per unit sold.",
    "why_important": "Despite generating $11,880.00 in revenue across 264 units sold, the product yielded only $475.20 in total gross profit, severely lagging peer products averaging 46.25% margin.",
    "hypotheses": [
        {
            "cause": "Unit cost of $43.20 is misaligned with the $45.00 selling price following supplier cost revisions logged on Nov 11.",
            "supporting_evidence": [
                "Unit cost is $43.20 while average selling price is $45.00.",
                "Supplier cost revision was recorded on 2026-11-11 in inventory audit events.",
                "Peer products maintain margins between 40% and 50%."
            ],
            "confidence_level": "high"
        }
    ],
    "responsible_department": "Procurement & Pricing Strategy",
    "recommended_actions": [
        "Renegotiate wholesale procurement pricing with component suppliers.",
        "Increase retail price from $45.00 to $65.00 to achieve ~33% gross margin.",
        "Bundle with high-margin items like keyboard or headphones."
    ],
    "verification_steps": [
        "Confirm gross margin exceeds 25.0% on next 100 units sold.",
        "Verify gross profit per unit reaches at least $15.00."
    ]
}


# ============================================================================
# Unit Tests for Python Fact Extractions
# ============================================================================

def test_extract_mobile_payment_facts_values():
    """Verify that Python strictly computes the factual numbers for mobile payment deterioration."""
    facts = extract_mobile_payment_facts()
    assert isinstance(facts, InvestigationFacts)
    assert facts.anomaly_id == "ANOMALY_FUNNEL_MOBILE_001"
    
    metrics = facts.metric_facts
    assert metrics["mobile_week1_payment_completion_rate"] == "74.98%"
    assert metrics["mobile_week2_payment_completion_rate"] == "21.95%"
    assert metrics["mobile_payment_completion_relative_change"] == "-70.73%"
    assert "74.97%" in metrics["desktop_week1_payment_completion_rate"]
    assert "74.97%" in metrics["desktop_week2_payment_completion_rate"]
    assert "18.00%" in metrics["overall_revenue_impact"]
    assert "-$15,300.00" in metrics["overall_revenue_impact"]
    
    events = facts.timeline_events
    assert len(events) >= 3
    descriptions = [e["description"].lower() for e in events]
    assert any("checkout frontend v2.4.0" in d for d in descriptions)
    assert any("504" in d for d in descriptions)


def test_extract_revenue_decline_facts_values():
    """Verify that Python strictly computes the factual numbers for Week 1 vs Week 2 revenue decline."""
    facts = extract_revenue_decline_facts()
    assert isinstance(facts, InvestigationFacts)
    assert facts.anomaly_id == "ANOMALY_REV_001"
    
    metrics = facts.metric_facts
    assert metrics["week1_total_revenue"] == "$85,000.00"
    assert metrics["week2_total_revenue"] == "$69,700.00"
    assert metrics["revenue_absolute_change"] == "-$15,300.00"
    assert metrics["revenue_percentage_change"] == "-18.00%"
    assert metrics["week1_daily_average_revenue"] == "$12,142.86/day"
    assert metrics["week2_daily_average_revenue"] == "$9,957.14/day"
    
    # Largest dollar drop product
    assert "PROD_001" in metrics["largest_revenue_loss_product"]
    assert "-$7,350.00" in metrics["largest_revenue_loss_product"]
    assert "48.0%" in metrics["largest_revenue_loss_product"] or "48" in metrics["largest_revenue_loss_product"]
    
    # Product-by-product breakdown contains all 5 items
    breakdown = metrics["product_level_breakdown"]
    assert len(breakdown) == 5
    prod_map = {p["product_id"]: p for p in breakdown}
    assert prod_map["PROD_001"]["week1_revenue"] == "$38,850.00"
    assert prod_map["PROD_001"]["week2_revenue"] == "$31,500.00"
    assert prod_map["PROD_002"]["week1_revenue"] == "$22,680.00"
    assert prod_map["PROD_005"]["week1_revenue"] == "$6,525.00"
    
    # Correlated events include marketing and deployment
    events = facts.timeline_events
    assert len(events) >= 5
    descriptions = [e["description"].lower() for e in events]
    assert any("marketing" in d or "digital ads" in d for d in descriptions)
    assert any("checkout frontend v2.4.0" in d for d in descriptions)


def test_extract_low_profitability_facts_values():
    """Verify that Python strictly computes the factual numbers for low product profitability."""
    facts = extract_low_profitability_facts(product_id="PROD_005")
    assert isinstance(facts, InvestigationFacts)
    assert facts.anomaly_id == "ANOMALY_PROFIT_PROD_005"
    
    metrics = facts.metric_facts
    assert metrics["product_id"] == "PROD_005"
    assert metrics["product_name"] == "Heavy Duty Gaming Monitor Stand"
    assert metrics["unit_selling_price"] == "$45.00"
    assert metrics["unit_cost"] == "$43.20"
    assert metrics["unit_gross_profit"] == "$1.80"
    assert metrics["gross_profit_margin_pct"] == "4.00%"
    assert metrics["units_sold"] == 264
    assert metrics["total_revenue"] == "$11,880.00"
    assert metrics["total_cost"] == "$11,404.80"
    assert metrics["total_gross_profit"] == "$475.20"
    assert metrics["low_margin_threshold"] == "15.00%"
    assert metrics["benchmark_peer_average_margin_pct"] == "46.25%"
    assert metrics["margin_deficit_vs_peers"] == "-42.25%"
    
    # Check inventory audit event
    events = facts.timeline_events
    assert any("supplier cost revision" in e["description"].lower() for e in events)


def test_build_investigation_prompt_contents():
    """Verify prompt formatting and domain guidance for each anomaly."""
    rev_facts = extract_revenue_decline_facts()
    rev_prompt = build_investigation_prompt(rev_facts)
    assert "$85,000.00" in rev_prompt
    assert "-$15,300.00" in rev_prompt
    assert "REVENUE INVESTIGATION" in rev_prompt

    profit_facts = extract_low_profitability_facts()
    profit_prompt = build_investigation_prompt(profit_facts)
    assert "PROD_005" in profit_prompt
    assert "4.00%" in profit_prompt
    assert "PRODUCT PROFITABILITY INVESTIGATION" in profit_prompt


# ============================================================================
# Mocked Multi-Problem Investigation Runner Tests
# ============================================================================

def test_run_investigation_revenue_decline():
    with patch("app.services.investigation_service.generate_json", return_value=MOCK_REVENUE_ANALYSIS_JSON):
        resp = run_investigation("ANOMALY_REV_001")
        assert isinstance(resp, InvestigationResponse)
        assert resp.status == "completed"
        assert resp.facts.anomaly_id == "ANOMALY_REV_001"
        assert resp.facts.metric_facts["revenue_percentage_change"] == "-18.00%"
        assert resp.analysis.responsible_department == "Cross-Functional (Engineering & Product Sales)"
        assert len(resp.analysis.hypotheses) == 1
        assert resp.analysis.hypotheses[0].confidence_level == "high"


def test_run_investigation_low_profitability():
    with patch("app.services.investigation_service.generate_json", return_value=MOCK_PROFIT_ANALYSIS_JSON):
        resp = run_investigation("ANOMALY_PROFIT_PROD_005")
        assert isinstance(resp, InvestigationResponse)
        assert resp.status == "completed"
        assert resp.facts.anomaly_id == "ANOMALY_PROFIT_PROD_005"
        assert resp.facts.metric_facts["gross_profit_margin_pct"] == "4.00%"
        assert resp.analysis.responsible_department == "Procurement & Pricing Strategy"


def test_run_investigation_mobile_payment():
    with patch("app.services.investigation_service.generate_json", return_value=MOCK_MOBILE_ANALYSIS_JSON):
        resp = run_investigation("ANOMALY_FUNNEL_MOBILE_001")
        assert isinstance(resp, InvestigationResponse)
        assert resp.status == "completed"
        assert resp.facts.anomaly_id == "ANOMALY_FUNNEL_MOBILE_001"
        assert resp.facts.metric_facts["mobile_payment_completion_relative_change"] == "-70.73%"


# ============================================================================
# API Endpoint Tests (POST /api/investigate)
# ============================================================================

def test_api_investigate_revenue_decline(client):
    with patch("app.services.investigation_service.generate_json", return_value=MOCK_REVENUE_ANALYSIS_JSON):
        resp = client.post("/api/investigate", json={"anomaly_id": "ANOMALY_REV_001"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["facts"]["anomaly_id"] == "ANOMALY_REV_001"
        assert data["facts"]["metric_facts"]["revenue_percentage_change"] == "-18.00%"
        assert "revenue" in data["facts"]["anomaly_title"].lower()


def test_api_investigate_low_profitability(client):
    with patch("app.services.investigation_service.generate_json", return_value=MOCK_PROFIT_ANALYSIS_JSON):
        resp = client.post("/api/investigate", json={"anomaly_id": "ANOMALY_PROFIT_PROD_005"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["facts"]["anomaly_id"] == "ANOMALY_PROFIT_PROD_005"
        assert data["facts"]["metric_facts"]["gross_profit_margin_pct"] == "4.00%"


def test_api_investigate_mobile_payment(client):
    with patch("app.services.investigation_service.generate_json", return_value=MOCK_MOBILE_ANALYSIS_JSON):
        resp = client.post("/api/investigate", json={"anomaly_id": "ANOMALY_FUNNEL_MOBILE_001"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["facts"]["anomaly_id"] == "ANOMALY_FUNNEL_MOBILE_001"
        assert data["facts"]["metric_facts"]["mobile_week2_payment_completion_rate"] == "21.95%"


def test_api_investigate_friendly_aliases(client):
    """Test that human-friendly aliases like 'revenue' or 'profitability' route correctly."""
    with patch("app.services.investigation_service.generate_json", return_value=MOCK_REVENUE_ANALYSIS_JSON):
        resp = client.post("/api/investigate", json={"anomaly_id": "revenue_decline"})
        assert resp.status_code == 200
        assert resp.json()["facts"]["anomaly_id"] == "ANOMALY_REV_001"

    with patch("app.services.investigation_service.generate_json", return_value=MOCK_PROFIT_ANALYSIS_JSON):
        resp = client.post("/api/investigate", json={"anomaly_id": "low_profitability"})
        assert resp.status_code == 200
        assert resp.json()["facts"]["anomaly_id"] == "ANOMALY_PROFIT_PROD_005"


def test_api_investigate_unsupported_anomaly(client):
    resp = client.post("/api/investigate", json={"anomaly_id": "ANOMALY_UNKNOWN_XYZ"})
    assert resp.status_code == 400
    assert "Unsupported anomaly_id" in resp.json()["detail"]


def test_extract_facts_empty_data_defensive():
    """Verify that empty datasets raise clear ValueErrors rather than crashing unhandled."""
    with pytest.raises(ValueError, match="Sales dataset is empty"):
        extract_revenue_decline_facts(df_sales=pd.DataFrame())

    with pytest.raises(ValueError, match="Sales or Costs dataset is empty"):
        extract_low_profitability_facts(df_sales=pd.DataFrame(), df_costs=pd.DataFrame())

    with pytest.raises(ValueError, match="Website funnel dataset is empty"):
        extract_mobile_payment_facts(df_funnel=pd.DataFrame())


def test_api_investigate_auth_error(client):
    with patch(
        "app.main.run_investigation",
        side_effect=GeminiAuthError("GEMINI_API_KEY is not configured"),
    ):
        resp = client.post("/api/investigate", json={})
        assert resp.status_code == 401
        assert "GEMINI_API_KEY is not configured" in resp.json()["detail"]


def test_api_investigate_service_error(client):
    with patch(
        "app.main.run_investigation",
        side_effect=GeminiServiceError("Gemini quota exceeded"),
    ):
        resp = client.post("/api/investigate", json={})
        assert resp.status_code == 502
        assert "Gemini quota exceeded" in resp.json()["detail"]
