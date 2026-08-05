import { loadProviderCatalog, loadSourcePortfolio } from "@/features/sources/api";
import { ProviderCatalog } from "@/features/sources/provider-catalog";
import { SourcePortfolio } from "@/features/sources/source-portfolio";
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
  const [catalog, portfolio] = await Promise.all([
    loadProviderCatalog(),
    loadSourcePortfolio(),
  ]);
  const providers = selectedState
    ? catalog.items.filter((provider) => provider.state === selectedState)
    : catalog.items;
  const summary = [
    {
      label: "Connected",
      value: catalog.items.filter((provider) => provider.state === "connected").length,
    },
    {
      label: "Executable sources",
      value: portfolio.items.filter((source) => source.status === "executable").length,
    },
    {
      label: "Stale or unavailable",
      value: portfolio.items.filter((source) =>
        ["stale_refresh_queued", "source_unavailable", "authorization_expired"].includes(
          source.health.freshness_state,
        ),
      ).length,
    },
    {
      label: "Candidates",
      value: portfolio.items.filter((source) => source.status === "candidate").length,
    },
  ] as const;

  return (
    <section className="page-stack sources-page">
      <div className="page-heading">
        <div>
          <p className="eyebrow">Source operations</p>
          <h1>Source Control Plane</h1>
          <p>
            Coordinate provider onboarding, runtime capability, freshness, backfill and source
            health without exposing provider secret values to this interface.
          </p>
        </div>
        <span className="live-label">Governed source portfolio</span>
      </div>

      <div className="summary-grid" aria-label="Source portfolio summary">
        {summary.map((item) => (
          <article className="summary-card" key={item.label}>
            <span>{item.label}</span>
            <strong>{item.value}</strong>
          </article>
        ))}
      </div>

      <section className="panel" aria-labelledby="source-runtime-title">
        <div className="panel-heading">
          <div>
            <h2 id="source-runtime-title">Runtime, freshness and health</h2>
            <p>
              {portfolio.total} catalog entries. Candidates cannot execute until a reviewed
              adapter, source policy and authorization are present.
            </p>
          </div>
        </div>
        <SourcePortfolio sources={portfolio.items} />
      </section>

      <section className="panel" aria-labelledby="provider-catalog-title">
        <div className="panel-heading">
          <div>
            <h2 id="provider-catalog-title">Provider onboarding</h2>
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
