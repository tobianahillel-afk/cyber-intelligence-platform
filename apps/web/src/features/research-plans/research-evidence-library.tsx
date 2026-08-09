import { PublicResourceTable } from "@/features/public-footprint/resource-table";
import type {
  PublicClaimType,
  PublicResourceKind,
  PublicResourcePage,
  ResourceRetrievalState,
} from "@/features/public-footprint/types";

interface ResearchEvidenceLibraryProps {
  page: PublicResourcePage;
  query: string;
  sourceId: string;
  kind: PublicResourceKind | undefined;
  retrievalState: ResourceRetrievalState | undefined;
  claimType: PublicClaimType | undefined;
}

export function ResearchEvidenceLibrary({
  page,
  query,
  sourceId,
  kind,
  retrievalState,
  claimType,
}: ResearchEvidenceLibraryProps) {
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
    <section className="panel" aria-labelledby="research-evidence-title">
      <div className="panel-heading public-footprint-heading">
        <div>
          <p className="eyebrow">Persisted evidence library</p>
          <h2 id="research-evidence-title">Collected resources and historical evidence</h2>
          <p>
            Search {page.total} persisted resource(s). This section never launches a crawl or
            provider request from a page render.
          </p>
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

      <div className="research-evidence-summary" aria-label="Evidence library summary">
        {summary.map((item) => (
          <span key={item.label}>
            <strong>{item.value}</strong> {item.label.toLowerCase()}
          </span>
        ))}
      </div>

      {page.items.length > 0 ? (
        <PublicResourceTable resources={page.items} />
      ) : (
        <div className="empty-state">
          <h3>No matching public evidence</h3>
          <p>
            No persisted resource matches these filters. Research plans and manual links do not
            convert this page into a live network search.
          </p>
        </div>
      )}
    </section>
  );
}
