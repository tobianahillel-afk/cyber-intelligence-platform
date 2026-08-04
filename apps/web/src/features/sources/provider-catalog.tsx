import {
  humanCheckpointAction,
  registerSecretReferenceAction,
  revokeProviderAction,
  startProviderAction,
  verifyProviderAction,
} from "@/app/sources/actions";

import type {
  ProviderHumanAction,
  ProviderOnboarding,
  ProviderOnboardingState,
} from "./types";

const stateLabels: Record<ProviderOnboardingState, string> = {
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

const actionLabels: Record<ProviderHumanAction, string> = {
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

interface ProviderCatalogProps {
  providers: readonly ProviderOnboarding[];
}

export function ProviderCatalog({ providers }: ProviderCatalogProps) {
  if (providers.length === 0) {
    return (
      <div className="empty-state">
        <h3>No provider matches this view</h3>
        <p>Change the state filter to display the remaining governed sources.</p>
      </div>
    );
  }
  return (
    <div className="provider-grid">
      {providers.map((provider) => (
        <ProviderCard key={provider.source_id} provider={provider} />
      ))}
    </div>
  );
}

function ProviderCard({ provider }: { provider: ProviderOnboarding }) {
  const blocked = provider.state === "blocked";
  return (
    <article className="provider-card">
      <header className="provider-card-heading">
        <div>
          <p className="provider-source-id">{provider.source_id}</p>
          <h3>{provider.display_name}</h3>
        </div>
        <span className={`provider-state provider-state-${provider.state}`}>
          {stateLabels[provider.state]}
        </span>
      </header>

      <dl className="provider-facts">
        <div>
          <dt>Authentication</dt>
          <dd>{provider.auth_mode.replaceAll("_", " ")}</dd>
        </div>
        <div>
          <dt>Onboarding</dt>
          <dd>{provider.automatic_onboarding ? "Automatic" : "Human checkpoint"}</dd>
        </div>
        <div>
          <dt>Last verified</dt>
          <dd>{provider.last_verified_at ? formatDate(provider.last_verified_at) : "Never"}</dd>
        </div>
      </dl>

      <div className="provider-links" aria-label={`${provider.display_name} official links`}>
        <a href={provider.documentation_url} target="_blank" rel="noreferrer">
          Official documentation
        </a>
        {provider.signup_url ? (
          <a href={provider.signup_url} target="_blank" rel="noreferrer">
            Official registration
          </a>
        ) : null}
        {provider.console_url && provider.console_url !== provider.signup_url ? (
          <a href={provider.console_url} target="_blank" rel="noreferrer">
            Provider console
          </a>
        ) : null}
      </div>

      {provider.blocked_reason ? (
        <div className="provider-blocked">
          <strong>Execution disabled</strong>
          <p>{provider.blocked_reason}</p>
        </div>
      ) : null}

      {provider.human_actions.length > 0 ? (
        <section className="provider-checklist" aria-label="Required human actions">
          <h4>Required checkpoints</h4>
          <ol>
            {provider.human_actions.map((action) => (
              <li key={action}>{actionLabels[action]}</li>
            ))}
          </ol>
        </section>
      ) : null}

      {provider.required_secret_names.length > 0 ? (
        <section className="provider-secrets" aria-label="Secret references">
          <h4>Deployment secret references</h4>
          <p>Only references are accepted. Values remain outside Git, the API and the database.</p>
          {provider.required_secret_names.map((name) => (
            <SecretReferenceRow key={name} provider={provider} name={name} />
          ))}
        </section>
      ) : null}

      {provider.last_error_message ? (
        <div className="provider-error">
          <strong>{provider.last_error_code ?? "Verification error"}</strong>
          <p>{provider.last_error_message}</p>
        </div>
      ) : null}

      {!blocked ? <ProviderActions provider={provider} /> : null}
    </article>
  );
}

function SecretReferenceRow({
  provider,
  name,
}: {
  provider: ProviderOnboarding;
  name: string;
}) {
  const configured = provider.secret_references[name];
  return (
    <div className="secret-reference-row">
      <div>
        <strong>{name}</strong>
        <span>{configured ?? "Missing reference"}</span>
      </div>
      <form action={registerSecretReferenceAction.bind(null, provider.source_id)}>
        <input name="actor" defaultValue="provider-operator" aria-label="Operator" required />
        <input name="name" type="hidden" value={name} />
        <input
          name="reference"
          placeholder={referencePlaceholder(provider.source_id, name)}
          aria-label={`${name} secret reference`}
          required
        />
        <button type="submit">Register reference</button>
      </form>
    </div>
  );
}

function ProviderActions({ provider }: { provider: ProviderOnboarding }) {
  const startVisible = ["not_configured", "revoked", "failed"].includes(provider.state);
  const revokeVisible = provider.state !== "revoked" && provider.state !== "not_configured";
  return (
    <section className="provider-actions" aria-label={`${provider.display_name} actions`}>
      <h4>Operator actions</h4>
      <div className="provider-action-buttons">
        {startVisible ? (
          <ActorAction
            action={startProviderAction.bind(null, provider.source_id)}
            label="Start onboarding"
          />
        ) : null}
        <ActorAction
          action={verifyProviderAction.bind(null, provider.source_id)}
          label="Verify configuration"
        />
        {revokeVisible ? (
          <ActorAction
            action={revokeProviderAction.bind(null, provider.source_id)}
            label="Revoke configuration"
            destructive
          />
        ) : null}
      </div>
      {provider.human_actions.length > 0 ? (
        <form
          className="checkpoint-form"
          action={humanCheckpointAction.bind(null, provider.source_id)}
        >
          <input name="actor" defaultValue="provider-operator" aria-label="Operator" required />
          <select name="state" defaultValue="awaiting_user_action" aria-label="Checkpoint state">
            <option value="awaiting_user_action">User action required</option>
            <option value="awaiting_email_verification">Email verification required</option>
            <option value="awaiting_mfa">MFA required</option>
            <option value="awaiting_provider_approval">Provider approval pending</option>
          </select>
          <input name="note" placeholder="Optional audit note" aria-label="Audit note" />
          <button type="submit">Record checkpoint</button>
        </form>
      ) : null}
    </section>
  );
}

function ActorAction({
  action,
  label,
  destructive = false,
}: {
  action: (formData: FormData) => Promise<void>;
  label: string;
  destructive?: boolean;
}) {
  return (
    <form action={action}>
      <input name="actor" type="hidden" value="provider-operator" />
      <button className={destructive ? "button-danger" : undefined} type="submit">
        {label}
      </button>
    </form>
  );
}

function referencePlaceholder(sourceId: string, name: string): string {
  const token = `${sourceId}_${name}`.replaceAll("-", "_").toUpperCase();
  return `env://CIP_${token}`;
}

function formatDate(value: string): string {
  return new Intl.DateTimeFormat("en", {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone: "UTC",
  }).format(new Date(value));
}
