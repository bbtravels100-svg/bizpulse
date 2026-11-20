# BizPulse ⚡

> **AI-Powered Autonomous Business Intelligence & Remediation Platform**  
> *Detect Anomalies. Investigate Root Causes. Orchestrate Action. Verify Outcomes.*

BizPulse is an end-to-end operational intelligence and automated decision platform designed for executive teams, product leaders, and operations managers. It closes the loop between **data detection** and **business remediation**:

```
[Detect] ➔ [Explain] ➔ [Recommend] ➔ [Approve] ➔ [Assign] ➔ [Follow Up] ➔ [Verify] ➔ [Close]
```

---

## 🚀 Key Features

1. **Executive Overview (Home)**: Real-time business KPIs (Revenue, Units Sold, WoW trends, Active Anomalies), sales trends, margin breakdown, and cross-channel funnel conversion.
2. **AI Assistant**: Conversational BI copilot powered by Google Gemini, grounded in internal facts, metric anomalies, and business operational history.
3. **Deep-Dive Investigations**: Automated multi-agent anomaly diagnosis (Revenue Decline, Mobile Payment Deterioration, Product Margin Compression) correlating analytics with system events.
4. **Autonomous Agent Orchestration**: Specialized 4-agent team (**Analyst** ➔ **Connector** ➔ **Router** ➔ **Writer**) that parses facts, discovers cross-department correlations, assigns ownership, and authors executive proposals.
5. **Action Centre**: Proposal approval gate (CEO/Manager review, edit, approve, reject), active task execution tracker, departmental assignments, deadline scheduling, and threaded audit logging.
6. **Verification Centre**: Automated baseline capture upon approval, deterministic post-remediation metric evaluation, Gemini-powered follow-up assessment, and one-click investigation reopening.
7. **Data Sources Centre**: Dataset catalog (`sales.csv`, `costs.csv`, `website_funnel.csv`, `events.csv`), schema inspection, live row counts, SHA-256 version tracking, and schema-validated CSV upload with automated rollback.
8. **Settings Centre**: Multi-role user context switching (CEO, Ops Manager, Marketing Lead, Finance Analyst), Gemini model configuration, and live API connectivity diagnostics.

---

## 🛠️ Technology Stack

| Layer | Technology | Purpose |
|---|---|---|
| **Frontend** | React 18, TypeScript 5, Vite, Lucide Icons | Component-driven responsive executive interface |
| **Backend** | Python 3.13, FastAPI, Uvicorn, Pydantic v2 | High-performance asynchronous REST API |
| **Analytics Engine** | Python, pandas, NumPy, SciPy | Deterministic statistical analysis, anomaly detection, metric verification |
| **AI / Multi-Agent** | Google Gemini API (`gemini-2.5-flash`), Google GenAI SDK | Multi-role autonomous agent orchestration and natural language synthesis |
| **Persistence** | SQLite (`bizpulse.db`), WAL mode | Relational storage for actions, tasks, verification records, and audit logs |
| **Data Storage** | Schema-validated CSV files (`backend/data/`) | Local data warehouse with SHA-256 hashing and `.bak` rollback |

---

## 📁 Repository Structure

```
Bizpulse/
├── README.md                  # System overview and quick-start guide
├── ARCHITECTURE.md            # Detailed system design, data flows, and state machines
├── API_REFERENCE.md           # Comprehensive REST API endpoint reference
├── TESTING.md                 # Test suite documentation, coverage, and execution instructions
├── KNOWN_LIMITATIONS.md       # Known architectural constraints and technical debt
├── DEPLOYMENT_READINESS.md    # Production readiness audit and deployment checklist
├── backend/                   # FastAPI backend application
│   ├── app/
│   │   ├── actions/           # Proposal & task state machine, SQLite repository, router
│   │   ├── agents/            # Specialized AI roles (Analyst, Connector, Router, Writer, Orchestrator)
│   │   ├── analytics/         # Data loading, anomaly detection, dataset tracker & hashing
│   │   ├── core/              # Config, settings, error definitions, Gemini client
│   │   ├── routers/           # Core API routes (overview, sales, funnel, anomalies, events, chat)
│   │   └── verification/      # Baseline capture, deterministic evaluator, follow-up engine
│   ├── data/                  # CSV datasets (sales.csv, costs.csv, website_funnel.csv, events.csv)
│   ├── tests/                 # 132 pytest unit, integration, and E2E tests
│   ├── requirements.txt       # Python dependencies
│   └── pytest.ini             # Pytest configuration
└── frontend/                  # React + TypeScript frontend
    ├── src/
    │   ├── api/               # Typed API client services
    │   ├── components/        # Reusable UI components (KPI cards, charts, badges, modals)
    │   ├── context/           # AppState and SettingsContext
    │   ├── types/             # Full TypeScript interface definitions
    │   └── views/             # 7 primary application views
    ├── package.json           # Frontend dependencies & scripts
    └── vite.config.ts         # Vite configuration
```

