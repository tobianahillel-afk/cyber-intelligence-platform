export type ConditionalProviderKind =
  | "linkedin"
  | "discord"
  | "brixhub"
  | "premium_cti"
  | "commercial_data"
  | "other";

export type ConditionalAccessMethod =
  | "official_api"
  | "licensed_api"
  | "admin_installed_connector"
  | "authorized_export"
  | "customer_provided_access"
  | "manual_import";

export type ApprovalState =
  | "draft"
  | "pending_review"
  | "approved"
  | "expired"
  | "revoked"
  | "paused";

export type TermsReviewState = "current" | "changed" | "review_required";

export type ProviderControlAction =
  | "pause"
  | "resume"
  | "activate_kill_switch"
  | "clear_kill_switch";

export interface ConditionalApproval {
  source_id: string;
  provider_kind: string;
  access_method: string;
  state: string;
  authorization_document_reference: string | null;
  licence_reference: string | null;
  terms_reference: string | null;
  terms_state: string;
  approved_scopes: readonly string[];
  approved_fields: readonly string[];
  approved_purposes: readonly string[];
  approved_data_categories: readonly string[];
  retention_days: number | null;
  automated_collection_allowed: boolean;
  account_reference: string | null;
  reviewed_at: string | null;
  review_due_at: string | null;
  expires_at: string | null;
  revoked_at: string | null;
  paused_reason: string | null;
  current_revision_key: string;
  created_at: string;
  updated_at: string;
}

export interface ConditionalApprovalRevision {
  revision_key: string;
  state: string;
  access_method: string;
  terms_state: string;
  approved_scopes: readonly string[];
  approved_fields: readonly string[];
  approved_purposes: readonly string[];
  approved_data_categories: readonly string[];
  retention_days: number | null;
  automated_collection_allowed: boolean;
  account_reference: string | null;
  reviewed_at: string | null;
  review_due_at: string | null;
  expires_at: string | null;
  revoked_at: string | null;
  paused_reason: string | null;
  actor: string;
  change_reason: string;
  created_at: string;
}

export interface ConditionalRuntimeControl {
  source_id: string;
  paused: boolean;
  kill_switch_active: boolean;
  paused_reason: string | null;
  updated_at: string;
}

export interface ConditionalControlDecision {
  decision_key: string;
  action: string;
  actor: string;
  reason: string;
  resulting_paused: boolean;
  resulting_kill_switch_active: boolean;
  decided_at: string;
  created_at: string;
}

export interface ConditionalExecutionDecision {
  decision_key: string;
  access_method: string;
  purpose: string;
  data_category: string;
  target_url: string;
  requested_scopes: readonly string[];
  requested_fields: readonly string[];
  retention_days: number;
  automated: boolean;
  store_raw_content: boolean;
  account_reference: string | null;
  onboarding_state: string;
  source_policy_allowed: boolean;
  source_portfolio_allowed: boolean;
  adapter_capability_present: boolean;
  provider_paused: boolean;
  kill_switch_active: boolean;
  quota_remaining: number | null;
  monthly_cost_used: number;
  monthly_cost_limit: number | null;
  allowed: boolean;
  reasons: readonly string[];
  evaluated_at: string;
}

export interface ConditionalProviderSummary {
  approval: ConditionalApproval;
  control: ConditionalRuntimeControl | null;
}

export interface ConditionalProviderDetail extends ConditionalProviderSummary {
  revisions: readonly ConditionalApprovalRevision[];
  control_decisions: readonly ConditionalControlDecision[];
  execution_decisions: readonly ConditionalExecutionDecision[];
}

export interface ConditionalProviderPage {
  items: readonly ConditionalProviderSummary[];
  total: number;
}

export interface SourceValueSummary {
  executions: number;
  modified_executions: number;
  observations_written: number;
  commercial_projections: number;
  identity_projections: number;
  request_cost: number;
}

export interface ConditionalProviderValue {
  source_id: string;
  evidence_available: boolean;
  source: SourceValueSummary;
  portfolio_without_source: SourceValueSummary;
}
