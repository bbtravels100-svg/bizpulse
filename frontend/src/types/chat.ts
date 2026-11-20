// Chat + action types — verified against backend/app/chat/models.py
// and backend/app/actions/models.py.

export interface InvestigationBrief {
  orchestration_id: string;
  anomaly_id: string;
  executive_summary: string;
  problem_statement: string;
  confirmed_evidence: string[];
  likely_causes: string[];
  target_team_and_priority: string;
  recommended_action_plan: string[];
  verification_and_success_criteria: string[];
}

export interface ChatApiResponse {
  intent: 'investigation' | 'analytics' | 'general';
  reply: string;
  confirmed_facts: string[];
  possible_explanations: string[];
  follow_up_questions: string[];
  investigation: InvestigationBrief | null;
  anomaly_id: string | null;
  can_propose_actions: boolean;
  data_sources_used: string[];
  model_used: string;
  generated_at: string;
}

export interface ChatTurnPayload {
  role: 'user' | 'assistant';
  content: string;
}

/** Mirrors backend ActionResponse (Phase 3B). */
export interface ActionItem {
  id: string;
  investigation_id: string;
  anomaly_id: string;
  problem_description: string;
  recommended_action: string;
  responsible_department: string;
  suggested_owner_role: string;
  priority: 'Critical' | 'High' | 'Medium' | 'Low';
  suggested_deadline: string;
  expected_outcome: string;
  verification_criteria: string;
  status: string;
  rejection_reason: string | null;
  created_at: string;
  updated_at: string;
}

export type DecisionState = 'idle' | 'working' | 'approved' | 'rejected' | 'error';

export interface ActionDecision {
  state: DecisionState;
  message?: string;
}

export interface ActionPanelState {
  status: 'loading' | 'ready' | 'error';
  items: ActionItem[];
  error?: string;
  decisions: Record<string, ActionDecision>;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'error';
  content: string;
  timestamp: string;
  /** Present on assistant messages. */
  response?: ChatApiResponse;
  /** Present on error messages: the user text that can be retried. */
  retryText?: string;
  /** Action proposals prepared from this message (after explicit user request). */
  actions?: ActionPanelState;
}
