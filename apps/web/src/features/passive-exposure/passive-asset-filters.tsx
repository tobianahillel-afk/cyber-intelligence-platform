import type {
  AttributionRisk,
  OrganizationLinkStatus,
  PassiveAssetKind,
  PassiveObservationState,
} from "./types";

interface PassiveAssetFiltersProps {
  query: string;
  assetKind: PassiveAssetKind | undefined;
  state: PassiveObservationState | undefined;
  organizationLinkStatus: OrganizationLinkStatus | undefined;
  attributionRisk: AttributionRisk | undefined;
  organizationId: string;
  active: boolean | undefined;
  historicalOnly: boolean | undefined;
  hasConflict: boolean | undefined;
}

export function PassiveAssetFilters(props: PassiveAssetFiltersProps) {
  return (
    <form className="filter-form passive-filters">
      <label>
        Search
        <input
          name="q"
          defaultValue={props.query}
          placeholder="Asset value or canonical key"
        />
      </label>
      <label>
        Asset type
        <select name="asset_kind" defaultValue={props.assetKind ?? ""}>
          <option value="">All types</option>
          <option value="domain">Domain</option>
          <option value="hostname">Hostname</option>
          <option value="ipv4">IPv4</option>
          <option value="ipv6">IPv6</option>
          <option value="certificate">Certificate</option>
          <option value="asn">ASN</option>
          <option value="cloud_resource">Cloud resource</option>
        </select>
      </label>
      <label>
        Current state
        <select name="state" defaultValue={props.state ?? ""}>
          <option value="">All states</option>
          <option value="current">Current</option>
          <option value="historical">Historical</option>
          <option value="expired">Expired</option>
          <option value="corrected">Corrected</option>
          <option value="retracted">Retracted</option>
          <option value="deleted">Deleted</option>
          <option value="unknown">Unknown</option>
        </select>
      </label>
      <label>
        Organization link
        <select
          name="organization_link_status"
          defaultValue={props.organizationLinkStatus ?? ""}
        >
          <option value="">All link states</option>
          <option value="unresolved">Unresolved</option>
          <option value="exact">Exact</option>
          <option value="candidate">Candidate</option>
          <option value="review_required">Review required</option>
          <option value="rejected">Rejected</option>
        </select>
      </label>
      <label>
        Attribution risk
        <select
          name="attribution_risk"
          defaultValue={props.attributionRisk ?? ""}
        >
          <option value="">All risks</option>
          <option value="shared_hosting">Shared hosting</option>
          <option value="cdn">CDN</option>
          <option value="reseller">Reseller</option>
          <option value="subsidiary">Subsidiary</option>
          <option value="abandoned_domain">Abandoned domain</option>
          <option value="reassigned_address">Reassigned address</option>
        </select>
      </label>
      <label>
        Organization ID
        <input
          name="organization_id"
          defaultValue={props.organizationId}
          placeholder="Canonical UUID"
        />
      </label>
      <BooleanFilter name="active" label="Active" value={props.active} />
      <BooleanFilter
        name="historical_only"
        label="Historical only"
        value={props.historicalOnly}
      />
      <BooleanFilter
        name="has_conflict"
        label="Conflicting sources"
        value={props.hasConflict}
      />
      <button type="submit">Apply</button>
    </form>
  );
}

interface BooleanFilterProps {
  name: string;
  label: string;
  value: boolean | undefined;
}

function BooleanFilter({ name, label, value }: BooleanFilterProps) {
  return (
    <label>
      {label}
      <select name={name} defaultValue={formatBoolean(value)}>
        <option value="">Any</option>
        <option value="true">Yes</option>
        <option value="false">No</option>
      </select>
    </label>
  );
}

function formatBoolean(value: boolean | undefined): string {
  return value === undefined ? "" : String(value);
}
