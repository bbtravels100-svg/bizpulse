"""BizPulse Analytics Package"""
from .data_loader import (
    load_sales_data,
    load_costs_data,
    load_funnel_data,
    load_events_data,
    get_all_datasets,
)
from .sales_analytics import (
    get_total_revenue,
    compare_revenue_periods,
    get_units_sold_by_product,
    get_daily_sales_trend,
)
from .profit_analytics import (
    calculate_product_profitability,
    detect_low_margin_products,
)
from .funnel_analytics import (
    calculate_funnel_conversion,
    compare_device_funnels,
)
from .anomaly_engine import (
    detect_all_anomalies,
    correlate_events_with_metric,
)
from .dataset_tracker import (
    DatasetTracker,
    DatasetVersionInfo,
    default_dataset_tracker,
)

__all__ = [
    "load_sales_data",
    "load_costs_data",
    "load_funnel_data",
    "load_events_data",
    "get_all_datasets",
    "get_total_revenue",
    "compare_revenue_periods",
    "get_units_sold_by_product",
    "get_daily_sales_trend",
    "calculate_product_profitability",
    "detect_low_margin_products",
    "calculate_funnel_conversion",
    "compare_device_funnels",
    "detect_all_anomalies",
    "correlate_events_with_metric",
    "DatasetTracker",
    "DatasetVersionInfo",
    "default_dataset_tracker",
    "datasets_router",
]

from .datasets_router import datasets_router  # noqa: E402

