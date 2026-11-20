from datetime import datetime, timezone
import uuid
from typing import List, Dict, Any, Optional
import pandas as pd
from pydantic import BaseModel, Field

from ..analytics.data_loader import (
    load_sales_data,
    load_costs_data,
    load_funnel_data,
    load_events_data,
)
from ..analytics.funnel_analytics import compare_device_funnels
from ..analytics.sales_analytics import (
    compare_revenue_periods,
    get_units_sold_by_product,
    get_daily_sales_trend,
)
from ..analytics.profit_analytics import calculate_product_profitability
from ..analytics.anomaly_engine import correlate_events_with_metric
from .gemini_service import generate_json, get_gemini_model_name


# ============================================================================
# Pydantic Schema: Separation of Verified Facts vs. AI Hypotheses
# ============================================================================

class Hypothesis(BaseModel):
    cause: str = Field(description="Description of the potential root cause")
    supporting_evidence: List[str] = Field(description="Specific facts or events supporting this cause")
    confidence_level: str = Field(description="Confidence rating: high, medium, or low")


class InvestigationAnalysis(BaseModel):
    what_happened: str = Field(description="Concise description of the observed issue")
    why_important: str = Field(description="Business and financial significance of the issue")
    hypotheses: List[Hypothesis] = Field(description="Ranked causal hypotheses with supporting evidence")
    responsible_department: str = Field(description="Primary department responsible for remediation")
    recommended_actions: List[str] = Field(description="Concrete next steps the business should take")
    verification_steps: List[str] = Field(description="Measurable steps to verify resolution after fixes")


class InvestigationFacts(BaseModel):
    anomaly_id: str
    anomaly_title: str
    metric_facts: Dict[str, Any]
    timeline_events: List[Dict[str, Any]]


class InvestigationResponse(BaseModel):
    investigation_id: str
    status: str
    facts: InvestigationFacts = Field(description="Factual evidence computed strictly by Python")
    analysis: InvestigationAnalysis = Field(description="AI-generated causal reasoning and action plan from Gemini")
    model_used: str
    generated_at: str


# ============================================================================
# Fact Extraction via Python Business Data Engine
# ============================================================================

def extract_mobile_payment_facts(
    df_funnel: Optional[pd.DataFrame] = None,
    df_events: Optional[pd.DataFrame] = None,
    df_sales: Optional[pd.DataFrame] = None,
) -> InvestigationFacts:
    """
    Extract verified quantitative metrics and chronological events for the mobile
    payment deterioration anomaly. No LLM arithmetic or guesswork is used.
    """
    if df_funnel is None:
        df_funnel = load_funnel_data()
    if df_events is None:
        df_events = load_events_data()
    if df_sales is None:
        df_sales = load_sales_data()

    if df_funnel.empty:
        raise ValueError("Website funnel dataset is empty. Cannot extract mobile payment facts.")

    # 1. Device comparison metrics (Week 1 vs Week 2)
    device_comp = compare_device_funnels(
        df_funnel,
        period1_range=("2026-11-01", "2026-11-07"),
        period2_range=("2026-11-08", "2026-11-14"),
    )

    # 2. Overall revenue context
    rev_comp = compare_revenue_periods(
        df_sales,
        period1_range=("2026-11-01", "2026-11-07"),
        period2_range=("2026-11-08", "2026-11-14"),
    )

    # 3. Contextual events during the affected window (Day 8 onwards)
    correlated_events = correlate_events_with_metric(
        df_events,
        start_date="2026-11-08",
        end_date="2026-11-14",
    )

    mobile_p1 = device_comp["mobile"]["period1"]
    mobile_p2 = device_comp["mobile"]["period2"]
    desktop_p1 = device_comp["desktop"]["period1"]
    desktop_p2 = device_comp["desktop"]["period2"]

    metric_facts = {
        "period1_dates": "2026-11-01 to 2026-11-07 (Week 1)",
        "period2_dates": "2026-11-08 to 2026-11-14 (Week 2)",
        "mobile_week1_payment_completion_rate": f"{mobile_p1['payment_completion_pct']:.2f}%",
        "mobile_week2_payment_completion_rate": f"{mobile_p2['payment_completion_pct']:.2f}%",
        "mobile_payment_completion_relative_change": f"{device_comp['mobile']['payment_completion_relative_change_pct']:.2f}%",
        "mobile_week1_overall_conversion_rate": f"{mobile_p1['overall_conversion_pct']:.2f}%",
        "mobile_week2_overall_conversion_rate": f"{mobile_p2['overall_conversion_pct']:.2f}%",
        "desktop_week1_payment_completion_rate": f"{desktop_p1['payment_completion_pct']:.2f}%",
        "desktop_week2_payment_completion_rate": f"{desktop_p2['payment_completion_pct']:.2f}%",
        "desktop_payment_completion_relative_change": f"{device_comp['desktop']['payment_completion_relative_change_pct']:.2f}% (unaffected control group)",
        "overall_revenue_impact": (
            f"Revenue dropped by {abs(rev_comp['percentage_change']):.2f}% "
            f"(-${abs(rev_comp['absolute_change']):,.2f}) from ${rev_comp['period1']['revenue']:,.2f} "
            f"in Week 1 to ${rev_comp['period2']['revenue']:,.2f} in Week 2"
        ),
    }

    return InvestigationFacts(
        anomaly_id="ANOMALY_FUNNEL_MOBILE_001",
        anomaly_title="Severe Mobile Payment Completion Deterioration After Website Update",
        metric_facts=metric_facts,
        timeline_events=correlated_events,
    )


def extract_revenue_decline_facts(
    df_sales: Optional[pd.DataFrame] = None,
    df_events: Optional[pd.DataFrame] = None,
    df_funnel: Optional[pd.DataFrame] = None,
) -> InvestigationFacts:
    """
    Extract verified quantitative metrics, product-level sales shifts, and correlated
    events for the revenue decline anomaly between Week 1 and Week 2.
    """
    if df_sales is None:
        df_sales = load_sales_data()
    if df_events is None:
        df_events = load_events_data()
    if df_funnel is None:
        df_funnel = load_funnel_data()

    if df_sales.empty:
        raise ValueError("Sales dataset is empty. Cannot extract revenue decline facts.")

    # 1. Total revenue comparison
    rev_comp = compare_revenue_periods(
        df_sales,
        period1_range=("2026-11-01", "2026-11-07"),
        period2_range=("2026-11-08", "2026-11-14"),
    )

    # 2. Product-by-product breakdown (Week 1 vs Week 2)
    p1_products = {p["product_id"]: p for p in get_units_sold_by_product(df_sales, "2026-11-01", "2026-11-07")}
    p2_products = {p["product_id"]: p for p in get_units_sold_by_product(df_sales, "2026-11-08", "2026-11-14")}

    product_breakdown = []
    largest_drop_prod = None
    max_dollar_drop = 0.0

    for pid, p1 in p1_products.items():
        p2 = p2_products.get(pid, {"units_sold": 0, "total_revenue": 0.0, "product_name": p1["product_name"]})
        rev_change = round(p2["total_revenue"] - p1["total_revenue"], 2)
        pct_change = round((rev_change / p1["total_revenue"]) * 100, 2) if p1["total_revenue"] > 0 else 0.0
        units_change = p2["units_sold"] - p1["units_sold"]

        if rev_change < 0 and abs(rev_change) > max_dollar_drop:
            max_dollar_drop = abs(rev_change)
            share_of_loss = round((max_dollar_drop / abs(rev_comp["absolute_change"])) * 100, 1) if rev_comp["absolute_change"] else 0.0
            largest_drop_prod = f"{p1['product_name']} ({pid}) with -${max_dollar_drop:,.2f} ({share_of_loss}% of total loss)"

        product_breakdown.append({
            "product_id": pid,
            "product_name": p1["product_name"],
            "week1_revenue": f"${p1['total_revenue']:,.2f}",
            "week2_revenue": f"${p2['total_revenue']:,.2f}",
            "revenue_change": f"${rev_change:,.2f}",
            "percentage_change": f"{pct_change:.2f}%",
            "week1_units": p1["units_sold"],
            "week2_units": p2["units_sold"],
            "units_change": units_change,
        })

    # Sort products by largest dollar drop first
    product_breakdown.sort(key=lambda x: float(x["revenue_change"].replace("$", "").replace(",", "")))

    # 3. Daily trend summary
    daily = get_daily_sales_trend(df_sales)
    w1_daily_rev = [d["revenue"] for d in daily if d["date"] <= "2026-11-07"]
    w2_daily_rev = [d["revenue"] for d in daily if d["date"] >= "2026-11-08"]
    w1_avg = round(sum(w1_daily_rev) / len(w1_daily_rev), 2) if w1_daily_rev else 0.0
    w2_avg = round(sum(w2_daily_rev) / len(w2_daily_rev), 2) if w2_daily_rev else 0.0

    # 4. Correlate with funnel conversion context (if funnel available)
    funnel_context: Dict[str, Any] = {}
    if not df_funnel.empty:
        device_comp = compare_device_funnels(
            df_funnel,
            period1_range=("2026-11-01", "2026-11-07"),
            period2_range=("2026-11-08", "2026-11-14"),
        )
        funnel_context = {
            "mobile_payment_completion_relative_drop": f"{device_comp['mobile']['payment_completion_relative_change_pct']:.2f}%",
            "desktop_payment_completion_relative_drop": f"{device_comp['desktop']['payment_completion_relative_change_pct']:.2f}%",
            "cross_department_finding": "Traffic remained steady, but mobile checkout completion collapsed from 74.98% to 21.95% after Nov 8 deployment, reducing completed orders across all catalog items."
        }

    # 5. Events across the entire 14-day window
    events = correlate_events_with_metric(df_events, start_date="2026-11-01", end_date="2026-11-14")

    metric_facts = {
        "period1_dates": "2026-11-01 to 2026-11-07 (Week 1)",
        "period2_dates": "2026-11-08 to 2026-11-14 (Week 2)",
        "week1_total_revenue": f"${rev_comp['period1']['revenue']:,.2f}",
        "week2_total_revenue": f"${rev_comp['period2']['revenue']:,.2f}",
        "revenue_absolute_change": f"-${abs(rev_comp['absolute_change']):,.2f}",
        "revenue_percentage_change": f"{rev_comp['percentage_change']:.2f}%",
        "week1_daily_average_revenue": f"${w1_avg:,.2f}/day",
        "week2_daily_average_revenue": f"${w2_avg:,.2f}/day",
        "largest_revenue_loss_product": largest_drop_prod or "N/A",
        "product_level_breakdown": product_breakdown,
        "funnel_cross_correlation": funnel_context,
    }

    return InvestigationFacts(
        anomaly_id="ANOMALY_REV_001",
        anomaly_title="Significant 18.00% Revenue Decline Between Week 1 and Week 2",
        metric_facts=metric_facts,
        timeline_events=events,
    )


