import {
  ProviderOperatorActions,
  ProviderSecretReferences,
} from "./provider-actions";
import {
  actionLabels,
  formatProviderDate,
  stateLabels,
} from "./provider-labels";
import type { ProviderOnboarding } from "./types";

export function ProviderCard({ provider }: { provider: ProviderOnboarding }) {
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
          <dd>
            {provider.last_verified_at
              ? formatProviderDate(provider.last_verified_at)
              : "Never"}
          </dd>
        </div>
      </dl>

      <ProviderLinks provider={provider} />
      {provider.blocked_reason ? (
        <div className="provider-blocked">
          <strong>Execution disabled</strong>
          <p>{provider.blocked_reason}</p>
        </div>
      ) : null}
      <ProviderChecklist provider={provider} />
      <ProviderSecretReferences provider={provider} />
      {provider.last_error_message ? (
        <div className="provider-error">
          <strong>{provider.last_error_code ?? "Verification error"}</strong>
          <p>{provider.last_error_message}</p>
        </div>
      ) : null}
      <ProviderOperatorActions provider={provider} />
    </article>
  );
}

function ProviderLinks({ provider }: { provider: ProviderOnboarding }) {
  return (
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
  );
}

function ProviderChecklist({ provider }: { provider: ProviderOnboarding }) {
  if (provider.human_actions.length === 0) {
    return null;
  }
  return (
    <section className="provider-checklist" aria-label="Required human actions">
      <h4>Required checkpoints</h4>
      <ol>
        {provider.human_actions.map((action) => (
          <li key={action}>{actionLabels[action]}</li>
        ))}
      </ol>
    </section>
  );
}
