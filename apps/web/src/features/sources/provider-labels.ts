import type {
  ProviderHumanAction,
  ProviderOnboardingState,
} from "./types";

export const stateLabels: Record<ProviderOnboardingState, string> = {
  not_required: "No setup required",
  not_configured: "Not configured",
  awaiting_user_action: "User action required",
  awaiting_email_verification: "Email verification required",
  awaiting_mfa: "MFA required",
  awaiting_provider_approval: "Provider approval pending",
  ready_to_verify: "Ready to verify",
  connected: "Connected",
  failed: "Verification failed",
  revoked: "Revoked",
  blocked: "Blocked",
};

export const actionLabels: Record<ProviderHumanAction, string> = {
  open_official_signup: "Open the official registration portal",
  sign_in: "Sign in through the official provider portal",
  verify_email: "Verify the account email through the provider message",
  complete_mfa: "Complete provider-managed MFA",
  accept_provider_terms: "Review and accept the provider terms",
  request_provider_access: "Request the documented API or data access",
  wait_for_provider_approval: "Wait for the provider approval",
  retrieve_technical_credentials: "Retrieve the issued technical credentials",
  register_secret_reference: "Register deployment secret references below",
  enable_source_policy: "Enable the governed source policy after review",
};

export function referencePlaceholder(sourceId: string, name: string): string {
  const token = `${sourceId}_${name}`.replaceAll("-", "_").toUpperCase();
  return `env://CIP_${token}`;
}

export function formatProviderDate(value: string): string {
  return new Intl.DateTimeFormat("en", {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone: "UTC",
  }).format(new Date(value));
}
