import { loadPassiveAssetPage } from "@/features/passive-exposure/api";
import { PassiveAssetFilters } from "@/features/passive-exposure/passive-asset-filters";
import { PassiveAssetTable } from "@/features/passive-exposure/passive-asset-table";
import type {
  AttributionRisk,
  OrganizationLinkStatus,
  PassiveAssetKind,
  PassiveObservationState,
} from "@/features/passive-exposure/types";

const assetKinds = new Set<PassiveAssetKind>([
  "domain",
  "hostname",
  "ipv4",
  "ipv6",
  "certificate",
  "asn",
  "cloud_resource",
]);
const states = new Set<PassiveObservationState>([
  "current",
  "historical",
  "expired",
  "corrected",
  "retracted",
  "deleted",
  "unknown",
]);
const linkStatuses = new Set<OrganizationLinkStatus>([
  "unresolved",
  "exact",
  "candidate",
  "review_required",
  "rejected",
]);
const attributionRisks = new Set<AttributionRisk>([
  "shared_hosting",
  "cdn",
  "reseller",
  "subsidiary",
  "abandoned_domain",
  "reassigned_address",
]);

interface PassiveExposurePageProps {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}

export default async function PassiveExposurePage({
  searchParams,
}: PassiveExposurePageProps) {
  const parameters = await searchParams;
  const query = first(parameters.q);
  const assetKind = parseValue(first(parameters.asset_kind), assetKinds);
  const state = parseValue(first(parameters.state), states);
  const organizationLinkStatus = parseValue(
    first(parameters.organization_link_status),
    linkStatuses,
  );
  const attributionRisk = parseValue(
    first(parameters.attribution_risk),
    attributionRisks,
  );
  const organizationId = first(parameters.organization_id);
  const active = parseBoolean(first(parameters.active));
  const historicalOnly = parseBoolean(first(parameters.historical_only));
  const hasConflict = parseBoolean(first(parameters.has_conflict));
  const page = await loadPassiveAssetPage({
    query,
    assetKind,
    state,
    organizationLinkStatus,
    attributionRisk,
    organizationId: organizationId || undefined,
    active,
    historicalOnly,
    hasConflict,
  });
  const summary = [
    { label: "Passive assets", value: page.total },
    {
      label: "Exact links",
      value: page.items.filter(
        (item) => item.organization_link_status === "exact",
      ).length,
    },
    {
      label: "Review required",
      value: page.items.filter(
        (item) => item.organization_link_status === "review_required",
      ).length,
    },
    {
      label: "Attribution risks",
      value: page.items.filter((item) => item.attribution_risks.length > 0)
        .length,
    },
  ] as const;

  return (
    <section className="page-stack">
      <div className="page-heading">
        <div>
          <p className="eyebrow">Passive exposure and technographics</p>
          <h1>Assets, technologies and attribution evidence</h1>
          <p>
            Review persisted passive observations, source history and organization
            attribution risks without probing an asset or asserting exposure.
          </p>
        </div>
        <span className="live-label">Persisted metadata only</span>
      </div>

      <div className="passive-warning">
        A passive observation is not proof that a product is vulnerable, a system is
        exposed, or an organization is compromised. This workspace performs no scan,
        authentication, service connection or exploit validation.
      </div>

      <div className="summary-grid" aria-label="Passive exposure summary">
        {summary.map((item) => (
          <article className="summary-card" key={item.label}>
            <span>{item.label}</span>
            <strong>{item.value}</strong>
          </article>
        ))}
      </div>

      <section className="panel" aria-labelledby="passive-assets-title">
        <div className="panel-heading passive-heading">
          <div>
            <h2 id="passive-assets-title">Canonical passive assets</h2>
            <p>{page.total} record(s), ordered by the latest source revision.</p>
          </div>
          <PassiveAssetFilters
            query={query}
            assetKind={assetKind}
            state={state}
            organizationLinkStatus={organizationLinkStatus}
            attributionRisk={attributionRisk}
            organizationId={organizationId}
            active={active}
            historicalOnly={historicalOnly}
            hasConflict={hasConflict}
          />
        </div>
        {page.items.length > 0 ? (
          <PassiveAssetTable assets={page.items} />
        ) : (
          <div className="empty-state">
            <h3>No matching passive asset</h3>
            <p>Changing filters never initiates collection or probes an asset.</p>
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
