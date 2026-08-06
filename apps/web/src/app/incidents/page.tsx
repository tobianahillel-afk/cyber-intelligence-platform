import { loadIncidentPage } from "@/features/incidents/api";
import { IncidentTable } from "@/features/incidents/incident-table";
import type {
  IncidentClaimType,
  IncidentSourceKind,
  IncidentStatus,
  IncidentType,
  OrganizationLinkStatus,
} from "@/features/incidents/types";

const statuses = new Set<IncidentStatus>([
  "under_review",
  "alleged",
  "reported",
  "confirmed",
  "denied",
  "retracted",
  "resolved",
]);
const incidentTypes = new Set<IncidentType>([
  "ransomware",
  "data_breach",
  "extortion",
  "business_email_compromise",
  "service_disruption",
  "supply_chain",
  "unauthorized_access",
  "malware",
  "unknown",
]);
const claimTypes = new Set<IncidentClaimType>([
  "attacker_allegation",
  "media_report",
  "researcher_report",
  "company_confirmation",
  "regulator_notice",
  "cert_notice",
  "provider_statement",
  "denial",
  "correction",
  "retraction",
]);
const sourceKinds = new Set<IncidentSourceKind>([
  "company",
  "regulator",
  "cert",
  "media",
  "research",
  "provider",
  "ransomware_metadata",
  "other",
]);
const linkStatuses = new Set<OrganizationLinkStatus>([
  "unresolved",
  "exact",
  "candidate",
  "review_required",
  "rejected",
]);

interface IncidentsPageProps {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}

