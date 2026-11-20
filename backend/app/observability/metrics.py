import time
import re
import threading
from typing import Dict, Tuple, Optional, Any

logger = logging = __import__("logging").getLogger("bizpulse.observability.metrics")

# Application startup timestamp for uptime calculation
APP_START_TIME = time.time()


def normalize_metric_route(path: str) -> str:
    """
    Normalize route paths to prevent metric label cardinality explosion.
    Replaces UUIDs, action IDs, task IDs, and hashes with generic {id} parameter.
    """
    if not path:
        return "/"
    p = path.split("?")[0]  # Strip query string
    p = re.sub(r"/usr-[a-f0-9\-]+", "/{id}", p)
    p = re.sub(r"/act-[a-f0-9\-]+", "/{id}", p)
    p = re.sub(r"/corr-[a-f0-9\-]+", "/{id}", p)
    p = re.sub(r"/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", "/{id}", p)
    return p


class MetricsCollector:
    """
    Thread-safe in-memory metrics collector producing Prometheus-compatible text format.
    Low overhead, zero external dependencies, low cardinality.
    """

    def __init__(self):
        self._lock = threading.Lock()
        # Key: (method, route, status_class) -> int
        self._http_requests: Dict[Tuple[str, str, str], int] = {}
        # Key: route -> [count, sum_seconds]
        self._http_duration: Dict[str, Tuple[int, float]] = {}
        # Counter: rate limit rejections
        self._rate_limit_rejections: int = 0
        # Key: (service, status) -> int
        self._ai_requests: Dict[Tuple[str, str], int] = {}
        # Key: (operation, status) -> int
        self._db_operations: Dict[Tuple[str, str], int] = {}

    def record_http_request(self, method: str, path: str, status_code: int, duration_sec: float) -> None:
        """Record an HTTP request execution and its latency."""
        norm_route = normalize_metric_route(path)
        status_class = f"{status_code // 100}xx"

        with self._lock:
            key = (method.upper(), norm_route, status_class)
            self._http_requests[key] = self._http_requests.get(key, 0) + 1

            count, total_time = self._http_duration.get(norm_route, (0, 0.0))
            self._http_duration[norm_route] = (count + 1, total_time + duration_sec)

    def record_rate_limit_rejection(self) -> None:
        """Increment rate limit rejection count."""
        with self._lock:
            self._rate_limit_rejections += 1

    def record_ai_request(self, service: str, success: bool) -> None:
        """Record an AI invocation (e.g. gemini, chat, agents)."""
        status = "success" if success else "failure"
        with self._lock:
            key = (service, status)
            self._ai_requests[key] = self._ai_requests.get(key, 0) + 1

    def record_db_operation(self, operation: str, success: bool) -> None:
        """Record a database operation."""
        status = "success" if success else "failure"
        with self._lock:
            key = (operation, status)
            self._db_operations[key] = self._db_operations.get(key, 0) + 1

    def get_active_task_counts(self) -> Dict[str, int]:
        """Query real task counts grouped by status from SQLite."""
        try:
            from ..db.connection import get_db_connection
            conn = get_db_connection()
            try:
                cursor = conn.execute("SELECT status, COUNT(*) FROM actions GROUP BY status;")
                return {row[0].lower(): row[1] for row in cursor.fetchall()}
            finally:
                conn.close()
        except Exception as e:
            logger.debug(f"Could not retrieve task counts for metrics: {e}")
            return {}

    def generate_prometheus_text(self) -> str:
        """Format collected metrics into standard Prometheus exposition format."""
        lines = []

        # 1. Total HTTP Requests
        lines.append("# HELP bizpulse_http_requests_total Total number of HTTP requests processed")
        lines.append("# TYPE bizpulse_http_requests_total counter")
        with self._lock:
            for (method, route, status_class), count in sorted(self._http_requests.items()):
                lines.append(
                    f'bizpulse_http_requests_total{{method="{method}",route="{route}",status_class="{status_class}"}} {count}'
                )

        # 2. HTTP Request Duration Summary
        lines.append("\n# HELP bizpulse_http_request_duration_seconds Latency of HTTP requests in seconds")
        lines.append("# TYPE bizpulse_http_request_duration_seconds summary")
        with self._lock:
            for route, (count, total_time) in sorted(self._http_duration.items()):
                lines.append(f'bizpulse_http_request_duration_seconds_count{{route="{route}"}} {count}')
                lines.append(f'bizpulse_http_request_duration_seconds_sum{{route="{route}"}} {round(total_time, 4)}')

        # 3. Application Uptime
        uptime = round(time.time() - APP_START_TIME, 2)
        lines.append("\n# HELP bizpulse_app_uptime_seconds Total application uptime in seconds")
        lines.append("# TYPE bizpulse_app_uptime_seconds gauge")
        lines.append(f"bizpulse_app_uptime_seconds {uptime}")

        # 4. Rate Limit Rejections
        lines.append("\n# HELP bizpulse_rate_limit_rejections_total Total rate limit rejections")
        lines.append("# TYPE bizpulse_rate_limit_rejections_total counter")
        lines.append(f"bizpulse_rate_limit_rejections_total {self._rate_limit_rejections}")

        # 5. AI Requests
        lines.append("\n# HELP bizpulse_ai_requests_total Total AI service requests")
        lines.append("# TYPE bizpulse_ai_requests_total counter")
        with self._lock:
            for (service, status), count in sorted(self._ai_requests.items()):
                lines.append(f'bizpulse_ai_requests_total{{service="{service}",status="{status}"}} {count}')

        # 6. Database Operations
        lines.append("\n# HELP bizpulse_db_operations_total Total database operations")
        lines.append("# TYPE bizpulse_db_operations_total counter")
        with self._lock:
            for (op, status), count in sorted(self._db_operations.items()):
                lines.append(f'bizpulse_db_operations_total{{operation="{op}",status="{status}"}} {count}')

        # 7. Active Business Tasks Count (from real database)
        task_counts = self.get_active_task_counts()
        lines.append("\n# HELP bizpulse_active_tasks_count Total business remediation tasks by status")
        lines.append("# TYPE bizpulse_active_tasks_count gauge")
        if task_counts:
            for status, count in sorted(task_counts.items()):
                lines.append(f'bizpulse_active_tasks_count{{status="{status}"}} {count}')
        else:
            lines.append('bizpulse_active_tasks_count{status="none"} 0')

        return "\n".join(lines) + "\n"

    def reset(self) -> None:
        """Reset collector metrics (useful for testing)."""
        with self._lock:
            self._http_requests.clear()
            self._http_duration.clear()
            self._rate_limit_rejections = 0
            self._ai_requests.clear()
            self._db_operations.clear()


# Default singleton instance
metrics_collector = MetricsCollector()
