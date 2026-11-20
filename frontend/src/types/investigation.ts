// ============================================================
// BizPulse Frontend — Investigation Type Definitions
// Exactly mirrors backend/app/services/investigation_service.py
// and backend/app/actions/models.py
// ============================================================

export interface InvestigationTimelineEvent {
  timestamp: string;
  event_type: string;
  description: string;
  affected_system: string;
}

export interface InvestigationFacts {
  anomaly_id: string;
  anomaly_title: string;
  metric_facts: Record<string, any>;
  timeline_events: InvestigationTimelineEvent[];
}

export interface InvestigationHypothesis {
  cause: string;
  supporting_evidence: string[];
  confidence_level: 'high' | 'medium' | 'low' | string;
}

export interface InvestigationAnalysis {
  what_happened: string;
  why_important: string;
  hypotheses: InvestigationHypothesis[];
  responsible_department: string;
  recommended_actions: string[];
  verification_steps: string[];
}

export interface InvestigationResponse {
  investigation_id: string;
  status: string;
  facts: InvestigationFacts;
  analysis: InvestigationAnalysis;
  model_used: string;
  generated_at: string;
}

export interface InvestigationRequest {
  anomaly_id: string;
}

import type { ActionResponse } from './action';

export type BackendAction = ActionResponse;

export interface ActionCreatePayload {
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
}

export interface HistoricalInvestigation {
  id: string;
  title: string;
  category: string;
  severity: string;
  date: string;
  status: 'completed' | 'active' | 'in_progress';
  summary: string;
  actionsCount: number;
  anomalyId: string;
  fullData?: InvestigationResponse;
}
