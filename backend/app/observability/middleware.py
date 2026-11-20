import time
import logging
from typing import Callable
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from .correlation import (
    generate_correlation_id,
    validate_correlation_id,
    set_correlation_id,
)
from .metrics import metrics_collector
from ..auth.audit import get_client_ip

logger = logging.getLogger("bizpulse.http")


class ObservabilityMiddleware(BaseHTTPMiddleware):
    """
    HTTP request monitoring and correlation middleware.
    - Extracts or generates validated X-Correlation-ID.
    - Injects correlation ID into context and response headers.
    - Records latency and increments Prometheus request metrics.
    - Emits structured JSON access logs with client IP and duration.
    - Skips excessive polling noise for health endpoints.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # 1. Resolve and validate correlation ID
        incoming_cid = request.headers.get("x-correlation-id")
        cid = validate_correlation_id(incoming_cid) or generate_correlation_id()
        set_correlation_id(cid)

        client_ip = get_client_ip(request)
        start_time = time.perf_counter()
        status_code = 500

        try:
            response = await call_next(request)
            status_code = response.status_code
            response.headers["X-Correlation-ID"] = cid
            return response
        except Exception:
            # Let exception handlers format the response, but record status 500
            status_code = 500
            raise
        finally:
            duration_sec = time.perf_counter() - start_time
            duration_ms = round(duration_sec * 1000, 2)
            method = request.method
            path = request.url.path

            # 2. Record metrics
            try:
                metrics_collector.record_http_request(
                    method=method,
                    path=path,
                    status_code=status_code,
                    duration_sec=duration_sec,
                )
            except Exception as e:
                logger.debug(f"Metrics recording error: {e}")

            # 3. Log request completion
            try:
                # Omit noisy health check logs at INFO level unless it failed
                is_health = path in ("/api/health", "/health")
                log_level = logging.INFO
                if is_health and status_code < 400:
                    log_level = logging.DEBUG
                elif status_code >= 500:
                    log_level = logging.ERROR
                elif status_code >= 400:
                    log_level = logging.WARNING

                # Log with extra structured attributes for JsonLogFormatter
                logger.log(
                    log_level,
                    f"{method} {path} -> {status_code} ({duration_ms}ms)",
                    extra={
                        "method": method,
                        "endpoint": path,
                        "status_code": status_code,
                        "duration_ms": duration_ms,
                        "client_ip": client_ip,
                        "correlation_id": cid,
                    },
                )
            except Exception as e:
                # Logging failure must NEVER crash the request
                pass
