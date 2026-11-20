from datetime import date, datetime
from typing import Dict, List, Optional, Any
import pandas as pd

from .sales_analytics import compare_revenue_periods
from .profit_analytics import calculate_product_profitability
from .funnel_analytics import compare_device_funnels

def correlate_events_with_metric(
    df_events: pd.DataFrame,
    start_date: date | str,
    end_date: Optional[date | str] = None,
    affected_system_filter: Optional[str] = None,
) -> List[Dict[str, str]]:
    """
    Search events that occurred during or near a detected anomaly window.
    """
    if df_events.empty:
        return []

    s_dt = pd.to_datetime(start_date, utc=True)
    events_filtered = df_events[df_events["timestamp"] >= s_dt].copy()

    if end_date is not None:
        e_dt = pd.to_datetime(end_date, utc=True) + pd.Timedelta(days=1)
        events_filtered = events_filtered[events_filtered["timestamp"] <= e_dt]

    if affected_system_filter is not None:
        events_filtered = events_filtered[
            events_filtered["affected_system"].str.contains(affected_system_filter, case=False, na=False)
        ]

    results = []
    for _, row in events_filtered.sort_values("timestamp").iterrows():
        results.append({
            "timestamp": row["timestamp"].isoformat(),
            "event_type": str(row["event_type"]),
            "description": str(row["description"]),
            "affected_system": str(row["affected_system"]),
        })
    return results

