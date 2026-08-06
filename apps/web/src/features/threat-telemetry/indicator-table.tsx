import Link from "next/link";

import type { ThreatIndicatorSummary } from "./types";

interface IndicatorTableProps {
  indicators: readonly ThreatIndicatorSummary[];
}

export function IndicatorTable({ indicators }: IndicatorTableProps) {
  return (
    <div className="threat-table-wrap">
      <table className="threat-table">
        <thead>
          <tr>
            <th>Indicator</th>
            <th>Current state</th>
            <th>Evidence</th>
            <th>Temporal scope</th>
            <th>Safety context</th>
          </tr>
        </thead>
        <tbody>
          {indicators.map((indicator) => (
            <tr key={indicator.id}>
              <td>
                <Link
                  className="threat-link"
                  href={`/threat-intelligence/${indicator.id}`}
                >
                  {indicator.indicator_value}
                </Link>
                <strong>{readable(indicator.indicator_type)}</strong>
                <span className="threat-muted">{indicator.indicator_key}</span>
              </td>
              <td>
                <span className={`threat-state threat-state-${indicator.state}`}>
                  {readable(indicator.state)}
                </span>
                <div className="threat-badges">
                  {indicator.observed_states.map((state) => (
                    <span key={state}>{readable(state)}</span>
                  ))}
                </div>
              </td>
              <td>
                <strong>{indicator.source_count} source(s)</strong>
                <span className="threat-muted">
                  {indicator.independent_source_count} independent positive group(s)
                </span>
                {indicator.has_conflict ? (
                  <span className="threat-conflict">Conflicting classifications</span>
                ) : null}
              </td>
              <td>
                <strong>Last seen {formatTimestamp(indicator.last_seen_at)}</strong>
                <span className="threat-muted">
                  First seen {formatTimestamp(indicator.first_seen_at)}
                </span>
                <span className="threat-muted">
                  Expires {formatTimestamp(indicator.expires_at)}
                </span>
              </td>
              <td>
                <strong>
                  {indicator.shared_infrastructure
                    ? "Shared infrastructure"
                    : "No shared flag"}
                </strong>
                <span className="threat-muted">
                  {indicator.historical_only ? "Historical only" : "Current-capable"}
                </span>
                <span className="threat-muted">
                  {indicator.active ? "Active source state" : "Inactive source state"}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function readable(value: string): string {
  return value
    .replaceAll("_", " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

export function formatTimestamp(value: string | null): string {
  if (!value) {
    return "Unknown";
  }
  return new Intl.DateTimeFormat("en-GB", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    timeZone: "UTC",
  }).format(new Date(value));
}
