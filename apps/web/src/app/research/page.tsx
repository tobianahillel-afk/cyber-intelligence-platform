import { loadPublicResourcePage } from "@/features/public-footprint/api";
import { PublicResourceTable } from "@/features/public-footprint/resource-table";
import type {
  PublicClaimType,
  PublicResourceKind,
  ResourceRetrievalState,
} from "@/features/public-footprint/types";

const allowedKinds = new Set<PublicResourceKind>([
  "sitemap",
  "feed",
  "structured_data",
  "web_page",
  "document",
  "repository",
  "archive_snapshot",
  "search_result",
]);
const allowedRetrievalStates = new Set<ResourceRetrievalState>([
  "discovered",
  "fetched",
  "not_modified",
  "changed",
  "tombstoned",
  "quarantined",
]);
const allowedClaimTypes = new Set<PublicClaimType>([
  "contract_or_project",
  "technology_or_architecture",
  "provider_partner_customer",
  "security_or_compliance_objective",
  "professional_contact_path",
  "corporate_change",
]);

interface ResearchPageProps {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}

export default async function ResearchPage({ searchParams }: ResearchPageProps) {
  const parameters = await searchParams;
  const query = first(parameters.q);
  const sourceId = first(parameters.source_id);
  const kind = parseKind(first(parameters.kind));
  const retrievalState = parseRetrievalState(first(parameters.retrieval_state));
  const claimType = parseClaimType(first(parameters.claim_type));
  const page = await loadPublicResourcePage({
    query,
    sourceId,
    kind,
    retrievalState,
    claimType,
  });
  const summary = [
    { label: "Resources in scope", value: page.total },
    {
      label: "Changed on page",
      value: page.items.filter((item) => item.retrieval_state === "changed").length,
    },
    {
      label: "Quarantined on page",
      value: page.items.filter((item) => item.retrieval_state === "quarantined").length,
    },
    {
      label: "Claims on page",
      value: page.items.reduce((total, item) => total + item.claim_count, 0),
    },
  ] as const;

  return (
    <section className="page-stack">
      <div className="page-heading">
        <div>
          <p className="eyebrow">Governed public evidence</p>
          <h1>Corporate public footprint</h1>
          <p>
            Search persisted public pages, documents, archive states and evidence claims. Search
            never triggers a new crawl and quarantined leads remain separate from confirmed facts.
          </p>
        </div>
        <span className="live-label">Read-only analyst workspace</span>
      </div>

      <div className="summary-grid" aria-label="Public footprint summary">
        {summary.map((item) => (
          <article className="summary-card" key={item.label}>
            <span>{item.label}</span>
            <strong>{item.value}</strong>
          </article>
        ))}
      </div>

      <section className="panel" aria-labelledby="public-footprint-title">
        <div className="panel-heading public-footprint-heading">
          <div>
            <h2 id="public-footprint-title">Collected resources and historical evidence</h2>
            <p>{page.total} resource(s), ordered by the latest governed observation.</p>
          </div>
          <form className="filter-form public-footprint-filters">
            <label>
              Search evidence
              <input name="q" defaultValue={query} placeholder="URL, title or persisted claim" />
            </label>
            <label>
              Source
              <input name="source_id" defaultValue={sourceId} placeholder="public-web-example" />
            </label>
            <label>
              Resource kind
              <select name="kind" defaultValue={kind ?? ""}>
                <option value="">All kinds</option>
                <option value="web_page">Web page</option>
                <option value="document">Document</option>
                <option value="archive_snapshot">Archive snapshot</option>
                <option value="search_result">Search result</option>
                <option value="repository">Repository</option>
                <option value="structured_data">Structured data</option>
              </select>
            </label>
            <label>
              Retrieval state
              <select name="retrieval_state" defaultValue={retrievalState ?? ""}>
                <option value="">All states</option>
                <option value="discovered">Discovered</option>
                <option value="fetched">Fetched</option>
                <option value="not_modified">Not modified</option>
                <option value="changed">Changed</option>
                <option value="tombstoned">Tombstoned</option>
                <option value="quarantined">Quarantined</option>
              </select>
            </label>
            <label>
              Claim type
              <select name="claim_type" defaultValue={claimType ?? ""}>
                <option value="">All claim types</option>
                <option value="technology_or_architecture">Technology or architecture</option>
                <option value="security_or_compliance_objective">
                  Security or compliance objective
                </option>
                <option value="contract_or_project">Contract or project</option>
                <option value="provider_partner_customer">Provider, partner or customer</option>
                <option value="corporate_change">Corporate change</option>
                <option value="professional_contact_path">Professional contact path</option>
              </select>
            </label>
            <button type="submit">Apply</button>
          </form>
        </div>
        {page.items.length > 0 ? (
          <PublicResourceTable resources={page.items} />
        ) : (
          <div className="empty-state">
            <h3>No matching public evidence</h3>
            <p>
              No persisted resource matches these filters. This workspace does not launch network
              collection from an analyst search.
            </p>
          </div>
        )}
      </section>
    </section>
  );
}

function first(value: string | string[] | undefined): string {
  return (Array.isArray(value) ? value[0] : value) ?? "";
}

function parseKind(value: string): PublicResourceKind | undefined {
  return allowedKinds.has(value as PublicResourceKind) ? (value as PublicResourceKind) : undefined;
}

function parseRetrievalState(value: string): ResourceRetrievalState | undefined {
  return allowedRetrievalStates.has(value as ResourceRetrievalState)
    ? (value as ResourceRetrievalState)
    : undefined;
}

function parseClaimType(value: string): PublicClaimType | undefined {
  return allowedClaimTypes.has(value as PublicClaimType) ? (value as PublicClaimType) : undefined;
}
