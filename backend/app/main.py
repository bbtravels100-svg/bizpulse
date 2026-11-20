import os
from contextlib import asynccontextmanager
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query, Depends
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from pydantic import BaseModel

from .analytics import (
    load_sales_data,
    load_costs_data,
    load_funnel_data,
    load_events_data,
    get_total_revenue,
    compare_revenue_periods,
    get_units_sold_by_product,
    get_daily_sales_trend,
    calculate_product_profitability,
    detect_low_margin_products,
    calculate_funnel_conversion,
    compare_device_funnels,
    detect_all_anomalies,
)
from .services.gemini_service import (
    GeminiServiceError,
    GeminiAuthError,
    GeminiRateLimitError,
    verify_gemini_connectivity,
)
from .services.investigation_service import (
    InvestigationResponse,
    run_investigation,
    run_mobile_payment_investigation,
    run_revenue_decline_investigation,
    run_low_profitability_investigation,
)
from .agents import (
    AgentRunRequest,
    OrchestrationResponse,
    run_agent_pipeline,
)
from .actions import (
    actions_router,
    init_db,
)
from .auth.permissions import (
    Permission,
    require_permissions,
)
from .auth import (
    auth_router,
    init_auth_db,
    validate_security_configuration,
    rate_limit,
    record_security_event,
    SecurityEventType,
    CSRFProtectionMiddleware,
)
from .verification import (
    verification_router,
)
from .db import (
    run_migrations,
)
from .db.router import (
    db_admin_router,
)
from .observability import (
    ObservabilityMiddleware,
    observability_router,
    register_error_handlers,
    configure_logging,
)

# Load environment variables from .env
load_dotenv()

# Configure structured JSON application logging
configure_logging(level_name=os.getenv("LOG_LEVEL", "INFO"))

# Initialize SQLite database schema and run migrations
run_migrations()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Validate security settings and perform startup integrity checks."""
    run_migrations()
    validate_security_configuration()
    yield


app = FastAPI(
    title="BizPulse API",
    description="Backend service for BizPulse - AI-powered business intelligence & execution platform",
    version="0.5.0",
    lifespan=lifespan,
)

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Enforce foundational HTTP security headers on all responses."""
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response


# Register safe correlation-aware error handlers
register_error_handlers(app)

# Configure CORS Origins
allowed_origins_raw = os.getenv(
    "ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
)
allowed_origins = [
    origin.strip()
    for origin in allowed_origins_raw.split(",")
    if origin.strip() and origin.strip() != "*"
]

# Explicit allowed HTTP methods & headers for browser clients
ALLOWED_METHODS = ["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"]
ALLOWED_HEADERS = ["Content-Type", "Authorization", "X-Correlation-ID", "X-CSRF-Token", "Accept"]

# Mount Middlewares (executed in reverse order of addition)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(ObservabilityMiddleware)
app.add_middleware(CSRFProtectionMiddleware, allowed_origins=allowed_origins)
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=ALLOWED_METHODS,
    allow_headers=ALLOWED_HEADERS,
    expose_headers=["X-Correlation-ID"],
)

# Mount Observability, Health & Telemetry Router (Phase 6 Step 5)
app.include_router(observability_router)


# Mount Authentication Router (Phase 6 Step 1)
app.include_router(auth_router)
# Mount Action Management & Task Router
app.include_router(actions_router)
# Mount conversational AI assistant router (Phase 4B Step 3)
from .chat import chat_router  # noqa: E402
app.include_router(chat_router)
# Mount Follow-up & Verification Engine Router (Phase 3C)
app.include_router(verification_router)
# Mount Data Sources & Datasets Router (Phase 4B Step 7)
from .analytics.datasets_router import datasets_router  # noqa: E402
app.include_router(datasets_router)
# Mount Database Administration Router (Phase 6 Step 4)
app.include_router(db_admin_router)


