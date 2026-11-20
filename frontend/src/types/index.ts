// ============================================================
// BizPulse Frontend — TypeScript Type Definitions
// Mirrors all backend Pydantic models (do not add client-only
// fields here — keep 1:1 with the API schemas).
// ============================================================

// ─── Health ──────────────────────────────────────────────────
export interface HealthResponse {
  status: string;
  service: string;
  version: string;
}

// ─── Investigation & Actions (Real Backend Schemas) ───────────
export type InvestigationType =
  | 'mobile_payment_deterioration'
  | 'revenue_decline'
  | 'low_product_profitability';

export * from './investigation';

// ─── Multi-Agent Orchestration ────────────────────────────────
export interface AgentRunRequest {
  investigation_type: InvestigationType;
  additional_context?: string;
}

export interface AgentOutput {
  agent_name: string;
  role: string;
  output: string;
  timestamp: string;
}

export interface AgentRunResponse {
  run_id: string;
  investigation_type: string;
  timestamp: string;
  analyst_output: AgentOutput;
  connector_output: AgentOutput;
  router_output: AgentOutput;
  writer_output: AgentOutput;
  final_report: string;
  model_used: string;
}

// ─── Actions & Tasks (Real Backend Schemas) ───────────────────
export * from './action';

// ─── Verification (Real Backend Schemas) ──────────────────────
export * from './verification';

// ─── UI-only types ────────────────────────────────────────────
export type View =
  | 'home'
  | 'assistant'
  | 'investigations'
  | 'actions'
  | 'verification'
  | 'datasources'
  | 'settings';

export type BackendStatus = 'connected' | 'disconnected' | 'checking';


export type BadgeVariant = 'success' | 'warning' | 'danger' | 'info' | 'neutral';
export type ButtonVariant = 'primary' | 'secondary' | 'danger' | 'ghost';
export type ButtonSize = 'sm' | 'md' | 'lg';

// Analytics response types (verified against backend)
export * from './analytics';
export * from './chat';
export * from './dataSources';
export * from './settings';


