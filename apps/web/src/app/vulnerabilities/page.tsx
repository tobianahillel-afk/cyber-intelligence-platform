import { loadVulnerabilityPage } from "@/features/vulnerabilities/api";
import type {
  ExploitationKind,
  VulnerabilitySource,
  VulnerabilityStatus,
} from "@/features/vulnerabilities/types";
import { VulnerabilityTable } from "@/features/vulnerabilities/vulnerability-table";

const statuses = new Set<VulnerabilityStatus>([
  "published",
  "updated",
  "rejected",
  "withdrawn",
  "superseded",
]);
const sources = new Set<VulnerabilitySource>([
  "cve_org",
  "nvd",
  "cisa_kev",
  "epss",
  "osv",
  "github_advisory",
  "circl_vulnerability_lookup",
]);
const exploitationKinds = new Set<ExploitationKind>([
  "proof_of_concept",
  "observed_exploitation",
  "known_exploited_catalog",
  "ransomware_campaign",
]);

interface VulnerabilitiesPageProps {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}

export default async function VulnerabilitiesPage({
  searchParams,
}: VulnerabilitiesPageProps) {
  const parameters = await searchParams;
  const query = first(parameters.q);
  const status = parseValue(first(parameters.status), statuses);
  const source = parseValue(first(parameters.source), sources);
  const exploitationKind = parseValue(
    first(parameters.exploitation_kind),
    exploitationKinds,
  );
  const page = await loadVulnerabilityPage({
    query,
    status,
    source,
    exploitationKind,
  });
  const summary = [
    { label: "Vulnerabilities", value: page.total },
    {
      label: "KEV on page",
      value: page.items.filter((item) =>
        item.exploitation_kinds.includes("known_exploited_catalog"),
      ).length,
    },
    {
      label: "PoC on page",
      value: page.items.filter((item) =>
        item.exploitation_kinds.includes("proof_of_concept"),
      ).length,
    },
    {
      label: "Withdrawn on page",
      value: page.items.filter((item) => item.status === "withdrawn").length,
    },
  ] as const;

  return (
    <section className="page-stack">
      <div className="page-heading">
        <div>
          <p className="eyebrow">Global vulnerability knowledge</p>
          <h1>Vulnerabilities and exploitation state</h1>
          <p>
            Compare persisted CVE, CVSS, affected-range, EPSS, KEV and advisory facts without
            treating global publication as evidence that an organization is exposed.
          </p>
        </div>
        <span className="live-label">Persisted data only</span>
      </div>

      <div className="exposure-warning">
        A vulnerability record never proves that a prospect uses the affected product or is
        vulnerable. Organization exposure requires separate, authorized evidence.
      </div>

      <div className="summary-grid" aria-label="Vulnerability summary">
        {summary.map((item) => (
          <article className="summary-card" key={item.label}>
            <span>{item.label}</span>
            <strong>{item.value}</strong>
          </article>
        ))}
      </div>

      <section className="panel" aria-labelledby="vulnerability-title">
        <div className="panel-heading vulnerability-heading">
          <div>
            <h2 id="vulnerability-title">Reconciled vulnerability records</h2>
            <p>{page.total} record(s), ordered by the latest source revision.</p>
          </div>
          <form className="filter-form vulnerability-filters">
            <label>
              Search
              <input name="q" defaultValue={query} placeholder="CVE, GHSA or title" />
            </label>
            <label>
              Status
              <select name="status" defaultValue={status ?? ""}>
                <option value="">All statuses</option>
                <option value="updated">Updated</option>
                <option value="published">Published</option>
                <option value="withdrawn">Withdrawn</option>
                <option value="rejected">Rejected</option>
                <option value="superseded">Superseded</option>
              </select>
            </label>
            <label>
              Source
              <select name="source" defaultValue={source ?? ""}>
                <option value="">All sources</option>
                <option value="cve_org">CVE.org</option>
                <option value="nvd">NVD</option>
                <option value="cisa_kev">CISA KEV</option>
                <option value="epss">EPSS</option>
                <option value="osv">OSV</option>
                <option value="github_advisory">GitHub Advisory</option>
                <option value="circl_vulnerability_lookup">CIRCL</option>
              </select>
            </label>
            <label>
              Exploitation dimension
              <select
                name="exploitation_kind"
                defaultValue={exploitationKind ?? ""}
              >
                <option value="">All dimensions</option>
                <option value="known_exploited_catalog">CISA KEV</option>
                <option value="proof_of_concept">Public PoC</option>
                <option value="observed_exploitation">Observed exploitation</option>
                <option value="ransomware_campaign">Ransomware campaign</option>
              </select>
            </label>
            <button type="submit">Apply</button>
          </form>
        </div>
        {page.items.length > 0 ? (
          <VulnerabilityTable vulnerabilities={page.items} />
        ) : (
          <div className="empty-state">
            <h3>No matching vulnerability record</h3>
            <p>These filters search persisted data and never launch provider collection.</p>
          </div>
        )}
      </section>
    </section>
  );
}

function first(value: string | string[] | undefined): string {
  return (Array.isArray(value) ? value[0] : value) ?? "";
}

function parseValue<T extends string>(value: string, allowed: Set<T>): T | undefined {
  return allowed.has(value as T) ? (value as T) : undefined;
}
