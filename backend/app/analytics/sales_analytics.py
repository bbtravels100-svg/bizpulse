from datetime import date
from typing import Dict, List, Optional, Tuple, Any
import pandas as pd

def filter_by_date_range(
    df: pd.DataFrame, start_date: Optional[date | str] = None, end_date: Optional[date | str] = None
) -> pd.DataFrame:
    """Filter DataFrame on a 'date' column with date objects or strings."""
    if df.empty or ("date" not in df.columns):
        return df

    filtered = df.copy()
    if start_date is not None:
        s_date = pd.to_datetime(start_date).date()
        filtered = filtered[filtered["date"] >= s_date]
    if end_date is not None:
        e_date = pd.to_datetime(end_date).date()
        filtered = filtered[filtered["date"] <= e_date]

    return filtered

def get_total_revenue(
    df_sales: pd.DataFrame,
    start_date: Optional[date | str] = None,
    end_date: Optional[date | str] = None,
) -> float:
    """Calculate total revenue over an optional date range."""
    df = filter_by_date_range(df_sales, start_date, end_date)
    if df.empty:
        return 0.0
    return round(float(df["revenue"].sum()), 2)

def compare_revenue_periods(
    df_sales: pd.DataFrame,
    period1_range: Tuple[date | str, date | str],
    period2_range: Tuple[date | str, date | str],
) -> Dict[str, Any]:
    """
    Compare total revenue between two consecutive or custom periods.
    Returns structured metrics including absolute and percentage change.
    """
    p1_start, p1_end = period1_range
    p2_start, p2_end = period2_range

    rev1 = get_total_revenue(df_sales, p1_start, p1_end)
    rev2 = get_total_revenue(df_sales, p2_start, p2_end)

    abs_change = round(rev2 - rev1, 2)
    
    # Guard against division by zero
    if rev1 > 0:
        pct_change = round((abs_change / rev1) * 100, 2)
    else:
        pct_change = 0.0 if abs_change == 0 else 100.0

    if abs_change < -0.01:
        trend = "declined"
    elif abs_change > 0.01:
        trend = "increased"
    else:
        trend = "flat"

    return {
        "period1": {
            "start_date": str(p1_start),
            "end_date": str(p1_end),
            "revenue": rev1,
        },
        "period2": {
            "start_date": str(p2_start),
            "end_date": str(p2_end),
            "revenue": rev2,
        },
        "absolute_change": abs_change,
        "percentage_change": pct_change,
        "trend": trend,
    }

def get_units_sold_by_product(
    df_sales: pd.DataFrame,
    start_date: Optional[date | str] = None,
    end_date: Optional[date | str] = None,
) -> List[Dict[str, Any]]:
    """Group sales by product and return total units sold and revenue."""
    df = filter_by_date_range(df_sales, start_date, end_date)
    if df.empty:
        return []

    grouped = (
        df.groupby(["product_id", "product_name"], as_index=False)
        .agg(units_sold=("units_sold", "sum"), total_revenue=("revenue", "sum"))
        .sort_values(by="total_revenue", ascending=False)
    )

    results = []
    for _, row in grouped.iterrows():
        results.append({
            "product_id": str(row["product_id"]),
            "product_name": str(row["product_name"]),
            "units_sold": int(row["units_sold"]),
            "total_revenue": round(float(row["total_revenue"]), 2),
        })
    return results

def get_daily_sales_trend(df_sales: pd.DataFrame) -> List[Dict[str, Any]]:
    """Aggregate revenue and units sold by date."""
    if df_sales.empty:
        return []

    daily = (
        df_sales.groupby("date", as_index=False)
        .agg(revenue=("revenue", "sum"), units_sold=("units_sold", "sum"))
        .sort_values("date")
    )

    results = []
    for _, row in daily.iterrows():
        results.append({
            "date": str(row["date"]),
            "revenue": round(float(row["revenue"]), 2),
            "units_sold": int(row["units_sold"]),
        })
    return results
