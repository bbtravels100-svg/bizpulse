# BizPulse — REST API Reference Specification

> **Base URL**: `http://localhost:8000`  
> **API Version**: `v1` / `0.5.0`  
> **Documentation Formats**: OpenAPI 3.0, Swagger UI (`/docs`), ReDoc (`/redoc`)

---

## 1. System & Health Endpoints

### `GET /`
Returns top-level API metadata, active version, and service status.

**Response `200 OK`**:
```json
{
  "service": "BizPulse API",
  "version": "0.5.0",
  "status": "online",
  "docs": "/docs"
}
```

---

### `GET /api/health`
Health check endpoint reporting connectivity and subsystem status.

**Response `200 OK`**:
```json
{
  "status": "healthy",
  "environment": "development",
  "database": "connected",
  "gemini_api_configured": true
}
```

---

## 2. Analytics & Reporting Endpoints

### `GET /api/overview`
Retrieves executive summary metrics, week-over-week revenue trends, and active anomaly count.

**Response `200 OK`**:
```json
{
  "total_revenue": 52400.0,
  "revenue_change_pct": -18.0,
  "units_sold": 1420,
  "active_anomalies_count": 3,
  "last_updated": "2026-11-20T16:00:00Z"
}
```

---

### `GET /api/sales`
Retrieves daily revenue trends and product sales volume breakdowns.

**Response `200 OK`**:
```json
{
  "daily_trend": [
    {"date": "2026-11-01", "revenue": 3400.0, "units": 90},
    {"date": "2026-11-02", "revenue": 2800.0, "units": 75}
  ],
  "top_products": [
    {"product_id": "PROD-001", "name": "Basic Tier", "revenue": 18200.0, "units": 600}
  ]
}
```

---

### `GET /api/products/profitability`
Returns unit cost, price, revenue, gross profit, and margin percentages across products.

**Response `200 OK`**:
```json
{
  "products": [
    {
      "product_id": "PROD-003",
      "name": "Premium Subscription",
      "price": 100.0,
      "unit_cost": 65.0,
      "gross_margin_pct": 35.0,
      "status": "LOW_MARGIN_ALERT"
    }
  ]
}
```

---

### `GET /api/funnel`
Returns website conversion funnel metrics segmented by device type (Desktop vs. Mobile).

**Response `200 OK`**:
```json
{
  "desktop": {
    "visitors": 12000,
    "cart_adds": 4800,
    "checkout_starts": 2400,
    "purchases": 1680,
    "conversion_rate": 0.70
  },
  "mobile": {
    "visitors": 18000,
    "cart_adds": 7200,
    "checkout_starts": 3600,
    "purchases": 432,
    "conversion_rate": 0.12
  }
}
```

---

### `GET /api/anomalies`
Returns detected business anomalies with severity ratings and linked operational events.

**Response `200 OK`**:
```json
{
  "anomalies": [
    {
      "anomaly_id": "ANOM-001",
      "metric": "mobile_checkout_conversion",
      "title": "Mobile Checkout Conversion Collapse",
      "severity": "CRITICAL",
      "baseline_value": 0.38,
      "current_value": 0.12,
      "change_pct": -68.42,
      "detected_at": "2026-11-15T09:30:00Z",
      "evidence_event_ids": ["DEP-002"]
    }
  ]
}
```

---

### `GET /api/events`
Returns operational events (deployments, marketing campaigns, infrastructure alerts).

**Response `200 OK`**:
```json
{
  "events": [
    {
      "event_id": "DEP-002",
      "timestamp": "2026-11-14T22:15:00Z",
      "category": "DEPLOYMENT",
      "description": "Payment Gateway SDK v4.2 upgrade deployed to production.",
      "author": "devops-team"
    }
  ]
}
```

---

## 3. AI & Multi-Agent Endpoints

### `POST /api/chat`
Conversational business copilot grounded in operational data and metrics.

**Request Body**:
```json
{
  "message": "Why did mobile conversion drop so sharply last week?",
  "session_id": "session-123"
}
```

**Response `200 OK`**:
```json
{
  "response": "Mobile checkout conversion dropped by 68.4% immediately following the deployment of Payment Gateway SDK v4.2 (DEP-002) on November 14.",
  "citations": ["ANOM-001", "DEP-002"]
}
```

---

### `POST /api/investigate`
Single-anomaly automated investigation synthesizing root-cause findings.

**Request Body**:
```json
{
  "anomaly_id": "ANOM-001"
}
```

**Response `200 OK`**:
```json
{
  "anomaly_id": "ANOM-001",
  "root_cause": "Regression in mobile payment SDK v4.2 causing client-side checkout crashes.",
  "evidence": ["DEP-002", "website_funnel.csv"],
  "recommended_action": "Roll back Payment Gateway SDK v4.2 to v4.1.2 immediately."
}
```

---

### `POST /api/agents/run`
Executes full 4-agent orchestration pipeline (`Analyst` ➔ `Connector` ➔ `Router` ➔ `Writer`).

**Request Body**:
```json
{
  "anomaly_id": "ANOM-001"
}
```

**Response `200 OK`**:
```json
{
  "anomaly_id": "ANOM-001",
  "analyst_output": {"metric": "mobile_checkout", "drop": "-68.4%"},
  "connector_output": {"correlated_event": "DEP-002", "confidence": 0.95},
  "router_output": {"assigned_department": "Engineering", "owner_role": "Mobile Lead"},
  "writer_output": {
    "title": "Emergency Rollback of Mobile Payment SDK",
    "description": "Roll back SDK v4.2 to restore mobile payment processing.",
    "urgency": "HIGH"
  }
}
```

