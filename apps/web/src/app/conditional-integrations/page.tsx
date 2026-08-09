import { loadConditionalProviders } from "@/features/conditional-integrations/api";
import { ConditionalProviderCatalog } from "@/features/conditional-integrations/catalog";
import { loadSourcePortfolio } from "@/features/sources/api";

export default async function ConditionalIntegrationsPage() {
  const [providers, portfolio] = await Promise.all([
    loadConditionalProviders(),
    loadSourcePortfolio(),
  ]);
  const candidates = portfolio.items.filter((source) =>
    source.category.startsWith("conditional_"),
  );
  const approvals = new Map(
    providers.items.map((provider) => [provider.approval.source_id, provider]),
  );
  const summary = [
    { label: "Conditional candidates", value: candidates.length },
    {
      label: "Approved dossiers",
      value: providers.items.filter((provider) => provider.approval.state === "approved").length,
    },
    {
      label: "Runtime adapters",
      value: candidates.filter((candidate) => candidate.adapter !== null).length,
    },
    {
      label: "Kill switches active",
      value: providers.items.filter((provider) => provider.control?.kill_switch_active).length,
    },
  ] as const;

  return (
    <section className="page-stack conditional-page">
      <div className="page-heading">
        <div>
          <p className="eyebrow">Provider governance</p>
          <h1>Conditional Integrations</h1>
          <p>
            Review licensed, administrator-consented and premium providers without turning a
            catalog entry or account reference into execution authorization.
          </p>
        </div>
        <span className="live-label">Fail-closed by default</span>
      </div>

      <div className="summary-grid" aria-label="Conditional integration summary">
        {summary.map((item) => (
          <article className="summary-card" key={item.label}>
            <span>{item.label}</span>
            <strong>{item.value}</strong>
          </article>
        ))}
      </div>

      <section className="panel">
        <div className="conditional-safety-banner">
          Public/professional availability ≠ platform automation authorization. No provider in
          this workspace can execute without its exact approval dossier plus Source Governance,
          onboarding, portfolio, capability, quota, cost and local runtime gates.
        </div>
      </section>

      <section className="panel" aria-labelledby="conditional-catalog-title">
        <div className="panel-heading">
          <div>
            <h2 id="conditional-catalog-title">Governed provider candidates</h2>
            <p>
              {candidates.length} candidate(s). Default catalog entries contain no executable
              adapter, no schedule and no network authorization.
            </p>
          </div>
        </div>
        <ConditionalProviderCatalog candidates={candidates} approvals={approvals} />
      </section>
    </section>
  );
}
