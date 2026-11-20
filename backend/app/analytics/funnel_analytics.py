from datetime import date
from typing import Dict, Optional, Tuple, Any
import pandas as pd
from .sales_analytics import filter_by_date_range

def calculate_funnel_conversion(
    df_funnel: pd.DataFrame,
    start_date: Optional[date | str] = None,
    end_date: Optional[date | str] = None,
    device: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Calculate conversion rates through the e-commerce funnel:
    Visitors -> Reached Cart -> Reached Payment -> Purchased.
    """
    df = filter_by_date_range(df_funnel, start_date, end_date)
    if device is not None:
        df = df[df["device"] == device.lower()]

    if df.empty:
        return {
            "visitors": 0,
            "reached_cart": 0,
            "reached_payment": 0,
            "purchased": 0,
            "cart_conversion_pct": 0.0,
            "payment_step_pct": 0.0,
            "payment_completion_pct": 0.0,
            "overall_conversion_pct": 0.0,
        }

    visitors = int(df["visitors"].sum())
    reached_cart = int(df["reached_cart"].sum())
    reached_payment = int(df["reached_payment"].sum())
    purchased = int(df["purchased"].sum())

    # Division by zero guards
    cart_rate = round((reached_cart / visitors * 100), 2) if visitors > 0 else 0.0
    payment_step_rate = round((reached_payment / reached_cart * 100), 2) if reached_cart > 0 else 0.0
    payment_completion_rate = (
        round((purchased / reached_payment * 100), 2) if reached_payment > 0 else 0.0
    )
    overall_conversion = round((purchased / visitors * 100), 2) if visitors > 0 else 0.0

    return {
        "visitors": visitors,
        "reached_cart": reached_cart,
        "reached_payment": reached_payment,
        "purchased": purchased,
        "cart_conversion_pct": cart_rate,
        "payment_step_pct": payment_step_rate,
        "payment_completion_pct": payment_completion_rate,
        "overall_conversion_pct": overall_conversion,
    }

def compare_device_funnels(
    df_funnel: pd.DataFrame,
    period1_range: Tuple[date | str, date | str],
    period2_range: Tuple[date | str, date | str],
) -> Dict[str, Any]:
    """
    Compare conversion metrics between Desktop and Mobile across two periods.
    Detects whether mobile payment completion deteriorated significantly.
    """
    p1_start, p1_end = period1_range
    p2_start, p2_end = period2_range

    desktop_p1 = calculate_funnel_conversion(df_funnel, p1_start, p1_end, device="desktop")
    desktop_p2 = calculate_funnel_conversion(df_funnel, p2_start, p2_end, device="desktop")
    mobile_p1 = calculate_funnel_conversion(df_funnel, p1_start, p1_end, device="mobile")
    mobile_p2 = calculate_funnel_conversion(df_funnel, p2_start, p2_end, device="mobile")

    # Payment completion relative drops: (P2 - P1) / P1 * 100
    def calc_relative_change(p1_val: float, p2_val: float) -> float:
        if p1_val > 0:
            return round(((p2_val - p1_val) / p1_val) * 100, 2)
        return 0.0

    desktop_payment_change = calc_relative_change(
        desktop_p1["payment_completion_pct"], desktop_p2["payment_completion_pct"]
    )
    mobile_payment_change = calc_relative_change(
        mobile_p1["payment_completion_pct"], mobile_p2["payment_completion_pct"]
    )

    # Flag deterioration if mobile payment dropped by > 30% relative
    mobile_deteriorated = mobile_payment_change < -30.0

    return {
        "period1_dates": {"start": str(p1_start), "end": str(p1_end)},
        "period2_dates": {"start": str(p2_start), "end": str(p2_end)},
        "desktop": {
            "period1": desktop_p1,
            "period2": desktop_p2,
            "payment_completion_relative_change_pct": desktop_payment_change,
        },
        "mobile": {
            "period1": mobile_p1,
            "period2": mobile_p2,
            "payment_completion_relative_change_pct": mobile_payment_change,
            "deterioration_detected": mobile_deteriorated,
        },
    }
