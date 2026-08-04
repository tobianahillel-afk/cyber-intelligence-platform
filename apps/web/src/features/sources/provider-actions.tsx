import {
  humanCheckpointAction,
  registerSecretReferenceAction,
  revokeProviderAction,
  startProviderAction,
  verifyProviderAction,
} from "@/app/sources/actions";

import { referencePlaceholder } from "./provider-labels";
import type { ProviderOnboarding } from "./types";

export function ProviderSecretReferences({
  provider,
}: {
  provider: ProviderOnboarding;
}) {
  if (provider.required_secret_names.length === 0) {
    return null;
  }
  return (
    <section className="provider-secrets" aria-label="Secret references">
      <h4>Deployment secret references</h4>
      <p>Only references are accepted. Values remain outside Git, the API and the database.</p>
      {provider.required_secret_names.map((name) => (
        <SecretReferenceRow key={name} provider={provider} name={name} />
      ))}
    </section>
  );
}

export function ProviderOperatorActions({
  provider,
}: {
  provider: ProviderOnboarding;
}) {
  if (provider.state === "blocked") {
    return null;
  }
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
