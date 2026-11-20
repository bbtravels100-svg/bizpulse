import os
import time
import sqlite3
import logging
from pathlib import Path
from typing import Dict, Any, Optional

from .metrics import APP_START_TIME

logger = logging.getLogger("bizpulse.observability.diagnostics")

# Cache for Gemini reachability check: (timestamp, status_dict)
_gemini_reachability_cache: Optional[tuple[float, Dict[str, Any]]] = None
_GEMINI_CACHE_TTL_SECONDS = 60.0


def check_db_health() -> Dict[str, Any]:
    """Lightweight database connectivity and integrity check."""
    try:
        from ..db.connection import get_db_connection
        conn = get_db_connection(timeout=3.0)
        try:
            cursor = conn.execute("PRAGMA quick_check;")
            check_result = cursor.fetchone()[0]
            is_ok = check_result.lower() == "ok"
            # Basic table existence
            t_cursor = conn.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table';")
            table_count = t_cursor.fetchone()[0]
            return {
                "status": "healthy" if is_ok else "corrupted",
                "available": is_ok,
                "table_count": table_count,
            }
        finally:
            conn.close()
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return {
            "status": "unavailable",
            "available": False,
            "error": "Database connectivity failed",
        }


def check_datasets_health() -> Dict[str, Any]:
    """Verify local datasets directory and essential CSV source files."""
    try:
        from ..analytics.data_loader import DEFAULT_DATA_DIR
        data_path = Path(DEFAULT_DATA_DIR)
        if not data_path.exists() or not data_path.is_dir():
            return {
                "status": "unavailable",
                "available": False,
                "error": "Data directory not accessible",
            }

        essential_files = ["sales.csv", "costs.csv", "website_funnel.csv", "events.csv"]
        found = [f for f in essential_files if (data_path / f).exists()]
        all_present = len(found) == len(essential_files)

        return {
            "status": "healthy" if all_present else "degraded",
            "available": len(found) > 0,
            "datasets_found": len(found),
            "datasets_total": len(essential_files),
        }
    except Exception as e:
        logger.error(f"Dataset storage health check failed: {e}")
        return {
            "status": "unavailable",
            "available": False,
            "error": "Dataset storage verification error",
        }


def check_gemini_health() -> Dict[str, Any]:
    """
    Check Gemini API configuration and bounded reachability.
    Caches connectivity result for 60 seconds to prevent expensive API polling.
    Never exposes API keys or raw credentials.
    """
    global _gemini_reachability_cache
    now = time.time()

    # Check cache first
    if _gemini_reachability_cache:
        cached_time, cached_res = _gemini_reachability_cache
        if (now - cached_time) < _GEMINI_CACHE_TTL_SECONDS:
            return cached_res

    api_key = os.getenv("GEMINI_API_KEY", "")
    is_configured = bool(api_key and api_key.strip() and api_key != "your_gemini_api_key_here")

    if not is_configured:
        res = {
            "status": "not_configured",
            "available": True,  # Non-fatal in dev/demo
            "configured": False,
            "model": os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite"),
        }
        _gemini_reachability_cache = (now, res)
        return res

    # Bounded connectivity probe
    try:
        from ..services.gemini_service import verify_gemini_connectivity
        # Quick ping with minimal prompt
        connectivity = verify_gemini_connectivity(prompt="Ping")
        res = {
            "status": "healthy",
            "available": True,
            "configured": True,
            "model": connectivity.get("model_name", "unknown"),
            "latency_ms": connectivity.get("response_time_ms", 0),
        }
    except Exception as e:
        logger.warning(f"Gemini API health probe failed or timed out: {e}")
        res = {
            "status": "degraded",
            "available": False,
            "configured": True,
            "error": "Gemini API reachability test failed",
        }

    _gemini_reachability_cache = (now, res)
    return res


def run_operational_diagnostics() -> Dict[str, Any]:
    """
    Execute full subsystem diagnostic check for CEO / Admin inspection.
    Returns composite status: healthy, degraded, or unavailable.
    """
    db_status = check_db_health()
    ds_status = check_datasets_health()
    ai_status = check_gemini_health()
    uptime_sec = round(time.time() - APP_START_TIME, 2)

    # Calculate overall health
    if not db_status.get("available") or not ds_status.get("available"):
        overall_status = "unavailable"
    elif db_status.get("status") != "healthy" or ds_status.get("status") != "healthy" or ai_status.get("status") == "degraded":
        overall_status = "degraded"
    else:
        overall_status = "healthy"

    return {
        "status": overall_status,
        "uptime_seconds": uptime_sec,
        "subsystems": {
            "database": db_status,
            "datasets": ds_status,
            "ai_gemini": ai_status,
        },
    }