export default async function IncidentsPage({ searchParams }: IncidentsPageProps) {
  const parameters = await searchParams;
  const query = first(parameters.q);
  const status = parseValue(first(parameters.status), statuses);
  const incidentType = parseValue(first(parameters.incident_type), incidentTypes);
  const claimType = parseValue(first(parameters.claim_type), claimTypes);
  const sourceKind = parseValue(first(parameters.source_kind), sourceKinds);
  const organizationLinkStatus = parseValue(
    first(parameters.organization_link_status),
    linkStatuses,
  );
  const officiallyConfirmed = parseBoolean(first(parameters.officially_confirmed));
  const historicalOnly = parseBoolean(first(parameters.historical_only));
  const page = await loadIncidentPage({
    query,
    status,
    incidentType,
    claimType,
    sourceKind,
    organizationLinkStatus,
    officiallyConfirmed,
    historicalOnly,
  });
  const summary = [
    { label: "Incidents", value: page.total },
    {
      label: "Confirmed on page",
      value: page.items.filter((item) => item.officially_confirmed).length,
    },
    {
      label: "Alleged on page",
      value: page.items.filter((item) => item.status === "alleged").length,
    },
    {
      label: "Review required",
      value: page.items.filter(
        (item) => item.organization_link_status === "review_required",
      ).length,
    },
  ] as const;

  return (
    <section className="page-stack">
      <div className="page-heading">
        <div>
          <p className="eyebrow">Public incident intelligence</p>
          <h1>Incidents, claims and official confirmation</h1>
          <p>
            Review persisted public incident metadata while keeping allegations,
            secondary reporting, official confirmation, denial, correction and
            retraction separate.
          </p>
        </div>
        <span className="live-label">Persisted data only</span>
      </div>

      <div className="incident-warning">
        No threat-actor interaction, negotiation portal, victim file, stolen data,
        credential or private communication is collected. An allegation never counts
        as an official confirmation.
      </div>

      <div className="summary-grid" aria-label="Incident summary">
        {summary.map((item) => (
          <article className="summary-card" key={item.label}>
            <span>{item.label}</span>
            <strong>{item.value}</strong>
          </article>
        ))}
      </div>

      <section className="panel" aria-labelledby="incident-title">
        <div className="panel-heading incident-heading">
          <div>
            <h2 id="incident-title">Reconciled incident records</h2>
            <p>{page.total} record(s), ordered by the latest persisted claim revision.</p>
          </div>
          <form className="filter-form incident-filters">
            <label>
              Search
              <input name="q" defaultValue={query} placeholder="Title, summary or key" />
            </label>
            <label>
              Status
              <select name="status" defaultValue={status ?? ""}>
                <option value="">All statuses</option>
                <option value="alleged">Alleged</option>
                <option value="reported">Reported</option>
                <option value="confirmed">Confirmed</option>
                <option value="denied">Denied</option>
                <option value="retracted">Retracted</option>
                <option value="under_review">Under review</option>
                <option value="resolved">Resolved</option>
              </select>
            </label>
            <label>
              Incident type
              <select name="incident_type" defaultValue={incidentType ?? ""}>
                <option value="">All types</option>
                <option value="ransomware">Ransomware</option>
                <option value="data_breach">Data breach</option>
                <option value="extortion">Extortion</option>
                <option value="business_email_compromise">Business email compromise</option>
                <option value="service_disruption">Service disruption</option>
                <option value="supply_chain">Supply chain</option>
                <option value="unauthorized_access">Unauthorized access</option>
                <option value="malware">Malware</option>
                <option value="unknown">Unknown</option>
              </select>
            </label>
            <label>
              Claim type
              <select name="claim_type" defaultValue={claimType ?? ""}>
                <option value="">All claims</option>
                <option value="attacker_allegation">Attacker allegation</option>
                <option value="media_report">Media report</option>
                <option value="researcher_report">Researcher report</option>
                <option value="company_confirmation">Company confirmation</option>
                <option value="regulator_notice">Regulator notice</option>
                <option value="cert_notice">CERT notice</option>
                <option value="provider_statement">Provider statement</option>
                <option value="denial">Denial</option>
                <option value="correction">Correction</option>
                <option value="retraction">Retraction</option>
              </select>
            </label>
            <label>
              Source kind
              <select name="source_kind" defaultValue={sourceKind ?? ""}>
                <option value="">All sources</option>
                <option value="company">Company</option>
                <option value="regulator">Regulator</option>
                <option value="cert">CERT</option>
                <option value="media">Media</option>
                <option value="research">Research</option>
                <option value="provider">Provider</option>
                <option value="ransomware_metadata">Ransomware metadata</option>
                <option value="other">Other</option>
              </select>
            </label>
            <label>
              Organization link
              <select
                name="organization_link_status"
                defaultValue={organizationLinkStatus ?? ""}
              >
                <option value="">All link states</option>
                <option value="exact">Exact</option>
                <option value="review_required">Review required</option>
                <option value="candidate">Candidate</option>
                <option value="unresolved">Unresolved</option>
                <option value="rejected">Rejected</option>
              </select>
            </label>
            <label>
              Official confirmation
              <select
                name="officially_confirmed"
                defaultValue={formatBoolean(officiallyConfirmed)}
              >
                <option value="">Any</option>
                <option value="true">Confirmed</option>
                <option value="false">Not confirmed</option>
              </select>
            </label>
            <label>
              Historical backfill
              <select
                name="historical_only"
                defaultValue={formatBoolean(historicalOnly)}
              >
                <option value="">Any</option>
                <option value="true">Historical only</option>
                <option value="false">Current-capable</option>
              </select>
            </label>
            <button type="submit">Apply</button>
          </form>
        </div>
        {page.items.length > 0 ? (
          <IncidentTable incidents={page.items} />
        ) : (
          <div className="empty-state">
            <h3>No matching incident record</h3>
            <p>These filters search persisted data and never launch source collection.</p>
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

function parseBoolean(value: string): boolean | undefined {
  if (value === "true") {
    return true;
  }
  if (value === "false") {
    return false;
  }
  return undefined;
}

function formatBoolean(value: boolean | undefined): string {
  return value === undefined ? "" : String(value);
}
