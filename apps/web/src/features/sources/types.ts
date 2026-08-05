export type ProviderAuthMode =
  | "none"
  | "api_key"
  | "oauth2_client_credentials"
  | "basic"
  | "sftp_key"
  | "manual";

export type ProviderOnboardingState =
  | "not_required"
  | "not_configured"
  | "awaiting_user_action"
  | "awaiting_email_verification"
  | "awaiting_mfa"
  | "awaiting_provider_approval"
  | "ready_to_verify"
  | "connected"
  | "failed"
  | "revoked"
  | "blocked";

export type ProviderHumanAction =
  | "open_official_signup"
  | "sign_in"
  | "verify_email"
  | "complete_mfa"
  | "accept_provider_terms"
  | "request_provider_access"
  | "wait_for_provider_approval"
  | "retrieve_technical_credentials"
  | "register_secret_reference"
  | "enable_source_policy";

export interface ProviderOnboarding {
  source_id: string;
  display_name: string;
  auth_mode: ProviderAuthMode;
  state: ProviderOnboardingState;
  documentation_url: string;
  signup_url: string | null;
  console_url: string | null;
  required_secret_names: readonly string[];
  missing_secret_names: readonly string[];
  human_actions: readonly ProviderHumanAction[];
  automatic_onboarding: boolean;
  secret_references: Readonly<Record<string, string>>;
  blocked_reason: string | null;
  last_verified_at: string | null;
  expires_at: string | null;
  last_error_code: string | null;
  last_error_message: string | null;
  updated_at: string | null;
}

export interface ProviderOnboardingPage {
  items: readonly ProviderOnboarding[];
  total: number;
}

export type SourcePortfolioStatus =
  | "candidate"
  | "executable"
  | "paused"
  | "disabled";

export interface SourceAdapterCapability {
  adapter_id: string;
  adapter_version: string;
  provider_schema_version: string;
  modes: readonly string[];
  canonical_output_types: readonly string[];
  supports_corrections: boolean;
  supports_tombstones: boolean;
  supports_retractions: boolean;
  max_page_size: number | null;
  max_window_days: number | null;
  cost_per_request: number;
}

export interface SourcePortfolioHealth {
  freshness_state: string;
  schema_state: string;
  volume_state: string;
  field_population_state: string;
  circuit_state: string;
  last_attempt_at: string | null;
  last_success_at: string | null;
  last_source_record_at: string | null;
  consecutive_failures: number;
  quota_remaining: number | null;
  monthly_cost_used: number;
  cost_window_started_at: string | null;
  current_backfill_state: string | null;
  last_error_code: string | null;
}

export interface SourcePortfolioEntry {
  source_id: string;
  display_name: string;
  canonical_url: string;
  category: string;
  status: SourcePortfolioStatus;
  executable: boolean;
  manual_resume_allowed: boolean;
  freshness_max_age_seconds: number;
  commercial_use_cases: readonly string[];
  authorization_expires_at: string | null;
  review_due_at: string | null;
  candidate_origin: string | null;
  monthly_cost_limit: number | null;
  adapter: SourceAdapterCapability | null;
  health: SourcePortfolioHealth;
}

export interface SourcePortfolioPage {
  items: readonly SourcePortfolioEntry[];
  total: number;
}

export interface PriorityRefreshResult {
  job_id: string;
  created: boolean;
}
