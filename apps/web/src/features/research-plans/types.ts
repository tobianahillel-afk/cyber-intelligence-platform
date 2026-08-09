export type ResearchPlanState =
  | "draft"
  | "pending_review"
  | "approved"
  | "in_progress"
  | "paused"
  | "completed"
  | "cancelled";

export type ResearchStepMode =
  | "persisted_search"
  | "manual_link"
  | "automated_adapter"
  | "approved_ingestion";

export interface ResearchPlan {
  id: string;
  question: string;
  purpose: string;
  data_category: string;
  state: ResearchPlanState | string;
  max_steps: number;
  max_automated_steps: number;
  max_total_cost: number;
  max_step_cost: number;
  allowed_source_ids: readonly string[];
  allowed_tool_ids: readonly string[];
  approved_step_keys: readonly string[];
  allowed_hosts: readonly string[];
  allowed_path_prefixes: readonly string[];
  max_risk_level: string;
  expires_at: string | null;
  current_revision_key: string;
  created_at: string;
  updated_at: string;
}

export interface ResearchUsage {
  completed_steps: number;
  automated_steps: number;
  cost_used: number;
}

export interface ResearchPlanRevision {
  revision_key: string;
  question: string;
  purpose: string;
  data_category: string;
  state: string;
  budget: Record<string, unknown>;
  allowed_source_ids: readonly string[];
  allowed_tool_ids: readonly string[];
  approved_step_keys: readonly string[];
  allowed_hosts: readonly string[];
  allowed_path_prefixes: readonly string[];
  max_risk_level: string;
  expires_at: string | null;
  actor: string;
  change_reason: string;
  created_at: string;
}

export interface ResearchStep {
  id: string;
  step_key: string;
  sequence: number;
  source_id: string;
  tool_id: string;
  mode: ResearchStepMode | string;
  purpose: string;
  data_category: string;
  estimated_cost: number;
  risk_level: string;
  target_url: string | null;
  query_text: string | null;
  ingestion_path_id: string | null;
  state: string;
  created_at: string;
  updated_at: string;
}

export interface ResearchPlanDecision {
  decision_key: string;
  decision_type: string;
  actor: string;
  reason: string;
  previous_state: string;
  resulting_state: string;
  decided_at: string;
  created_at: string;
}

export interface ResearchStepDecision {
  step_id: string;
  decision_key: string;
  allowed: boolean;
  next_state: string;
  reasons: readonly string[];
  usage_snapshot: Record<string, unknown>;
  runtime_snapshot: Record<string, unknown>;
  evaluated_at: string;
  created_at: string;
}

export interface ResearchAttempt {
  id: string;
  step_id: string;
  attempt_key: string;
  mode: string;
  state: string;
  actor: string;
  external_action_started: boolean;
  external_action_reference: string | null;
  error_code: string | null;
  started_at: string;
  completed_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface ResearchResult {
  id: string;
  step_id: string;
  attempt_id: string | null;
  result_key: string;
  result_type: string;
  evidence_reference: string;
  provenance_reference: string;
  source_id: string;
  summary: string | null;
  recorded_by: string;
  recorded_at: string;
}

export interface ResearchPlanDetail {
  plan: ResearchPlan;
  usage: ResearchUsage;
  revisions: readonly ResearchPlanRevision[];
  steps: readonly ResearchStep[];
  plan_decisions: readonly ResearchPlanDecision[];
  step_decisions: readonly ResearchStepDecision[];
  attempts: readonly ResearchAttempt[];
  results: readonly ResearchResult[];
}

export interface ResearchPlanPage {
  items: readonly ResearchPlan[];
  total: number;
}
