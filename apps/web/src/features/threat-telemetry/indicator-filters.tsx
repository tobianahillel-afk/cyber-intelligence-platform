import type {
  IndicatorState,
  IndicatorType,
  SensorScope,
  TelemetrySourceKind,
} from "./types";

interface IndicatorFiltersProps {
  query: string;
  indicatorType: IndicatorType | undefined;
  state: IndicatorState | undefined;
  sourceKind: TelemetrySourceKind | undefined;
  sensorScope: SensorScope | undefined;
  active: boolean | undefined;
  sharedInfrastructure: boolean | undefined;
  historicalOnly: boolean | undefined;
  hasConflict: boolean | undefined;
}

export function IndicatorFilters(props: IndicatorFiltersProps) {
  return (
    <form className="filter-form threat-filters">
      <label>
        Search
        <input
          name="q"
          defaultValue={props.query}
          placeholder="Indicator value or canonical key"
        />
      </label>
      <label>
        Indicator type
        <select name="indicator_type" defaultValue={props.indicatorType ?? ""}>
          <option value="">All types</option>
          <option value="ipv4">IPv4</option>
          <option value="ipv6">IPv6</option>
          <option value="domain">Domain</option>
          <option value="url">URL</option>
          <option value="file_hash">File hash</option>
          <option value="certificate_fingerprint">Certificate</option>
          <option value="email_address">Email address</option>
        </select>
      </label>
      <label>
        Current state
        <select name="state" defaultValue={props.state ?? ""}>
          <option value="">All states</option>
          <option value="malicious">Malicious</option>
          <option value="suspicious">Suspicious</option>
          <option value="benign">Benign</option>
          <option value="sinkholed">Sinkholed</option>
          <option value="shared_infrastructure">Shared infrastructure</option>
          <option value="historical">Historical</option>
          <option value="expired">Expired</option>
          <option value="retracted">Retracted</option>
          <option value="unknown">Unknown</option>
        </select>
      </label>
      <label>
        Source kind
        <select name="source_kind" defaultValue={props.sourceKind ?? ""}>
          <option value="">All sources</option>
          <option value="stix_taxii">STIX/TAXII</option>
          <option value="phishing_feed">Phishing feed</option>
          <option value="passive_dns">Passive DNS</option>
          <option value="malware_metadata">File metadata</option>
          <option value="certificate_feed">Certificate feed</option>
          <option value="provider">Provider</option>
          <option value="other">Other</option>
        </select>
      </label>
      <label>
        Sensor scope
        <select name="sensor_scope" defaultValue={props.sensorScope ?? ""}>
          <option value="">All scopes</option>
          <option value="global">Global</option>
          <option value="regional">Regional</option>
          <option value="sector">Sector</option>
          <option value="customer_tenant">Customer tenant</option>
          <option value="provider_aggregate">Provider aggregate</option>
          <option value="unknown">Unknown</option>
        </select>
      </label>
      <BooleanFilter name="active" label="Active" value={props.active} />
      <BooleanFilter
        name="shared_infrastructure"
        label="Shared infrastructure"
        value={props.sharedInfrastructure}
      />
      <BooleanFilter
        name="historical_only"
        label="Historical only"
        value={props.historicalOnly}
      />
      <BooleanFilter
        name="has_conflict"
        label="Conflicting states"
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