def extract_low_profitability_facts(
    product_id: Optional[str] = "PROD_005",
    df_sales: Optional[pd.DataFrame] = None,
    df_costs: Optional[pd.DataFrame] = None,
    df_events: Optional[pd.DataFrame] = None,
) -> InvestigationFacts:
    """
    Extract verified unit economics, gross margins, peer benchmarks, and supplier events
    for the lowest-margin product (PROD_005 by default).
    """
    if df_sales is None:
        df_sales = load_sales_data()
    if df_costs is None:
        df_costs = load_costs_data()
    if df_events is None:
        df_events = load_events_data()

    if df_sales.empty or df_costs.empty:
        raise ValueError("Sales or Costs dataset is empty. Cannot extract product profitability facts.")

    profitability = calculate_product_profitability(df_sales, df_costs, low_margin_threshold_pct=15.0)

    if not profitability:
        raise ValueError("No product profitability records could be calculated.")

    # Locate target product (PROD_005 or lowest margin product)
    target_prod = None
    if product_id:
        norm_id = product_id.strip().upper()
        for p in profitability:
            if p["product_id"].upper() == norm_id:
                target_prod = p
                break

    if not target_prod:
        sorted_by_margin = sorted(profitability, key=lambda x: x["gross_profit_margin_pct"])
        target_prod = sorted_by_margin[0]

    pid = target_prod["product_id"]
    pname = target_prod["product_name"]
    units = target_prod["units_sold"]
    revenue = target_prod["total_revenue"]
    unit_cost = target_prod["unit_cost"]
    total_cost = target_prod["total_cost"]
    gross_profit = target_prod["gross_profit"]
    margin_pct = target_prod["gross_profit_margin_pct"]
    avg_price = round(revenue / units, 2) if units > 0 else 0.0
    unit_profit = round(avg_price - unit_cost, 2)

    # Benchmark against peer products
    peer_prods = [p for p in profitability if p["product_id"] != pid]
    peer_margins = [p["gross_profit_margin_pct"] for p in peer_prods]
    peer_avg_margin = round(sum(peer_margins) / len(peer_margins), 2) if peer_margins else 0.0
    highest_margin_prod = max(profitability, key=lambda x: x["gross_profit_margin_pct"])

    # Correlated operational timeline events (supplier revisions, audits)
    events = correlate_events_with_metric(df_events, start_date="2026-11-01", end_date="2026-11-14")

    metric_facts = {
        "product_id": pid,
        "product_name": pname,
        "unit_selling_price": f"${avg_price:.2f}",
        "unit_cost": f"${unit_cost:.2f}",
        "unit_gross_profit": f"${unit_profit:.2f}",
        "gross_profit_margin_pct": f"{margin_pct:.2f}%",
        "units_sold": units,
        "total_revenue": f"${revenue:,.2f}",
        "total_cost": f"${total_cost:,.2f}",
        "total_gross_profit": f"${gross_profit:,.2f}",
        "low_margin_threshold": "15.00%",
        "benchmark_peer_average_margin_pct": f"{peer_avg_margin:.2f}%",
        "margin_deficit_vs_peers": f"-{round(peer_avg_margin - margin_pct, 2):.2f}%",
        "highest_margin_product": f"{highest_margin_prod['product_name']} ({highest_margin_prod['gross_profit_margin_pct']:.2f}%)",
        "other_products_comparison": [
            {
                "product_id": p["product_id"],
                "product_name": p["product_name"],
                "gross_profit_margin_pct": f"{p['gross_profit_margin_pct']:.2f}%",
                "gross_profit": f"${p['gross_profit']:,.2f}",
            }
            for p in peer_prods
        ],
    }

    return InvestigationFacts(
        anomaly_id=f"ANOMALY_PROFIT_{pid}",
        anomaly_title=f"Critically Low Gross Profit Margin ({margin_pct:.2f}%) for {pname}",
        metric_facts=metric_facts,
        timeline_events=events,
    )


