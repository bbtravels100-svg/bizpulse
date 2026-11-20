import pytest
import pandas as pd
from app.analytics.data_loader import (
    load_sales_data,
    load_costs_data,
    load_funnel_data,
    load_events_data,
)

def test_sales_data_schema_and_validation():
    df = load_sales_data()
    assert not df.empty
    expected_cols = {"date", "product_id", "product_name", "units_sold", "revenue"}
    assert expected_cols.issubset(set(df.columns))
    assert (df["units_sold"] >= 0).all()
    assert (df["revenue"] >= 0.0).all()
    # 14 days of data, 5 products = 70 records
    assert len(df) == 70

def test_costs_data_schema_and_validation():
    df = load_costs_data()
    assert not df.empty
    expected_cols = {"product_id", "product_name", "unit_cost"}
    assert expected_cols.issubset(set(df.columns))
    assert (df["unit_cost"] >= 0.0).all()
    assert len(df) == 5

def test_funnel_data_mathematical_consistency():
    df = load_funnel_data()
    assert not df.empty
    expected_cols = {"date", "device", "visitors", "reached_cart", "reached_payment", "purchased"}
    assert expected_cols.issubset(set(df.columns))
    
    # Check mathematical hierarchy for every record
    for _, row in df.iterrows():
        assert row["visitors"] >= row["reached_cart"], f"Cart exceeds visitors on {row['date']} {row['device']}"
        assert row["reached_cart"] >= row["reached_payment"], f"Payment exceeds cart on {row['date']} {row['device']}"
        assert row["reached_payment"] >= row["purchased"], f"Purchased exceeds payment on {row['date']} {row['device']}"
        assert row["purchased"] >= 0

def test_events_data_schema_and_validation():
    df = load_events_data()
    assert not df.empty
    expected_cols = {"timestamp", "event_type", "description", "affected_system"}
    assert expected_cols.issubset(set(df.columns))
    assert len(df) >= 5