@app.get("/")
def read_root():
    """Root endpoint welcoming API consumers."""
    return {
        "message": "Welcome to BizPulse API",
        "docs_url": "/docs",
        "health_check": "/api/health",
        "endpoints": {
            "auth_login": "/api/auth/login",
            "auth_logout": "/api/auth/logout",
            "auth_me": "/api/auth/me",
            "auth_provision": "/api/auth/provision",
            "overview": "/api/overview",
            "sales": "/api/sales",
            "profitability": "/api/products/profitability",
            "funnel": "/api/funnel",
            "anomalies": "/api/anomalies",
            "events": "/api/events",
            "gemini_test": "/api/gemini/test",
            "investigate": "/api/investigate",
            "agents_run": "/api/agents/run",
            "actions_proposals": "/api/actions/proposals",
            "actions_generate": "/api/actions/generate",
            "tasks": "/api/tasks",
            "verification_baseline": "/api/verification/baseline",
            "verification_verify": "/api/verification/verify",
            "verification_results": "/api/verification/results/{action_id}",
            "verification_history": "/api/verification/history/{action_id}",
            "verification_notes": "/api/verification/notes",
            "verification_reopen": "/api/verification/reopen",
            "admin_diagnostics": "/api/admin/diagnostics",
            "admin_metrics": "/api/admin/metrics",
        },
    }


