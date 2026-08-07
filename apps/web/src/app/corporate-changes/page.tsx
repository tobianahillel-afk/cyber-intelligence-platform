import { loadChangePage } from "@/features/corporate-changes/api";
import { ChangeTable } from "@/features/corporate-changes/change-table";
import type {
  ChangeClaimType,
  ChangeEventStatus,
  ChangeEventType,
  ChangeSourceKind,
  OrganizationLinkStatus,
} from "@/features/corporate-changes/types";

const statuses = new Set<ChangeEventStatus>([
  "under_review",
  "speculative",
  "reported",
  "confirmed",
  "disputed",
  "corrected",
  "retracted",
  "stale",
]);
const eventTypes = new Set<ChangeEventType>([
  "acquisition",
  "leadership",
  "funding",
  "restructuring",
  "geographic_expansion",
  "cloud_digital_program",
  "regulatory_action",
  "breach",
  "audit",
  "certification",
  "security_commitment",
  "other",
]);
const claimTypes = new Set<ChangeClaimType>([
  "confirmation",
  "report",
  "speculation",
  "dispute",
  "correction",
  "retraction",
]);
const sourceKinds = new Set<ChangeSourceKind>([
  "official_filing",
  "regulator",
  "company",
  "media",
  "analyst",
  "other",
]);
const linkStatuses = new Set<OrganizationLinkStatus>([
  "unresolved",
  "exact",
  "candidate",
  "review_required",
  "rejected",
]);

interface CorporateChangesPageProps {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}

export default async function CorporateChangesPage({
  searchParams,
}: CorporateChangesPageProps) {
  const parameters = await searchParams;
  const query = first(parameters.q);
  const status = parseValue(first(parameters.status), statuses);
  const eventType = parseValue(first(parameters.event_type), eventTypes);
  const claimType = parseValue(first(parameters.claim_type), claimTypes);
  const sourceKind = parseValue(first(parameters.source_kind), sourceKinds);
  const organizationLinkStatus = parseValue(
    first(parameters.organization_link_status),
    linkStatuses,
  );
  const officiallyConfirmed = parseBoolean(first(parameters.officially_confirmed));
  const historicalOnly = parseBoolean(first(parameters.historical_only));
  const page = await loadChangePage({
    query,
    status,
    eventType,
    claimType,
    sourceKind,
    organizationLinkStatus,
    officiallyConfirmed,
    historicalOnly,
  });
  const summary = [
    { label: "Changes", value: page.total },
    {
      label: "Confirmed on page",
      value: page.items.filter((item) => item.officially_confirmed).length,
    },
    {
      label: "Speculative on page",
      value: page.items.filter((item) => item.status === "speculative").length,
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
          <p className="eyebrow">Corporate and regulatory change intelligence</p>
          <h1>Material public changes</h1>
          <p>
            Review persisted disclosures and reporting while keeping official
            confirmation, independent reporting, syndication, speculation,
            corrections, retractions and service mappings distinct.
          </p>
        </div>
        <span className="live-label">Persisted data only</span>
      </div>

      <div className="change-warning">
        A public mention is not independent corroboration, official confirmation,
        a service need, an opportunity, or authorization to contact an organization.
      </div>

      <div className="summary-grid" aria-label="Corporate change summary">
        {summary.map((item) => (
          <article className="summary-card" key={item.label}>
            <span>{item.label}</span>
            <strong>{item.value}</strong>
          </article>
        ))}
      </div>

      <section className="panel" aria-labelledby="change-title">
        <div className="panel-heading change-heading">
          <div>
            <h2 id="change-title">Reconciled change events</h2>
            <p>{page.total} event(s), ordered by latest persisted evidence.</p>
          </div>
          <form className="filter-form change-filters">
            <label>
              Search
              <input name="q" defaultValue={query} placeholder="Title, excerpt or key" />
            </label>
            <label>
              Status
              <select name="status" defaultValue={status ?? ""}>
                <option value="">All statuses</option>
                {[...statuses].map((value) => (
                  <option key={value} value={value}>{readable(value)}</option>
                ))}
              </select>
            </label>
            <label>
              Event type
              <select name="event_type" defaultValue={eventType ?? ""}>
                <option value="">All event types</option>
                {[...eventTypes].map((value) => (
                  <option key={value} value={value}>{readable(value)}</option>
                ))}
              </select>
            </label>
            <label>
              Claim type
              <select name="claim_type" defaultValue={claimType ?? ""}>
                <option value="">All claim types</option>
                {[...claimTypes].map((value) => (
                  <option key={value} value={value}>{readable(value)}</option>
                ))}
              </select>
            </label>
            <label>
              Source kind
              <select name="source_kind" defaultValue={sourceKind ?? ""}>
                <option value="">All source kinds</option>
                {[...sourceKinds].map((value) => (
                  <option key={value} value={value}>{readable(value)}</option>
                ))}
              </select>
            </label>
            <label>
              Organization link
              <select
                name="organization_link_status"
                defaultValue={organizationLinkStatus ?? ""}
              >
                <option value="">All link states</option>
                {[...linkStatuses].map((value) => (
                  <option key={value} value={value}>{readable(value)}</option>
                ))}
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
          <ChangeTable changes={page.items} />
        ) : (
          <div className="empty-state">
            <h3>No matching change event</h3>
            <p>These filters search persisted evidence and never launch collection.</p>
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
  if (value === "true") return true;
  if (value === "false") return false;
  return undefined;
}

function formatBoolean(value: boolean | undefined): string {
  return value === undefined ? "" : String(value);
}

function readable(value: string): string {
  return value.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}