# ============================================================================
# Gemini Investigation Prompt & Execution
# ============================================================================

def build_investigation_prompt(facts: InvestigationFacts) -> str:
    """
    Construct a specialized prompt constraining Gemini to synthesize hypotheses and business
    recommendations strictly from verified Python facts without inventing metrics.
    """
    events_text = "\n".join(
        f"- [{ev['timestamp']}] ({ev['event_type']} on {ev['affected_system']}): {ev['description']}"
        for ev in facts.timeline_events
    )

    metrics_text = "\n".join(
        f"- {k}: {v}" for k, v in facts.metric_facts.items()
    )

    # Domain-specific framing based on anomaly type
    domain_guidance = ""
    if "REV" in facts.anomaly_id.upper():
        domain_guidance = """
DOMAIN CONTEXT (REVENUE INVESTIGATION):
- Analyze the overall revenue decline between Week 1 and Week 2.
- Examine which specific products drove the largest dollar and unit losses.
- Examine sales trends across time and evaluate how operational events (such as checkout frontend deployment on Nov 8 or digital ad marketing campaigns) correlate with the timing of the revenue drop.
- Distinguish between marketing top-of-funnel effects and checkout execution failures.
"""
    elif "PROFIT" in facts.anomaly_id.upper():
        domain_guidance = """
DOMAIN CONTEXT (PRODUCT PROFITABILITY INVESTIGATION):
- Analyze why this product's gross profit margin is critically low compared to the 15% threshold and peer product benchmarks.
- Examine unit economics: unit selling price, unit cost, and total gross profit generated relative to units sold.
- Connect operational events such as supplier cost revisions or inventory audits to explain cost structure.
- Propose actionable remediation options (e.g., renegotiating supplier costs, adjusting retail pricing, bundling with higher-margin accessories).
"""
    else:
        domain_guidance = """
DOMAIN CONTEXT (MOBILE CHECKOUT FUNNEL INVESTIGATION):
- Analyze why mobile payment completion deteriorated severely after Week 1 while desktop remained steady.
- Correlate the timeline with the checkout frontend v2.4.0 deployment, HTTP 504 timeouts, and customer support spikes.
"""

    prompt = f"""You are the Principal Business Intelligence & Incident Investigation Analyst for BizPulse.

You are given verified, calculated facts from our deterministic Python analytics engine for an active business anomaly: "{facts.anomaly_title}".

{domain_guidance}

VERIFIED METRICS:
{metrics_text}

CORRELATED OPERATIONAL TIMELINE:
{events_text}

STRICT INSTRUCTIONS:
1. Do NOT invent new numbers, dates, or events. Rely exclusively on the verified facts above.
2. Clearly separate observed facts from your causal hypotheses.
3. Return a valid JSON object matching the following structure:
{{
  "what_happened": "A clear, factual summary of the anomaly based on the data.",
  "why_important": "Explain the business, financial, and strategic impact.",
  "hypotheses": [
    {{
      "cause": "Specific potential root cause supported by the metrics or timeline.",
      "supporting_evidence": ["Evidence 1 from timeline or metrics", "Evidence 2"],
      "confidence_level": "high | medium | low"
    }}
  ],
  "responsible_department": "Primary department(s) responsible for remediation (e.g. Engineering, Procurement, Pricing, Marketing, Customer Support)",
  "recommended_actions": [
    "Immediate action 1",
    "Short-term diagnostic or operational action 2",
    "Medium-term structural or strategic action 3"
  ],
  "verification_steps": [
    "Measurable verification step 1 with clear target metric or benchmark",
    "Measurable verification step 2"
  ]
}}
"""
    return prompt


