import pytest
from app.analytics.data_loader import (
    load_sales_data,
    load_costs_data,
    load_funnel_data,
    load_events_data,
)
from app.analytics.sales_analytics import (
    get_total_revenue,
    compare_revenue_periods,
    get_units_sold_by_product,
    get_daily_sales_trend,
)
from app.analytics.profit_analytics import (
    calculate_product_profitability,
    detect_low_margin_products,
)
from app.analytics.funnel_analytics import (
    calculate_funnel_conversion,
    compare_device_funnels,
)
from app.analytics.anomaly_engine import (
    detect_all_anomalies,
    correlate_events_with_metric,
)

@pytest.fixture
def sales_df():
    return load_sales_data()

@pytest.fixture
def costs_df():
    return load_costs_data()

@pytest.fixture
def funnel_df():
    return load_funnel_data()

@pytest.fixture
def events_df():
    return load_events_data()

def test_total_revenue(sales_df):
    total = get_total_revenue(sales_df)
    # Week 1 ($85,000) + Week 2 ($69,700) = $154,700
    assert total == 154700.00

def test_revenue_decline_approximately_18_percent(sales_df):
    """
    Verification of Problem 1:
    Revenue declines approximately 18% in the second week compared with the first week.
    """
    comparison = compare_revenue_periods(
        sales_df, ("2026-11-01", "2026-11-07"), ("2026-11-08", "2026-11-14")
    )
    assert comparison["period1"]["revenue"] == 85000.00
    assert comparison["period2"]["revenue"] == 69700.00
    assert comparison["absolute_change"] == -15300.00
    # Exact percentage change: -18.0%
    assert comparison["percentage_change"] == -18.0
    assert comparison["trend"] == "declined"

def test_units_sold_by_product(sales_df):
    units = get_units_sold_by_product(sales_df)
    assert len(units) == 5
    product_ids = {u["product_id"] for u in units}
    assert product_ids == {"PROD_001", "PROD_002", "PROD_003", "PROD_004", "PROD_005"}
    for item in units:
        assert item["units_sold"] > 0
        assert item["total_revenue"] > 0

def test_daily_sales_trend(sales_df):
    trend = get_daily_sales_trend(sales_df)
    assert len(trend) == 14
    for day in trend:
        assert day["revenue"] > 0
        assert day["units_sold"] > 0

def test_product_profitability_and_low_margin_detection(sales_df, costs_df):
    """
    Verification of Problem 2:
    At least one product has an unusually low gross profit margin.
    """
    profitability = calculate_product_profitability(sales_df, costs_df, low_margin_threshold_pct=15.0)
    assert len(profitability) == 5

    # Check for low margin detection
    low_margin_items = detect_low_margin_products(sales_df, costs_df, threshold_pct=15.0)
    assert len(low_margin_items) >= 1

    # Specifically PROD_005 (Gaming Monitor Stand) should be flagged with ~4% margin
    stand = next(p for p in profitability if p["product_id"] == "PROD_005")
    assert stand["is_low_margin"] is True
    assert stand["gross_profit_margin_pct"] == 4.0
    assert stand["unit_cost"] == 43.20

    # Other products should have healthy margins (40% - 50%)
    for p in profitability:
        if p["product_id"] != "PROD_005":
            assert p["gross_profit_margin_pct"] >= 40.0
            assert p["is_low_margin"] is False

def test_funnel_conversion_rates(funnel_df):
    conversion = calculate_funnel_conversion(funnel_df)
    assert conversion["visitors"] > 0
    assert conversion["purchased"] > 0
    assert 0.0 < conversion["overall_conversion_pct"] < 100.0
    assert 0.0 < conversion["payment_completion_pct"] < 100.0

def test_mobile_payment_deterioration(funnel_df):
    """
    Verification of Problem 3:
    Mobile payment completion deteriorates sharply in Week 2, while desktop remains stable.
    """
    comp = compare_device_funnels(
        funnel_df, ("2026-11-01", "2026-11-07"), ("2026-11-08", "2026-11-14")
    )
    # Desktop payment completion should be steady
    assert abs(comp["desktop"]["payment_completion_relative_change_pct"]) < 5.0

    # Mobile payment completion should deteriorate sharply
    assert comp["mobile"]["deterioration_detected"] is True
    assert comp["mobile"]["payment_completion_relative_change_pct"] < -50.0

    m_w1_comp = comp["mobile"]["period1"]["payment_completion_pct"]
    m_w2_comp = comp["mobile"]["period2"]["payment_completion_pct"]
    assert m_w1_comp > 70.0
    assert m_w2_comp < 30.0

def test_anomaly_engine_and_event_correlation(sales_df, costs_df, funnel_df, events_df):
    """
    Verification of Master Anomaly Engine:
    Detects revenue decline, low margin product, mobile payment breakdown,
    and correlates events from events.csv.
    """
    anomalies = detect_all_anomalies(sales_df, costs_df, funnel_df, events_df)
    assert len(anomalies) >= 3

    categories = {a["category"] for a in anomalies}
    assert "revenue" in categories
    assert "profitability" in categories
    assert "funnel" in categories

    # Verify event evidence attached to mobile funnel anomaly
    funnel_anomaly = next(a for a in anomalies if a["category"] == "funnel")
    evidence_descriptions = [e["description"] for e in funnel_anomaly["supporting_evidence"]]
    
    # Contextual evidence must include website update
    has_website_update = any("checkout frontend v2.4.0" in desc.lower() for desc in evidence_descriptions)
    assert has_website_update, "Website deployment event must be included in supporting evidence"