@app.get(
    "/api/overview",
    dependencies=[Depends(require_permissions([Permission.ANALYTICS_READ]))],
)
def get_business_overview(
    p1_start: str = Query("2026-11-01", description="Period 1 start date"),
    p1_end: str = Query("2026-11-07", description="Period 1 end date"),
    p2_start: str = Query("2026-11-08", description="Period 2 start date"),
    p2_end: str = Query("2026-11-14", description="Period 2 end date"),
):
    """
    Retrieve top-level business overview metrics:
    total revenue, period comparisons, total units sold, conversion rate, and anomaly summary.
    """
    try:
        df_sales = load_sales_data()
        df_costs = load_costs_data()
        df_funnel = load_funnel_data()
        df_events = load_events_data()

        total_rev = get_total_revenue(df_sales)
        rev_comparison = compare_revenue_periods(
            df_sales, (p1_start, p1_end), (p2_start, p2_end)
        )
        total_units = int(df_sales["units_sold"].sum())
        funnel_summary = calculate_funnel_conversion(df_funnel)
        anomalies = detect_all_anomalies(
            df_sales, df_costs, df_funnel, df_events, (p1_start, p1_end), (p2_start, p2_end)
        )

        return {
            "total_revenue": total_rev,
            "total_units_sold": total_units,
            "week_over_week": rev_comparison,
            "overall_funnel": funnel_summary,
            "anomalies_detected_count": len(anomalies),
            "critical_anomalies_count": sum(1 for a in anomalies if a.get("severity") == "critical"),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate overview metrics: {str(e)}")


@app.get(
    "/api/sales",
    dependencies=[Depends(require_permissions([Permission.ANALYTICS_READ]))],
)
def get_sales_analysis(
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    p1_start: str = Query("2026-11-01", description="Period 1 start date"),
    p1_end: str = Query("2026-11-07", description="Period 1 end date"),
    p2_start: str = Query("2026-11-08", description="Period 2 start date"),
    p2_end: str = Query("2026-11-14", description="Period 2 end date"),
):
    """
    Retrieve sales analysis, revenue comparisons, product sales, and daily trends.
    """
    try:
        df_sales = load_sales_data()
        total_rev = get_total_revenue(df_sales, start_date, end_date)
        period_comp = compare_revenue_periods(
            df_sales, (p1_start, p1_end), (p2_start, p2_end)
        )
        product_sales = get_units_sold_by_product(df_sales, start_date, end_date)
        daily_trend = get_daily_sales_trend(df_sales)

        return {
            "total_revenue": total_rev,
            "period_comparison": period_comp,
            "products": product_sales,
            "daily_trend": daily_trend,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate sales analysis: {str(e)}")


@app.get(
    "/api/products/profitability",
    dependencies=[Depends(require_permissions([Permission.PROFITABILITY_READ]))],
)
def get_product_profitability(
    low_margin_threshold: float = Query(15.0, description="Gross margin threshold percentage to flag low-margin items"),
):
    """
    Retrieve product profitability, gross profits, and gross profit margins.
    Flags low-margin items.
    """
    try:
        df_sales = load_sales_data()
        df_costs = load_costs_data()

        profitability = calculate_product_profitability(
            df_sales, df_costs, low_margin_threshold_pct=low_margin_threshold
        )
        low_margin_items = [p for p in profitability if p["is_low_margin"]]

        return {
            "threshold_used_pct": low_margin_threshold,
            "total_products": len(profitability),
            "low_margin_products_count": len(low_margin_items),
            "products": profitability,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to calculate product profitability: {str(e)}")


@app.get(
    "/api/funnel",
    dependencies=[Depends(require_permissions([Permission.ANALYTICS_READ]))],
)
def get_funnel_analysis(
    p1_start: str = Query("2026-11-01", description="Period 1 start date"),
    p1_end: str = Query("2026-11-07", description="Period 1 end date"),
    p2_start: str = Query("2026-11-08", description="Period 2 start date"),
    p2_end: str = Query("2026-11-14", description="Period 2 end date"),
):
    """
    Retrieve website funnel conversion analysis and device breakdown (desktop vs mobile).
    """
    try:
        df_funnel = load_funnel_data()
        overall_conversion = calculate_funnel_conversion(df_funnel)
        device_comparison = compare_device_funnels(
            df_funnel, (p1_start, p1_end), (p2_start, p2_end)
        )

        return {
            "overall_funnel": overall_conversion,
            "device_comparison": device_comparison,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to analyze website funnel: {str(e)}")


@app.get(
    "/api/anomalies",
    dependencies=[Depends(require_permissions([Permission.ANALYTICS_READ]))],
)
def get_detected_anomalies(
    p1_start: str = Query("2026-11-01", description="Period 1 start date"),
    p1_end: str = Query("2026-11-07", description="Period 1 end date"),
    p2_start: str = Query("2026-11-08", description="Period 2 start date"),
    p2_end: str = Query("2026-11-14", description="Period 2 end date"),
):
    """
    Retrieve all detected business anomalies, root-cause correlations, and supporting event evidence.
    """
    try:
        df_sales = load_sales_data()
        df_costs = load_costs_data()
        df_funnel = load_funnel_data()
        df_events = load_events_data()

        anomalies = detect_all_anomalies(
            df_sales, df_costs, df_funnel, df_events, (p1_start, p1_end), (p2_start, p2_end)
        )
        return {
            "count": len(anomalies),
            "anomalies": anomalies,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to detect anomalies: {str(e)}")


@app.get(
    "/api/events",
    dependencies=[Depends(require_permissions([Permission.ANALYTICS_READ]))],
)
def get_events():
    """
    Retrieve system and business event timeline.
    """
    try:
        df_events = load_events_data()
        events_list = []
        for _, row in df_events.sort_values("timestamp").iterrows():
            events_list.append({
                "timestamp": row["timestamp"].isoformat(),
                "event_type": str(row["event_type"]),
                "description": str(row["description"]),
                "affected_system": str(row["affected_system"]),
            })
        return {
            "count": len(events_list),
            "events": events_list,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve events: {str(e)}")


class GeminiTestRequest(BaseModel):
    prompt: Optional[str] = "You are connected to BizPulse. Reply with: Gemini connection successful."


class GeminiTestResponse(BaseModel):
    connection_status: str
    model_name: str
    response: str
    response_time_ms: float


@app.post(
    "/api/gemini/test",
    response_model=GeminiTestResponse,
    dependencies=[
        Depends(require_permissions([Permission.ADMIN_DIAGNOSTICS])),
        Depends(rate_limit(limit_default="10/minute", env_var_name="RATE_LIMIT_GEMINI_TEST", key_prefix="gemini_test")),
    ],
)
def gemini_connectivity_test(payload: Optional[GeminiTestRequest] = None):
    """
    Test connectivity to Google Gemini API.
    Sends a test prompt and returns the real model response and latency.
    """
    if payload and payload.prompt and len(payload.prompt) > 1000:
        record_security_event(
            event_type=SecurityEventType.AI_PAYLOAD_LIMIT_EXCEEDED,
            detail=f"Gemini test prompt exceeds 1000 characters ({len(payload.prompt)})",
        )
        raise HTTPException(
            status_code=400,
            detail="Prompt exceeds maximum allowed length of 1000 characters",
        )
    prompt = (
        payload.prompt
        if payload and payload.prompt
        else "You are connected to BizPulse. Reply with: Gemini connection successful."
    )
    try:
        result = verify_gemini_connectivity(prompt=prompt)
        return GeminiTestResponse(**result)
    except GeminiAuthError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except GeminiRateLimitError as e:
        raise HTTPException(status_code=429, detail=str(e))
    except GeminiServiceError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


class InvestigationRequest(BaseModel):
    anomaly_id: Optional[str] = "ANOMALY_FUNNEL_MOBILE_001"


@app.post(
    "/api/investigate",
    response_model=InvestigationResponse,
    dependencies=[
        Depends(require_permissions([Permission.AI_INVESTIGATE])),
        Depends(rate_limit(limit_default="10/minute", env_var_name="RATE_LIMIT_INVESTIGATE", key_prefix="investigate")),
    ],
)
def investigate_anomaly_endpoint(payload: Optional[InvestigationRequest] = None):
    """
    Investigate an active business anomaly.
    Supports all three planted business anomalies:
      - ANOMALY_REV_001: Week 1 vs Week 2 Revenue Decline (-18.00%)
      - ANOMALY_PROFIT_PROD_005: Low Product Profitability (4.00% gross margin)
      - ANOMALY_FUNNEL_MOBILE_001: Mobile Checkout Payment Deterioration
    Combines verified quantitative evidence from the Python Business Data Engine
    with structured causal reasoning and recommendations from Google Gemini.
    """
    if payload and payload.anomaly_id and len(payload.anomaly_id) > 64:
        record_security_event(
            event_type=SecurityEventType.AI_PAYLOAD_LIMIT_EXCEEDED,
            detail=f"Investigation anomaly_id exceeds 64 chars ({len(payload.anomaly_id)})",
        )
        raise HTTPException(
            status_code=400,
            detail="Anomaly ID exceeds maximum allowed length of 64 characters",
        )
    try:
        anomaly_id = (
            payload.anomaly_id
            if payload and payload.anomaly_id
            else "ANOMALY_FUNNEL_MOBILE_001"
        )
        result = run_investigation(anomaly_id=anomaly_id)
        return result
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except GeminiAuthError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except GeminiRateLimitError as e:
        raise HTTPException(status_code=429, detail=str(e))
    except GeminiServiceError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Investigation failed: {str(e)}")


@app.post(
    "/api/agents/run",
    response_model=OrchestrationResponse,
    dependencies=[
        Depends(require_permissions([Permission.AI_INVESTIGATE])),
        Depends(rate_limit(limit_default="10/minute", env_var_name="RATE_LIMIT_AGENTS", key_prefix="agents_run")),
    ],
)
def run_agents_endpoint(payload: Optional[AgentRunRequest] = None):
    """
    Multi-Agent Orchestration Endpoint (Phase 3A).
    Coordinates four specialized AI roles in sequence:
      1. Analyst: Validates critical numerical metrics & identifies patterns.
      2. Connector: Uncovers cross-departmental dependencies across systems.
      3. Router: Identifies responsible department, recommended team, priority, and next action.
      4. Writer: Synthesizes an executive-ready business action brief.
    Preserves evidence references across all stages and validates all outputs with Pydantic.
    """
    if payload and payload.anomaly_id and len(payload.anomaly_id) > 64:
        record_security_event(
            event_type=SecurityEventType.AI_PAYLOAD_LIMIT_EXCEEDED,
            detail=f"Agent orchestration anomaly_id exceeds 64 chars ({len(payload.anomaly_id)})",
        )
        raise HTTPException(
            status_code=400,
            detail="Anomaly ID exceeds maximum allowed length of 64 characters",
        )
    try:
        anomaly_id = (
            payload.anomaly_id
            if payload and payload.anomaly_id
            else "ANOMALY_FUNNEL_MOBILE_001"
        )
        result = run_agent_pipeline(anomaly_id=anomaly_id)
        return result
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except GeminiAuthError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except GeminiRateLimitError as e:
        raise HTTPException(status_code=429, detail=str(e))
    except GeminiServiceError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent orchestration failed: {str(e)}")



