import { loadThreatIndicatorPage } from "@/features/threat-telemetry/api";
import { IndicatorFilters } from "@/features/threat-telemetry/indicator-filters";
import { IndicatorTable } from "@/features/threat-telemetry/indicator-table";
import type {
  IndicatorState,
  IndicatorType,
  SensorScope,
  TelemetrySourceKind,
} from "@/features/threat-telemetry/types";

const indicatorTypes = new Set<IndicatorType>([
  "ipv4",
  "ipv6",
  "domain",
  "url",
  "file_hash",
  "certificate_fingerprint",
  "email_address",
]);
const states = new Set<IndicatorState>([
  "malicious",
  "suspicious",
  "historical",
  "expired",
  "sinkholed",
  "benign",
  "shared_infrastructure",
  "unknown",
  "retracted",
]);
const sourceKinds = new Set<TelemetrySourceKind>([
  "stix_taxii",
  "phishing_feed",
  "passive_dns",
  "malware_metadata",
  "certificate_feed",
  "provider",
  "other",
]);
const sensorScopes = new Set<SensorScope>([
  "global",
  "regional",
  "sector",
  "customer_tenant",
  "provider_aggregate",
  "unknown",
]);

interface ThreatIntelligencePageProps {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}

export default async function ThreatIntelligencePage({
  searchParams,
}: ThreatIntelligencePageProps) {
  const parameters = await searchParams;
  const query = first(parameters.q);
  const indicatorType = parseValue(
    first(parameters.indicator_type),
    indicatorTypes,
  );
  const state = parseValue(first(parameters.state), states);
  const sourceKind = parseValue(first(parameters.source_kind), sourceKinds);
  const sensorScope = parseValue(first(parameters.sensor_scope), sensorScopes);
  const active = parseBoolean(first(parameters.active));
  const sharedInfrastructure = parseBoolean(
    first(parameters.shared_infrastructure),
  );
  const historicalOnly = parseBoolean(first(parameters.historical_only));
  const hasConflict = parseBoolean(first(parameters.has_conflict));
  const page = await loadThreatIndicatorPage({
    query,
    indicatorType,
    state,
    sourceKind,
    sensorScope,
    active,
    sharedInfrastructure,
    historicalOnly,
    hasConflict,
  });
  const summary = [
    { label: "Indicators", value: page.total },
    {
      label: "High-risk state",
      value: page.items.filter((item) => item.state === "malicious").length,
    },
    {
      label: "Conflicts",
      value: page.items.filter((item) => item.has_conflict).length,
    },
    {
      label: "Shared infrastructure",
      value: page.items.filter((item) => item.shared_infrastructure).length,
    },
  ] as const;

  return (
    <section className="page-stack">
      <div className="page-heading">
        <div>
          <p className="eyebrow">Defensive telemetry</p>
          <h1>Indicators, infrastructure and campaign context</h1>
          <p>
            Review persisted metadata with source scope, classification history,
            expiration and shared-infrastructure context.
          </p>
        </div>
        <span className="live-label">Persisted data only</span>
      </div>

      <div className="threat-warning">
        Global telemetry does not prove that a named organization is affected. This
        workspace performs no active connection, scanning or binary collection.
      </div>

      <div className="summary-grid" aria-label="Telemetry summary">
        {summary.map((item) => (
          <article className="summary-card" key={item.label}>
            <span>{item.label}</span>
            <strong>{item.value}</strong>
          </article>
        ))}
      </div>

      <section className="panel" aria-labelledby="threat-indicator-title">
        <div className="panel-heading threat-heading">
          <div>
            <h2 id="threat-indicator-title">Canonical indicators</h2>
            <p>{page.total} record(s), ordered by the latest source revision.</p>
          </div>
          <IndicatorFilters
            query={query}
            indicatorType={indicatorType}
            state={state}
            sourceKind={sourceKind}
            sensorScope={sensorScope}
            active={active}
            sharedInfrastructure={sharedInfrastructure}
            historicalOnly={historicalOnly}
            hasConflict={hasConflict}
          />
        </div>
        {page.items.length > 0 ? (
          <IndicatorTable indicators={page.items} />
        ) : (
          <div className="empty-state">
            <h3>No matching indicator</h3>
            <p>These filters never initiate collection or contact an indicator.</p>
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
