# BizPulse — Logging, Monitoring & Alerting Guide

> **Document Version**: 1.0.0  
> **Status**: Operational Runbook  
> **Target Audience**: Site Reliability Engineers (SRE), DevOps & System Administrators

---

## 1. Structured Logging Configuration

Application logging is initialized during backend startup in `app.main` using `app.observability.configure_logging()`.

### 1.1 Environment Configuration

| Variable | Default | Purpose |
|---|---|---|
| `LOG_LEVEL` | `INFO` | Application log verbosity (`DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`). |
| `TRUST_PROXY_HEADERS` | `false` | Enables reverse-proxy IP extraction from `X-Forwarded-For`. |
| `TRUSTED_PROXIES` | `127.0.0.1,::1` | Whitelisted upstream load balancers / proxies. |

---

## 2. Monitoring & Diagnostic Endpoints

### 2.1 Public Endpoint (`GET /api/health`)
Used by container orchestrators (Kubernetes liveness/readiness probes, Docker healthchecks, AWS Route53):

```powershell
curl -i http://localhost:8000/api/health
```

Expected output:
```json
{
  "status": "healthy",
  "service": "BizPulse API",
  "version": "0.5.0",
  "timestamp": "2026-11-20T18:30:00.000000Z",
  "uptime_seconds": 1250.42
}
```

### 2.2 Deep Diagnostic Check (`GET /api/admin/diagnostics`)
Used by administrators to inspect subsystem dependencies:

```powershell
curl -H "Authorization: Bearer <CEO_ADMIN_TOKEN>" http://localhost:8000/api/admin/diagnostics
```

Expected output:
```json
{
  "status": "healthy",
  "uptime_seconds": 1250.42,
  "subsystems": {
    "database": {
      "status": "healthy",
      "available": true,
      "table_count": 9
    },
    "datasets": {
      "status": "healthy",
      "available": true,
      "datasets_found": 4,
      "datasets_total": 4
    },
    "ai_gemini": {
      "status": "healthy",
      "available": true,
      "configured": true,
      "model": "gemini-3.1-flash-lite",
      "latency_ms": 342.1
    }
  }
}
```

---

## 3. Prometheus Scrape Configuration

To configure a Prometheus agent to scrape BizPulse operational metrics:

```yaml
scrape_configs:
  - job_name: "bizpulse-api"
    scrape_interval: 15s
    metrics_path: "/api/admin/metrics"
    bearer_token: "<CEO_ADMIN_TOKEN>"
    static_configs:
      - targets: ["localhost:8000"]
```

### 3.1 Recommended Alerting Rules

```yaml
groups:
  - name: bizpulse_alerts
    rules:
      - alert: BizPulseApiHighErrorRate
        expr: rate(bizpulse_http_requests_total{status_class="5xx"}[5m]) > 0.05
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "BizPulse API 5xx error rate exceeds 5%"

      - alert: BizPulseDatabaseUnavailable
        expr: bizpulse_db_operations_total{status="failure"} > 5
        for: 1m
        labels:
          severity: page
        annotations:
          summary: "Database operations failing in BizPulse"

      - alert: BizPulseRateLimitSpike
        expr: rate(bizpulse_rate_limit_rejections_total[5m]) > 10
        for: 2m
        labels:
          severity: warning
        annotations:
          summary: "High rate of 429 rate-limit rejections detected"
```

---

## 4. Correlation & Error Investigation Runbook

When an end-user or operational alert reports an error:

1. **Extract Correlation ID**: Retrieve the `correlation_id` from the HTTP response or header (`X-Correlation-ID: corr-XXXXXXXXXXXX`).
2. **Filter Log Aggregator**: Search centralized logs (CloudWatch, Datadog, ELK, Loki) for `correlation_id="corr-XXXXXXXXXXXX"`.
3. **Trace Lifecycle**:
   - Locate the initial access log line (`method`, `endpoint`, `client_ip`).
   - Identify any subsequent `ERROR` or `WARNING` log lines carrying the exact same `correlation_id`.
   - Inspect the server-side exception stack trace.