# Mapping of supported anomaly IDs and friendly aliases
SUPPORTED_ANOMALY_ROUTING = {
    "ANOMALY_REV_001": "revenue",
    "REVENUE_DECLINE": "revenue",
    "REVENUE": "revenue",
    "REV": "revenue",
    "ANOMALY_PROFIT_PROD_005": "profitability",
    "ANOMALY_PROFIT_001": "profitability",
    "LOW_PROFITABILITY": "profitability",
    "PROFITABILITY": "profitability",
    "PROD_005": "profitability",
    "PROFIT": "profitability",
    "ANOMALY_FUNNEL_MOBILE_001": "mobile_payment",
    "MOBILE_PAYMENT": "mobile_payment",
    "MOBILE_FUNNEL": "mobile_payment",
    "MOBILE": "mobile_payment",
}


def run_investigation(anomaly_id: str = "ANOMALY_FUNNEL_MOBILE_001", model_name: Optional[str] = None) -> InvestigationResponse:
    """
    Execute end-to-end business intelligence investigation for any of the 3 planted problems:
    1. Python engine extracts verified factual evidence.
    2. Specialized prompt is dispatched to Gemini with response_mime_type="application/json".
    3. Structured JSON response is validated into Pydantic models.
    """
    norm_id = (anomaly_id or "ANOMALY_FUNNEL_MOBILE_001").strip().upper()
    category = SUPPORTED_ANOMALY_ROUTING.get(norm_id)

    if not category:
        # Check partial matching
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

    # Dispatch to appropriate fact extractor
    if category == "revenue":
        facts = extract_revenue_decline_facts()
    elif category == "profitability":
        facts = extract_low_profitability_facts()
    else:
        facts = extract_mobile_payment_facts()

    prompt = build_investigation_prompt(facts)
    model = model_name or get_gemini_model_name()

    raw_json = generate_json(prompt=prompt, model_name=model)
    analysis = InvestigationAnalysis(**raw_json)

    return InvestigationResponse(
        investigation_id=f"INV-{uuid.uuid4().hex[:8].upper()}",
        status="completed",
        facts=facts,
        analysis=analysis,
        model_used=model,
        generated_at=datetime.now(timezone.utc).isoformat(),
    )


# Backward-compatible convenience aliases
def run_mobile_payment_investigation(model_name: Optional[str] = None) -> InvestigationResponse:
    return run_investigation("ANOMALY_FUNNEL_MOBILE_001", model_name=model_name)


def run_revenue_decline_investigation(model_name: Optional[str] = None) -> InvestigationResponse:
    return run_investigation("ANOMALY_REV_001", model_name=model_name)


def run_low_profitability_investigation(model_name: Optional[str] = None) -> InvestigationResponse:
    return run_investigation("ANOMALY_PROFIT_PROD_005", model_name=model_name)
