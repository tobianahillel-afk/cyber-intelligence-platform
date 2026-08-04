import { loadProviderCatalog } from "@/features/sources/api";
import { ProviderCatalog } from "@/features/sources/provider-catalog";
import type { ProviderOnboardingState } from "@/features/sources/types";

const allowedStates = new Set<ProviderOnboardingState>([
  "not_required",
  "not_configured",
  "awaiting_user_action",
  "awaiting_email_verification",
  "awaiting_mfa",
  "awaiting_provider_approval",
  "ready_to_verify",
  "connected",
  "failed",
  "revoked",
  "blocked",
]);

interface SourcesPageProps {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}

export default async function SourcesPage({ searchParams }: SourcesPageProps) {
  const parameters = await searchParams;
  const selectedState = parseState(parameters.state);
  const catalog = await loadProviderCatalog();
  const providers = selectedState
    ? catalog.items.filter((provider) => provider.state === selectedState)
    : catalog.items;
  const summary = [
    {
      label: "Connected",
      value: catalog.items.filter((provider) => provider.state === "connected").length,
    },
    {
      label: "Human action",
      value: catalog.items.filter((provider) => provider.state.startsWith("awaiting_")).length,
    },
    {
      label: "Ready to verify",
      value: catalog.items.filter((provider) => provider.state === "ready_to_verify").length,
    },
    {
      label: "Blocked or failed",
      value: catalog.items.filter((provider) =>
        ["blocked", "failed"].includes(provider.state),
      ).length,
    },
  ] as const;

  return (
    <section className="page-stack sources-page">
      <div className="page-heading">
        <div>
          <p className="eyebrow">Source operations</p>
          <h1>Provider Onboarding</h1>
          <p>
            Connect public sources automatically and coordinate the official human checkpoints
            required by authenticated providers. Secret values never enter this interface.
          </p>
        </div>
        <span className="live-label">Governed provider catalog</span>
      </div>

      <div className="summary-grid" aria-label="Provider onboarding summary">
        {summary.map((item) => (
          <article className="summary-card" key={item.label}>
            <span>{item.label}</span>
            <strong>{item.value}</strong>
          </article>
        ))}
      </div>

      <section className="panel" aria-labelledby="provider-catalog-title">
        <div className="panel-heading">
          <div>
            <h2 id="provider-catalog-title">Governed sources</h2>
            <p>
              {providers.length} of {catalog.total} provider(s) shown. Registration links point
              only to official provider-controlled portals.
            </p>
          </div>
          <form className="filter-form">
            <label>
              State
              <select name="state" defaultValue={selectedState ?? ""}>
                <option value="">All states</option>
                <option value="connected">Connected</option>
                <option value="not_configured">Not configured</option>
                <option value="awaiting_user_action">User action required</option>
                <option value="awaiting_email_verification">Email verification</option>
                <option value="awaiting_mfa">MFA required</option>
                <option value="awaiting_provider_approval">Provider approval</option>
                <option value="ready_to_verify">Ready to verify</option>
                <option value="failed">Failed</option>
                <option value="revoked">Revoked</option>
                <option value="blocked">Blocked</option>
              </select>
            </label>
            <button type="submit">Apply</button>
          </form>
        </div>
        <ProviderCatalog providers={providers} />
      </section>
    </section>
  );
}

function parseState(
  value: string | string[] | undefined,
): ProviderOnboardingState | undefined {
  const raw = Array.isArray(value) ? value[0] : value;
  return raw && allowedStates.has(raw as ProviderOnboardingState)
    ? (raw as ProviderOnboardingState)
    : undefined;
}
