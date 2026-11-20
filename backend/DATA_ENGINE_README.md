# BizPulse Business Data Engine & Analytics Documentation 📈

The **Business Data Engine** is Phase 2 of BizPulse. It provides robust ingestion, validation, and analytics over realistic e-commerce business data covering a 14-day observation window (`2026-11-01` to `2026-11-14`).

---

## 📊 Datasets Overview

The raw datasets are stored in `backend/data/`:

| Dataset | File | Records | Key Columns | Purpose |
| :--- | :--- | :--- | :--- | :--- |
| **Sales** | [`sales.csv`](file:///D:/Bizpulse/backend/data/sales.csv) | 70 rows (14 days × 5 products) | `date, product_id, product_name, units_sold, revenue` | Tracks daily unit sales and revenue per product |
| **Costs** | [`costs.csv`](file:///D:/Bizpulse/backend/data/costs.csv) | 5 rows | `product_id, product_name, unit_cost` | Tracks product cost of goods sold (COGS) |
| **Website Funnel** | [`website_funnel.csv`](file:///D:/Bizpulse/backend/data/website_funnel.csv) | 28 rows (14 days × 2 devices) | `date, device, visitors, reached_cart, reached_payment, purchased` | Tracks visitor drop-off across desktop and mobile devices |
| **Events** | [`events.csv`](file:///D:/Bizpulse/backend/data/events.csv) | 7 rows | `timestamp, event_type, description, affected_system` | Timeline of deploys, errors, support alerts & marketing |

---

## 🎯 The Three Planted Business Problems

BizPulse is designed to discover three deliberate problems planted in this data:

### 1. Revenue Decline of ~18% in Week 2
- **Week 1 (`2026-11-01` to `2026-11-07`) Revenue:** `$85,000.00`
- **Week 2 (`2026-11-08` to `2026-11-14`) Revenue:** `$69,700.00`
- **Absolute Change:** `-$15,300.00`
- **Percentage Change:** Exactly **`-18.00%`**
- **Calculated Metric:**
  $$\text{Percentage Change} = \frac{\text{Revenue}_{W2} - \text{Revenue}_{W1}}{\text{Revenue}_{W1}} \times 100 = \frac{69,700 - 85,000}{85,000} \times 100 = -18.00\%$$

---

### 2. Unusually Low Gross Profit Margin Product
- **Problem Product:** `PROD_005` ("Heavy Duty Gaming Monitor Stand")
- **Unit Selling Price:** `$45.00`
- **Unit COGS (Cost):** `$43.20`
- **Gross Profit Per Unit:** `$1.80`
- **Gross Profit Margin:** **`4.00%`**
- **Comparison to Benchmark:**
  - `PROD_001` (Ergonomic Desk Chair): **`50.0%`** margin ($175.00 profit / $350.00 price)
  - `PROD_002` (Headphones): **`50.0%`** margin ($90.00 profit / $180.00 price)
  - `PROD_003` (Fitness Watch): **`40.0%`** margin ($48.00 profit / $120.00 price)
  - `PROD_004` (Mechanical Keyboard): **`45.0%`** margin ($42.75 profit / $95.00 price)
  - **Healthy Products Average Margin:** **`46.25%`**
  - `PROD_005` with a 4.0% margin is flagged as a critical margin outlier!

---

### 3. Mobile Payment Deterioration Following Website Deployment
- **Root-Cause Event (`events.csv`):**
  - **Timestamp:** `2026-11-08T02:15:00Z`
  - **Type:** `website_update`
  - **Description:** *"Deployed checkout frontend v2.4.0 with revised mobile payment sheet integration"*
  - **Followed by Error Alerts:**
    - `2026-11-08T06:45:00Z`: Spike in client-side Javascript exceptions and mobile gateway timeouts (HTTP 504)
    - `2026-11-09T10:30:00Z`: Support received 90+ tickets reporting frozen payment on mobile
- **Funnel Metric Impact (`website_funnel.csv`):**
  - **Desktop (Control Group):**
    - Week 1 Payment Completion: `75.0%`
    - Week 2 Payment Completion: `75.0%` (Relative change: `0.0%`, completely stable)
  - **Mobile (Affected Group):**
    - Week 1 Payment Completion: **`75.0%`**
    - Week 2 Payment Completion: **`22.0%`**
    - **Relative Deterioration:** **`-70.7%` collapse in mobile payment completion!**
  - **Mathematical Consistency:** `visitors >= reached_cart >= reached_payment >= purchased >= 0` holds true on 100% of rows.

---

## 🧮 Analytics Functions & Formulas

Located in `backend/app/analytics/`:

| Function | Module | Description & Formula |
| :--- | :--- | :--- |
| `get_total_revenue` | `sales_analytics.py` | Computes $\sum \text{revenue}$ over an optional date window |
| `compare_revenue_periods` | `sales_analytics.py` | Computes $\text{Rev}_{P2} - \text{Rev}_{P1}$ and $\% \Delta$ |
| `get_units_sold_by_product`| `sales_analytics.py` | Aggregates units and revenue grouped by product |
| `get_daily_sales_trend` | `sales_analytics.py` | Groups sales day-by-day for time-series charts |
| `calculate_product_profitability` | `profit_analytics.py` | Gross profit: $\text{Rev} - (\text{Units} \times \text{Unit Cost})$; Margin: $\frac{\text{Gross Profit}}{\text{Rev}} \times 100$ |
| `detect_low_margin_products` | `profit_analytics.py` | Filters products below margin threshold (default 15%) |
| `calculate_funnel_conversion` | `funnel_analytics.py` | Computes step-by-step conversion rates and overall visitor-to-purchase % |
| `compare_device_funnels` | `funnel_analytics.py` | Compares Desktop vs Mobile across periods and detects deterioration |
| `detect_all_anomalies` | `anomaly_engine.py` | Cross-correlates metrics, detects the 3 anomalies, and attaches event evidence |

---

## 🌐 API Endpoints

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/health` | Health-check returning service status |
| `GET` | `/api/overview` | Executive summary: total revenue, WoW change, units, anomaly count |
| `GET` | `/api/sales` | Detailed sales metrics, period comparison, and daily trends |
| `GET` | `/api/products/profitability` | Profitability and margin breakdown with low-margin flags |
| `GET` | `/api/funnel` | Full funnel conversion by device (Desktop vs. Mobile) |
| `GET` | `/api/anomalies` | Detected business anomalies with root-cause event evidence |
| `GET` | `/api/events` | Complete operational timeline of deployments and alerts |
| `POST` | `/api/gemini/test` | Verifies live Gemini API connectivity and latency |
| `POST` | `/api/investigate` | Multi-problem AI investigation: synthesizes verified Python metrics with Gemini causal analysis (`ANOMALY_REV_001`, `ANOMALY_PROFIT_PROD_005`, `ANOMALY_FUNNEL_MOBILE_001`) |
| `POST` | `/api/agents/run` | Multi-Agent Orchestration: 4 coordinated roles (Analyst → Connector → Router → Writer) producing an executive business action brief |
| `POST` | `/api/actions/propose` | Create an action proposal in 'Pending Approval' |
| `GET` | `/api/actions/proposals` | List all proposals awaiting manager approval |
| `POST` | `/api/actions/{action_id}/approve` | Approve a proposal and transition into active workflow |
| `POST` | `/api/actions/{action_id}/reject` | Reject a proposal with mandatory reason |
| `GET` | `/api/tasks` | List active tasks with filtering |
| `POST` | `/api/verification/baseline` | Capture or view immutable baseline metrics for an action |
| `POST` | `/api/verification/verify` | Trigger deterministic Python verification run with Gemini causal follow-up |
| `GET` | `/api/verification/results/{action_id}` | Latest verification outcome and comparison details |
| `GET` | `/api/verification/history/{action_id}` | Chronological history of all verification runs and notes |
| `POST` | `/api/verification/notes` | Attach diagnostic or operational notes to verification attempts |
| `POST` | `/api/verification/reopen` | Reopen investigation when verification fails & generate secondary proposal |

---

## 🤖 Multi-Agent Orchestration Architecture (Phase 3A)

BizPulse features a 4-role sequential agent pipeline powered by Google Gemini:

```
[Business Data Engine]
        │
        ▼ (Deterministic Facts & Events)
┌────────────────────────────────────────────────────────┐
│  AGENT 1: ANALYST                                      │
│  Validates critical metrics, trends, and patterns      │
│  without hallucinating or inventing numbers.           │
└───────────────────────┬────────────────────────────────┘
                        │
                        ▼ (Analytical Summary & Patterns)
┌────────────────────────────────────────────────────────┐
│  AGENT 2: CONNECTOR                                    │
│  Discovers cross-departmental dependencies across      │
│  tech, sales, support, and finance.                    │
└───────────────────────┬────────────────────────────────┘
                        │
                        ▼ (Cross-Department Connections)
┌────────────────────────────────────────────────────────┐
│  AGENT 3: ROUTER                                       │
│  Identifies responsible department, recommended team,  │
│  remediation priority, and suggested next action.      │
└───────────────────────┬────────────────────────────────┘
                        │
                        ▼ (Routing Decision & Next Action)
┌────────────────────────────────────────────────────────┐
│  AGENT 4: WRITER                                       │
│  Synthesizes an executive-ready business action brief  │
│  with concrete remediation & verification criteria.    │
└────────────────────────────────────────────────────────┘
```

---

## 📋 Action Management & Task Workflow (Phase 3B)

BizPulse transforms AI recommendations into structured, persistent, and auditable business tasks stored in SQLite (`backend/data/bizpulse.db`):

### Database Schema:
- **`actions`**: Core records tracking `id`, `investigation_id`, `anomaly_id`, `problem_description`, `recommended_action`, `responsible_department`, `suggested_owner_role`, `priority`, `suggested_deadline`, `expected_outcome`, `verification_criteria`, `status`, `rejection_reason`, `completion_details`, `completed_at`, `created_at`, `updated_at`.
- **`action_notes`**: Threaded management notes and technical observations.
- **`action_audit_log`**: Immutable audit trail logging state transitions, edits, reassignments, and author timestamps.

### Task Lifecycle & Status Transitions:
```
[AI Multi-Agent Pipeline]
         │
         ▼
[Pending Approval] ────────(Reject with reason)────────► [Rejected] (Terminal)
         │
    (Approve)
         ▼
    [Approved] ────────────(Deadline passed)───────────► [Overdue]
         │                                                   │
   (Start Work)                                          (Resume)
         ▼                                                   │
   [In Progress] ◄───────────────────────────────────────────┘
         │
    (Complete with verification details)
         ▼
    [Completed] (Terminal)
```

---

## 🔍 Follow-Up and Verification Engine (Phase 3C)

BizPulse rigorously evaluates whether completed actions genuinely resolved underlying business problems.

### Core Principle: Task Completion != Problem Resolution
Marking an engineering or operational task as "Completed" does NOT mean the business problem is solved. BizPulse enforces strict quantitative verification using deterministic Python calculations combined with qualitative Gemini follow-up interpretation.

```
[Manager Approves Action]
          │
          ▼ (Automatic & Immutable)
┌────────────────────────────────────────┐
│  Baseline Capture (metric_baselines)   │
│  Stores: Action ID, Anomaly ID, Metric,│
│  Baseline Value, Period, Target Value. │
└──────────────────┬─────────────────────┘
                   │
                   ▼ (Action Implemented & Deployed)
┌────────────────────────────────────────┐
│  Deterministic Python Engine           │
│  Computes: Absolute Move, Relative %,  │
│  Target Met (True/False), & Outcome:   │
│  • Improved                            │
│  • Not Improved                        │
│  • Deteriorated                        │
│  • Inconclusive                        │
│  • Insufficient Data                   │
└──────────────────┬─────────────────────┘
                   │
                   ▼ (Pre-Calculated Numbers)
┌────────────────────────────────────────┐
│  Gemini Follow-Up Interpretation       │
│  Explains factual movement, evaluates  │
│  plausible causes, recommends next     │
│  steps, and assigns causal confidence  │
│  (High | Medium | Low | Unsubstantiated)│
└──────────────────┬─────────────────────┘
                   │
        ┌──────────┴──────────┐
        ▼                     ▼
[Target Met: Resolved]   [Target Unmet / Deteriorated]
• Action archived        • Flagged as Needs Reopening
• Resolution confirmed   • Secondary Diagnostic Proposal
                         • Critical Reopened Workflow
```

### Verification Database Schema:
- **`metric_baselines`**: Immutable store of baseline metric values captured upon action approval. Original baselines are never overwritten.
- **`verification_runs`**: Records of all verification attempts across stages (`initial`, `follow_up`, `final`, `manual`), storing Python calculations, outcome classifications, target fulfillment, resolution flags, and Gemini follow-up evaluations.
- **`verification_notes`**: Threaded diagnostic notes and manager commentary attached to verification attempts.

---

## 🧪 Automated Testing

Run the test suite using pytest from `backend/`:

```bash
cd D:\Bizpulse\backend
.\.venv\Scripts\Activate.ps1
pytest -v
```

All 88 test cases pass:
- **`test_verification.py`** (12 tests): Verifies all 5 outcome classifications (`Improved`, `Not Improved`, `Deteriorated`, `Inconclusive`, `Insufficient Data`), direction handling (increase vs decrease), immutable baseline capture on approval, simulated scenario runs, multi-stage evaluations (`initial`, `follow_up`, `final`), diagnostic note threading, failed verification reopening workflow, and full REST API endpoint integration.
- **`test_actions.py`** (18 tests): Tests proposal creation, manager approval/rejection gates, editing proposals, valid/invalid transitions, task completion details, persistence after restart, deadline updates, progress notes, and audit trails.
- **`test_agents.py`** (13 tests): Verifies all 4 agent roles independently, full orchestration pipeline, stage failure handling, evidence preservation, and `POST /api/agents/run` endpoint.
- **`test_data_loader.py`** (4 tests): Validates CSV schemas, types, non-negativity, and funnel hierarchy constraints.
- **`test_analytics.py`** (8 tests): Verifies exact `-18.00%` revenue decline, 4.0% low-margin stand detection, mobile payment drop, and event correlation.
- **`test_api.py`** (8 tests): Verifies all FastAPI endpoints respond with HTTP 200 and valid JSON data.
- **`test_gemini_service.py`** (10 tests): Verifies API key redaction, client configuration, prompt dispatch, error handling, and connectivity endpoint.
- **`test_investigation.py`** (15 tests): Verifies deterministic Python fact extraction, prompt generation, mocked multi-problem investigation runs, API routing, friendly aliases, and error handling for all 3 problems.
