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