def detect_all_anomalies(
    df_sales: pd.DataFrame,
    df_costs: pd.DataFrame,
    df_funnel: pd.DataFrame,
    df_events: pd.DataFrame,
    period1_range: tuple = ("2026-11-01", "2026-11-07"),
    period2_range: tuple = ("2026-11-08", "2026-11-14"),
) -> List[Dict[str, Any]]:
    """
    Master anomaly detection engine. Evaluates business health across:
    1. Revenue decline (~18% drop between week 1 and week 2).
    2. Low product gross profit margins (< 15%).
    3. Mobile payment conversion deterioration after website deployment.
    Attaches supporting events from events.csv as contextual evidence.
    """
    anomalies: List[Dict[str, Any]] = []

    # ---------------------------------------------------------
    # Problem 1: Revenue Decline Anomaly Detection
    # ---------------------------------------------------------
    rev_comp = compare_revenue_periods(df_sales, period1_range, period2_range)
    if rev_comp["percentage_change"] < -10.0:
        pct_drop = abs(rev_comp["percentage_change"])
        anomalies.append({
            "anomaly_id": "ANOMALY_REV_001",
            "title": "Significant Revenue Decline in Week 2",
            "category": "revenue",
            "severity": "critical",
            "description": (
                f"Revenue declined by {pct_drop:.1f}% in the second week "
                f"(${rev_comp['period2']['revenue']:,.2f}) compared to the first week "
                f"(${rev_comp['period1']['revenue']:,.2f}), representing a drop of "
                f"${abs(rev_comp['absolute_change']):,.2f}."
            ),
            "metric_impact": {
                "week1_revenue": rev_comp["period1"]["revenue"],
                "week2_revenue": rev_comp["period2"]["revenue"],
                "absolute_change": rev_comp["absolute_change"],
                "percentage_change": rev_comp["percentage_change"],
            },
            "supporting_evidence": correlate_events_with_metric(
                df_events, start_date=period2_range[0], end_date=period2_range[1]
            ),
            "recommended_actions": [
                "Investigate root cause behind Week 2 conversion drops.",
                "Review checkout funnel metrics by device category.",
                "Verify payment gateway error rates starting around Week 2 boundary.",
            ],
        })

    # ---------------------------------------------------------
    # Problem 2: Product Gross Margin Anomaly Detection
    # ---------------------------------------------------------
    profitability = calculate_product_profitability(df_sales, df_costs, low_margin_threshold_pct=15.0)
    low_margin_products = [p for p in profitability if p["is_low_margin"]]

    if low_margin_products:
        for p in low_margin_products:
            anomalies.append({
                "anomaly_id": f"ANOMALY_PROFIT_{p['product_id']}",
                "title": f"Unusually Low Gross Margin: {p['product_name']}",
                "category": "profitability",
                "severity": "warning",
                "description": (
                    f"Product '{p['product_name']}' ({p['product_id']}) has an unusually low "
                    f"gross profit margin of {p['gross_profit_margin_pct']:.1f}%. Unit cost (${p['unit_cost']:.2f}) "
                    f"is nearly equal to unit selling price (${p['total_revenue'] / p['units_sold']:.2f} avg), "
                    f"yielding only ${p['gross_profit']:,.2f} total gross profit across {p['units_sold']} units sold."
                ),
                "metric_impact": {
                    "product_id": p["product_id"],
                    "product_name": p["product_name"],
                    "gross_profit_margin_pct": p["gross_profit_margin_pct"],
                    "total_revenue": p["total_revenue"],
                    "total_cost": p["total_cost"],
                    "gross_profit": p["gross_profit"],
                },
                "supporting_evidence": [
                    {
                        "source": "costs.csv",
                        "unit_cost": p["unit_cost"],
                        "threshold_pct": 15.0,
                        "benchmark_avg_other_products_margin_pct": round(
                            float(pd.Series([
                                prod["gross_profit_margin_pct"]
                                for prod in profitability
                                if not prod["is_low_margin"]
                            ]).mean()), 1
                        )
                    }
                ],
                "recommended_actions": [
                    "Renegotiate wholesale procurement pricing with component supplier.",
                    "Review pricing strategy and consider adjusting retail price upwards.",
                    "Bundle product with higher-margin accessories to protect basket margin.",
                ],
            })

    # ---------------------------------------------------------
    # Problem 3: Mobile Payment Deterioration & Event Correlation
    # ---------------------------------------------------------
    device_comp = compare_device_funnels(df_funnel, period1_range, period2_range)
    if device_comp["mobile"]["deterioration_detected"]:
        m_p1_comp = device_comp["mobile"]["period1"]["payment_completion_pct"]
        m_p2_comp = device_comp["mobile"]["period2"]["payment_completion_pct"]
        rel_drop = abs(device_comp["mobile"]["payment_completion_relative_change_pct"])

        # Correlate events related to checkout, frontend, or payment
        relevant_events = correlate_events_with_metric(
            df_events, start_date=period2_range[0], end_date=period2_range[1]
        )

        anomalies.append({
            "anomaly_id": "ANOMALY_FUNNEL_MOBILE_001",
            "title": "Severe Mobile Payment Completion Deterioration After Website Update",
            "category": "funnel",
            "severity": "critical",
            "description": (
                f"Mobile payment completion plummeted from {m_p1_comp:.1f}% in Week 1 "
                f"down to {m_p2_comp:.1f}% in Week 2 (a relative decline of {rel_drop:.1f}%). "
                f"Desktop payment completion remained steady ({device_comp['desktop']['period1']['payment_completion_pct']:.1f}% "
                f"vs {device_comp['desktop']['period2']['payment_completion_pct']:.1f}%), pinpointing the issue "
                f"specifically to the mobile checkout flow."
            ),
            "metric_impact": {
                "mobile_week1_payment_completion_pct": m_p1_comp,
                "mobile_week2_payment_completion_pct": m_p2_comp,
                "relative_drop_pct": rel_drop,
                "desktop_week1_payment_completion_pct": device_comp["desktop"]["period1"]["payment_completion_pct"],
                "desktop_week2_payment_completion_pct": device_comp["desktop"]["period2"]["payment_completion_pct"],
            },
            "supporting_evidence": relevant_events,
            "recommended_actions": [
                "Roll back or hotfix the frontend v2.4.0 mobile payment sheet component.",
                "Review payment gateway HTTP 504 timeout logs on mobile user agents.",
                "Test credit card input auto-focus and payment submission handler across iOS Safari & Android Chrome.",
            ],
        })

    return anomalies