---

## 4. Action & Task Management Endpoints

### `POST /api/actions/propose`
Manually submits a new action proposal in `PENDING_APPROVAL` status.

**Request Body**:
```json
{
  "anomaly_id": "ANOM-001",
  "title": "Roll back Mobile SDK v4.2",
  "description": "Revert to v4.1.2 to fix checkout drop.",
  "department": "Engineering",
  "owner_role": "Mobile Lead",
  "priority": "HIGH"
}
```

**Response `201 Created`**:
```json
{
  "action_id": "ACT-1001",
  "status": "PENDING_APPROVAL",
  "title": "Roll back Mobile SDK v4.2",
  "created_at": "2026-11-20T16:10:00Z"
}
```

---

### `POST /api/actions/generate`
Generates proposals from orchestration with idempotency and duplicate prevention.

**Request Body**:
```json
{
  "anomaly_id": "ANOM-001"
}
```

**Response `200 OK`**:
```json
{
  "generated_count": 1,
  "proposals": [
    {
      "action_id": "ACT-1001",
      "status": "PENDING_APPROVAL",
      "fingerprint": "a3f8...",
      "title": "Roll back Mobile SDK v4.2"
    }
  ]
}
```

---

### `POST /api/actions/{action_id}/approve`
Manager approval gate. Transitions status to `APPROVED` and automatically captures immutable baseline metrics.

**Response `200 OK`**:
```json
{
  "action_id": "ACT-1001",
  "status": "APPROVED",
  "approved_at": "2026-11-20T16:15:00Z",
  "baseline_captured": true
}
```

---

### `POST /api/actions/{action_id}/reject`
Rejects a proposal with mandatory justification.

**Request Body**:
```json
{
  "reason": "Engineering confirmed issue will be hotfixed in v4.2.1 instead."
}
```

**Response `200 OK`**:
```json
{
  "action_id": "ACT-1001",
  "status": "REJECTED",
  "rejection_reason": "Engineering confirmed issue will be hotfixed in v4.2.1 instead."
}
```

---

### `PATCH /api/actions/{action_id}`
Edits proposal details before approval. Disallowed once approved or in progress.

**Request Body**:
```json
{
  "title": "Urgent Rollback of Mobile SDK v4.2",
  "priority": "CRITICAL"
}
```

**Response `200 OK` / `400 Bad Request`** (if already approved).

---

### `PATCH /api/tasks/{task_id}/status`
Transitions task execution status along the valid lifecycle:
`APPROVED` ➔ `IN_PROGRESS` ➔ `COMPLETED` / `OVERDUE`.

**Request Body**:
```json
{
  "status": "IN_PROGRESS"
}
```

---

### `POST /api/tasks/{task_id}/notes`
Appends a threaded progress note to a task.

**Request Body**:
```json
{
  "author": "Alice (Mobile Lead)",
  "note": "Rollback PR merged and deployed to staging."
}
```

---

### `GET /api/tasks/{task_id}/history`
Returns complete chronological audit history and progress notes.

---

## 5. Verification Endpoints

### `POST /api/verification/verify`
Triggers deterministic verification calculation and Gemini follow-up assessment.

> **Requirement**: Action must be in `APPROVED`, `IN_PROGRESS`, or `COMPLETED`. Rejects `PENDING_APPROVAL` or `REJECTED` with **HTTP 409 Conflict**.

**Request Body**:
```json
{
  "action_id": "ACT-1001"
}
```

**Response `200 OK`**:
```json
{
  "verification_id": "VER-501",
  "action_id": "ACT-1001",
  "baseline_value": 0.12,
  "current_value": 0.37,
  "delta": 0.25,
  "percentage_change": 208.33,
  "outcome": "IMPROVED",
  "verified_at": "2026-11-20T16:20:00Z",
  "gemini_analysis": "Mobile checkout conversion restored to normal historical baseline following rollback."
}
```

---

### `POST /api/verification/reopen`
Reopens an investigation after a failed or deteriorated verification outcome, creating a linked secondary action proposal.

**Request Body**:
```json
{
  "action_id": "ACT-1001",
  "reason": "Mobile conversion failed to recover; deeper payment gateway issue suspected."
}
```

---

## 6. Dataset Management Endpoints

### `GET /api/datasets`
Returns inventory of all managed datasets, record counts, SHA-256 hashes, and version numbers.

**Response `200 OK`**:
```json
{
  "datasets": [
    {
      "name": "sales.csv",
      "record_count": 1500,
      "columns": ["date", "product_id", "units", "revenue"],
      "version": 2,
      "sha256": "4b9e...",
      "last_updated": "2026-11-20T16:05:00Z",
      "status": "LOADED"
    }
  ]
}
```

---

### `POST /api/datasets/{dataset_name}/upload`
Uploads a replacement CSV file with schema validation, backup snapshot, and immediate cache invalidation.

**Form Data**:
- `file`: CSV file binary.

**Response `200 OK`**:
```json
{
  "dataset_name": "sales.csv",
  "status": "SUCCESS",
  "version": 3,
  "record_count": 1550,
  "sha256": "8f12...",
  "cache_cleared": true
}
```

**Error Responses**:
- `400 Bad Request`: Schema validation error (missing required columns or invalid types). Automatic rollback to `.bak` restored.
