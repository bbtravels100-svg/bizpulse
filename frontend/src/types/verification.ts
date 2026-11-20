// ============================================================
// BizPulse Frontend — Verification Engine Types
// Matches backend/app/verification/models.py
// ============================================================

export type VerificationOutcome =
  | 'Improved'
  | 'Not Improved'
  | 'Deteriorated'
  | 'Inconclusive'
  | 'Insufficient Data';

export type VerificationStage = 'initial' | 'follow_up' | 'final' | 'manual';

export type MetricComparisonDirection = 'increase' | 'decrease';

export interface BaselineMetric {
  id: string;
  action_id: string;
  investigation_id: string;
  anomaly_id: string;
  metric_name: string;
  baseline_value: number;
  baseline_period: string;
  expected_improvement: string;
  target_value: number;
  comparison_direction: MetricComparisonDirection;
  verification_criteria: string;
  captured_at: string;
}

export interface VerificationComparison {
  metric_name: string;
  baseline_value: number;
  current_value: number;
  absolute_change: number;
  percentage_change: number;
  target_value: number;
  comparison_direction: MetricComparisonDirection;
  target_met: boolean;
  outcome: VerificationOutcome;
  calculation_summary: string;
}

export interface GeminiFollowUpAnalysis {
  what_changed: string;
  did_metric_improve: boolean;
  did_it_meet_target: boolean;
  possible_explanations: string[];
  recommended_next_steps: string[];
  causal_attribution_confidence: 'high' | 'medium' | 'low' | 'unsubstantiated';
}

export interface VerificationRunResponse {
  id: string;
  action_id: string;
  baseline_id: string;
  verification_stage: VerificationStage;
  evaluation_period: string;
  comparison: VerificationComparison;
  outcome: VerificationOutcome;
  target_met: boolean;
  is_resolved: boolean;
  needs_reopening: boolean;
  data_source: string;
  gemini_analysis?: GeminiFollowUpAnalysis | null;
  executed_at: string;
}

export interface VerificationNoteResponse {
  id: number;
  verification_id: string;
  action_id: string;
  note: string;
  author: string;
  created_at: string;
}

export interface VerificationHistoryResponse {
  action_id: string;
  baseline: BaselineMetric;
  verification_runs: VerificationRunResponse[];
  notes: VerificationNoteResponse[];
  current_resolution_status: string;
}

export interface VerificationTriggerRequest {
  action_id: string;
  stage?: VerificationStage;
  current_value?: number;
  evaluation_period?: string;
  simulated_data_scenario?: 'improved' | 'not_improved' | 'deteriorated' | 'insufficient_data';
}

export interface ReopenInvestigationRequest {
  action_id: string;
  reason: string;
  requested_by?: string;
  suggested_additional_actions?: string[];
}

export interface ReopenResponse {
  status: string;
  original_action_id: string;
  new_action_id: string;
  reopening_reason?: string;
  requested_by?: string;
  new_action_proposal?: any;
  message?: string;
}

export interface ActionVerificationSummary {
  actionId: string;
  problemDescription: string;
  recommendedAction: string;
  responsibleDepartment: string;
  actionStatus: string;
  baseline?: BaselineMetric;
  latestRun?: VerificationRunResponse;
  runsCount: number;
  resolutionStatus: 'Resolved' | 'Unresolved' | 'Awaiting Verification' | 'No Baseline';
}
