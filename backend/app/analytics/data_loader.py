import os
from typing import Optional, Dict
import pandas as pd

DEFAULT_DATA_DIR = os.getenv(
    "DATA_DIR",
    os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data"
    ),
)

def get_data_path(filename: str, custom_dir: Optional[str] = None) -> str:
    directory = custom_dir or DEFAULT_DATA_DIR
    return os.path.join(directory, filename)

def load_sales_data(filepath: Optional[str] = None) -> pd.DataFrame:
    """
    Load and validate sales.csv.
    Required fields: date, product_id, product_name, units_sold, revenue.
    """
    path = filepath or get_data_path("sales.csv")
    if not os.path.exists(path):
        raise FileNotFoundError(f"Sales dataset not found at: {path}")

    df = pd.read_csv(path)
    required_cols = {"date", "product_id", "product_name", "units_sold", "revenue"}
    missing = required_cols - set(df.columns)
    if missing:
        raise ValueError(f"Sales dataset missing required columns: {missing}")

    # Validate types and clean
    df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.date
    df = df.dropna(subset=["date"])
    df["product_id"] = df["product_id"].astype(str)
    df["product_name"] = df["product_name"].astype(str)
    df["units_sold"] = pd.to_numeric(df["units_sold"], errors="coerce").fillna(0).astype(int)
    df["revenue"] = pd.to_numeric(df["revenue"], errors="coerce").fillna(0.0).astype(float)

    # Sanity checks
    df["units_sold"] = df["units_sold"].clip(lower=0)
    df["revenue"] = df["revenue"].clip(lower=0.0)

    return df

def load_costs_data(filepath: Optional[str] = None) -> pd.DataFrame:
    """
    Load and validate costs.csv.
    Required fields: product_id, product_name, unit_cost.
    """
    path = filepath or get_data_path("costs.csv")
    if not os.path.exists(path):
        raise FileNotFoundError(f"Costs dataset not found at: {path}")

    df = pd.read_csv(path)
    required_cols = {"product_id", "product_name", "unit_cost"}
    missing = required_cols - set(df.columns)
    if missing:
        raise ValueError(f"Costs dataset missing required columns: {missing}")

    df["product_id"] = df["product_id"].astype(str)
    df["product_name"] = df["product_name"].astype(str)
    df["unit_cost"] = pd.to_numeric(df["unit_cost"], errors="coerce").fillna(0.0).astype(float)
    df["unit_cost"] = df["unit_cost"].clip(lower=0.0)

    return df

def load_funnel_data(filepath: Optional[str] = None) -> pd.DataFrame:
    """
    Load and validate website_funnel.csv.
    Required fields: date, device, visitors, reached_cart, reached_payment, purchased.
    """
    path = filepath or get_data_path("website_funnel.csv")
    if not os.path.exists(path):
        raise FileNotFoundError(f"Funnel dataset not found at: {path}")

    df = pd.read_csv(path)
    required_cols = {"date", "device", "visitors", "reached_cart", "reached_payment", "purchased"}
    missing = required_cols - set(df.columns)
    if missing:
        raise ValueError(f"Funnel dataset missing required columns: {missing}")

    df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.date
    df = df.dropna(subset=["date"])
    df["device"] = df["device"].astype(str).str.lower()
    
    numeric_cols = ["visitors", "reached_cart", "reached_payment", "purchased"]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int).clip(lower=0)

    return df

def load_events_data(filepath: Optional[str] = None) -> pd.DataFrame:
    """
    Load and validate events.csv.
    Required fields: timestamp, event_type, description, affected_system.
    """
    path = filepath or get_data_path("events.csv")
    if not os.path.exists(path):
        raise FileNotFoundError(f"Events dataset not found at: {path}")

    df = pd.read_csv(path)
    required_cols = {"timestamp", "event_type", "description", "affected_system"}
    missing = required_cols - set(df.columns)
    if missing:
        raise ValueError(f"Events dataset missing required columns: {missing}")

    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
    df = df.dropna(subset=["timestamp"])
    df["event_type"] = df["event_type"].astype(str)
    df["description"] = df["description"].astype(str)
    df["affected_system"] = df["affected_system"].astype(str)

    return df

def get_all_datasets(data_dir: Optional[str] = None) -> Dict[str, pd.DataFrame]:
    """Convenience helper to load all 4 validated datasets."""
    return {
        "sales": load_sales_data(get_data_path("sales.csv", data_dir)),
        "costs": load_costs_data(get_data_path("costs.csv", data_dir)),
        "funnel": load_funnel_data(get_data_path("website_funnel.csv", data_dir)),
        "events": load_events_data(get_data_path("events.csv", data_dir)),
    }
