from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel

from ..auth.permissions import require_roles, ROLE_ADMIN
from .diagnostics import run_operational_diagnostics
from .metrics import metrics_collector, APP_START_TIME
import time

observability_router = APIRouter(tags=["Observability & Telemetry"])


class PublicHealthResponse(BaseModel):
    status: str
    service: str
    version: str
    timestamp: str
    uptime_seconds: float


@observability_router.get(
    "/api/health",
    response_model=PublicHealthResponse,
    summary="Public application health check",
)
def public_health_check():
    """
    Minimal public health check.
    Returns basic service availability without exposing internal database paths,
    environment variables, or infrastructure secrets.
    """
    now = datetime.now(timezone.utc).isoformat()
    uptime = round(time.time() - APP_START_TIME, 2)
    return PublicHealthResponse(
        status="healthy",
        service="BizPulse API",
        version="0.5.0",
        timestamp=now,
        uptime_seconds=uptime,
    )


@observability_router.get(
    "/api/admin/diagnostics",
    summary="Protected operational subsystem diagnostics (CEO / Admin Only)",
    dependencies=[Depends(require_roles([ROLE_ADMIN]))],
)
def get_admin_diagnostics():
    """
    Deep operational diagnostics assessing database connectivity, dataset storage,
    and Gemini reachability with caching and bounded timeouts.
    """
    return run_operational_diagnostics()


@observability_router.get(
    "/api/admin/metrics",
    summary="Prometheus-compatible operational telemetry metrics (CEO / Admin Only)",
    dependencies=[Depends(require_roles([ROLE_ADMIN]))],
)
def get_admin_metrics():
    """
    Prometheus exposition metrics for request rates, latencies, rate limits,
    AI operations, and active business task counts.
    """
    text_data = metrics_collector.generate_prometheus_text()
    return Response(
        content=text_data,
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )
