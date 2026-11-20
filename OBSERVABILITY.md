# BizPulse — Production Observability & Telemetry Architecture

> **Document Version**: 1.0.0  
> **Status**: Active Operational Reference  
> **Telemetry Protocol**: Standard Prometheus Text Format (`text/plain; version=0.0.4; charset=utf-8`)  
> **Logging Protocol**: Single-line Structured JSON with Redaction

---

## 1. Observability Architecture Overview

BizPulse implements end-to-end production observability designed to provide deep runtime transparency into API operations, background tasks, and AI integrations without exposing credentials, secrets, or sensitive customer details.

```
                  ┌────────────────────────────────────────┐
                  │          Incoming HTTP Request         │
                  └───────────────────┬────────────────────┘
                                      │
               [1. Observability & Correlation Middleware]
               - Extracts or generates validated X-Correlation-ID
               - Binds contextvars correlation ID
               - Records start timestamp (perf_counter)
                                      │
               [2. Application & API Execution]
               - Authentication & RBAC verification
               - Request handling & Business Logic
               - Metrics recorded in-memory (requests, latencies)
                                      │
               [3. Safe Response & Error Formatting]
               - Injects X-Correlation-ID in response headers
               - Standard error envelope: {"detail": "...", "correlation_id": "..."}
               - Server-side exception stack trace logging only
                                      │
               [4. Structured JSON Logging Stream]
               - ISO 8601 UTC timestamp, level, module, message
               - HTTP method, route, status code, duration_ms
               - Automatic credential / JWT / API key redaction
```

---

## 2. Request Correlation (`X-Correlation-ID`)

Every incoming and outgoing HTTP request is tagged with a unique correlation identifier.

### 2.1 Format & Validation
- **Generated Format**: `corr-<16-hex-chars>` (e.g. `corr-7a4f91b2c83e105d`).
- **Header Key**: `X-Correlation-ID`.
- **Validation**: Incoming client headers are strictly validated against `^[a-zA-Z0-9_\-]{8,64}$`. Malformed or oversized headers are rejected and replaced with a newly generated identifier.

### 2.2 Response Ingestion
All API responses include the correlation ID in the response headers:
```http
HTTP/1.1 200 OK
Content-Type: application/json
X-Correlation-ID: corr-7a4f91b2c83e105d
```

In the event of an HTTP error (4xx/5xx), the correlation ID is also present in the JSON body:
```json
{
  "detail": "Action proposal not found",
  "correlation_id": "corr-7a4f91b2c83e105d"
}
```

---

## 3. Structured JSON Logging

Application logs are formatted as single-line JSON records using `JsonLogFormatter`:

```json
{
  "timestamp": "2026-11-20T18:25:00.123456+00:00",
  "level": "INFO",
  "logger": "bizpulse.http",
  "message": "POST /api/actions/proposals -> 200 (45.2ms)",
  "correlation_id": "corr-7a4f91b2c83e105d",
  "method": "POST",
  "endpoint": "/api/actions/proposals",
  "status_code": 200,
  "duration_ms": 45.2,
  "client_ip": "192.168.1.50"
}
```

### 3.1 Automatic Data Redaction
Before any message is serialized, regex scrubbers automatically sanitize:
- Passwords (`password=[REDACTED]`)
- Bearer tokens (`Bearer [REDACTED]`)
- API keys and provisioning keys (`api_key=[REDACTED]`, `provisioning_key=[REDACTED]`)
- JWT strings (`[REDACTED_JWT]`)
- Cookie session values (`access_token=[REDACTED]`)

---

## 4. Operational Health Monitoring

Health monitoring is partitioned into two distinct visibility levels:

### 4.1 Public Health Check
- **Endpoint**: `GET /api/health`
- **Access**: Unauthenticated (Public)
- **Response**:
  ```json
  {
    "status": "healthy",
    "service": "BizPulse API",
    "version": "0.5.0",
    "timestamp": "2026-11-20T18:25:00.000000Z",
    "uptime_seconds": 3600.5
  }
  ```
- **Privacy**: Does not reveal database paths, internal filesystem structures, or subsystem dependencies.

### 4.2 Protected Operational Diagnostics
- **Endpoint**: `GET /api/admin/diagnostics`
- **Access**: Restricted to `CEO / Admin` role
- **Features**:
  - **Database Health**: Connectivity and `PRAGMA quick_check;` structure validation.
  - **Datasets Storage**: Checks local filesystem availability for CSV datasets.
  - **Gemini Reachability**: Cached 60-second probe testing external API availability with bounded timeouts. Non-configured keys in development are reported safely as `not_configured` without degrading the overall system.
  - **Subsystem Breakdown**: Evaluates individual subsystem health (`healthy`, `degraded`, `unavailable`).

---

## 5. Prometheus Operational Metrics

Prometheus-compatible metrics are exposed for ingestion by Prometheus, Grafana, OpenTelemetry collectors, or Datadog.

- **Endpoint**: `GET /api/admin/metrics`
- **Access**: Restricted to `CEO / Admin` role
- **Content-Type**: `text/plain; version=0.0.4; charset=utf-8`

### 5.1 Metrics Catalog

| Metric Name | Type | Labels | Description |
|---|:---:|---|---|
| `bizpulse_http_requests_total` | Counter | `method`, `route`, `status_class` | Total HTTP requests handled |
| `bizpulse_http_request_duration_seconds` | Summary | `route` | Latency count and sum in seconds |
| `bizpulse_app_uptime_seconds` | Gauge | None | Application uptime in seconds |
| `bizpulse_rate_limit_rejections_total` | Counter | None | Total rate limit rejections (429s) |
| `bizpulse_ai_requests_total` | Counter | `service`, `status` | Invocations of Gemini, Chat, or Agent workflows |
| `bizpulse_db_operations_total` | Counter | `operation`, `status` | Relational database operations |
| `bizpulse_active_tasks_count` | Gauge | `status` | Real-time counts of business tasks in SQLite |

### 5.2 Cardinality Protection
Dynamic identifiers (such as `/api/actions/tasks/act-12345/status`) are automatically normalized to `/api/actions/tasks/{id}/status` before recording to prevent Prometheus label cardinality explosion.