---

## ⚡ Getting Started

### Prerequisites

- **Python**: 3.11+ (Tested on Python 3.13)
- **Node.js**: v18+ (Tested on Node v20/v22/v26)
- **npm**: 9+
- **Google Gemini API Key**: Required for AI investigations, chat, and agent orchestration.

---

### 1. Backend Setup

1. Open a terminal and navigate to `backend`:
   ```bash
   cd D:\Bizpulse\backend
   ```

2. Create and activate a Python virtual environment:
   - **PowerShell**:
     ```powershell
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```
   - **Bash / macOS / Linux**:
     ```bash
     python -m venv .venv
     source .venv/bin/activate
     ```

3. Install required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Configure your `.env` file:
   ```bash
   cp .env.example .env
   ```
   Edit `.env` to supply your configuration:
   ```env
   HOST=127.0.0.1
   PORT=8000
   ENVIRONMENT=development
   ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
   GEMINI_API_KEY=your_gemini_api_key_here
   GEMINI_MODEL=gemini-2.5-flash
   ```

5. Start the backend server:
   ```bash
   uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
   ```

6. Verify the backend:
   - Health Check: [http://localhost:8000/api/health](http://localhost:8000/api/health)
   - Swagger Documentation: [http://localhost:8000/docs](http://localhost:8000/docs)

---

### 2. Frontend Setup

1. Open a second terminal and navigate to `frontend`:
   ```bash
   cd D:\Bizpulse\frontend
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Configure frontend environment variables:
   Ensure `.env` exists in `frontend/` with:
   ```env
   VITE_API_BASE_URL=http://localhost:8000
   ```

4. Start the frontend development server:
   ```bash
   npm run dev
   ```

5. Access BizPulse:
   - Open your browser to [http://localhost:5173](http://localhost:5173)

---

## 🧪 Testing

BizPulse maintains comprehensive test coverage across unit, integration, and full end-to-end workflows.

### Run Backend Tests (132 tests)

```bash
cd D:\Bizpulse\backend
.\.venv\Scripts\pytest.exe -v
```

### Run Frontend Typecheck & Build

```bash
cd D:\Bizpulse\frontend
npm run build
```

See [TESTING.md](TESTING.md) for full test architecture, test scenarios, and execution commands.

---

## 📖 Complete Documentation

- **[ARCHITECTURE.md](ARCHITECTURE.md)**: Deep-dive into data models, agent orchestration, state machines, and cache invalidation.
- **[API_REFERENCE.md](API_REFERENCE.md)**: Detailed schema and status code specifications for all REST endpoints.
- **[TESTING.md](TESTING.md)**: Inventory of 132 automated tests and verification suites.
- **[KNOWN_LIMITATIONS.md](KNOWN_LIMITATIONS.md)**: Explicit list of current technical constraints and architectural trade-offs.
- **[DEPLOYMENT_READINESS.md](DEPLOYMENT_READINESS.md)**: Production readiness rubric (9 categories) and production deployment guide.

---

## 🔒 Security Notice

- **Zero Secret Leakage**: The backend automatically sanitizes all exception messages and logs to redact `GEMINI_API_KEY` patterns (`AIza...`).
- **No Client Secrets**: The frontend contains no private credentials or API keys.
- **Strict State Machines**: Verification and task transitions are strictly enforced via backend business logic gates.
- *Notice*: BizPulse v0.5.0 does not currently enforce user authentication or role-based access control (RBAC) on backend endpoints. Review [DEPLOYMENT_READINESS.md](DEPLOYMENT_READINESS.md) before public cloud deployment.
