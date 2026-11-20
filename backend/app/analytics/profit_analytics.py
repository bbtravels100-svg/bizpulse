from typing import Dict, List, Optional
import pandas as pd

def calculate_product_profitability(
    df_sales: pd.DataFrame,
    df_costs: pd.DataFrame,
    low_margin_threshold_pct: float = 15.0,
) -> List[Dict[str, float | str | bool | int]]:
    """
    Calculate gross profit and gross profit margin by product.
    Formula:
      total_cost = units_sold * unit_cost
      gross_profit = total_revenue - total_cost
      gross_profit_margin_pct = (gross_profit / total_revenue) * 100
    """
    if df_sales.empty or df_costs.empty:
        return []

    sales_agg = (
        df_sales.groupby("product_id", as_index=False)
        .agg(units_sold=("units_sold", "sum"), total_revenue=("revenue", "sum"))
    )

    merged = pd.merge(sales_agg, df_costs, on="product_id", how="left")

    results = []
    for _, row in merged.iterrows():
        units = int(row["units_sold"])
        revenue = float(row["total_revenue"])
        raw_cost = row.get("unit_cost")
        unit_cost = float(raw_cost) if pd.notna(raw_cost) else 0.0

        total_cost = round(units * unit_cost, 2)
        gross_profit = round(revenue - total_cost, 2)

        # Guard division by zero
        if revenue > 0:
            margin_pct = round((gross_profit / revenue) * 100, 2)
        else:
            margin_pct = 0.0

        is_low_margin = margin_pct < low_margin_threshold_pct

        results.append({
            "product_id": str(row["product_id"]),
            "product_name": str(row["product_name"]),
            "units_sold": units,
            "unit_cost": round(unit_cost, 2),
            "total_revenue": round(revenue, 2),
            "total_cost": total_cost,
            "gross_profit": gross_profit,
            "gross_profit_margin_pct": margin_pct,
            "is_low_margin": is_low_margin,
        })

    # Sort descending by gross profit
    results.sort(key=lambda x: x["gross_profit"], reverse=True)
    return results

def detect_low_margin_products(
    df_sales: pd.DataFrame,
    df_costs: pd.DataFrame,
    threshold_pct: float = 15.0,
) -> List[Dict[str, float | str | bool | int]]:
    """Return only products with gross profit margin below the threshold."""
    profitability = calculate_product_profitability(
        df_sales, df_costs, low_margin_threshold_pct=threshold_pct
    )
    return [p for p in profitability if p["is_low_margin"]]
