import Link from "next/link";

import type { PassiveAssetSummary } from "./types";

interface PassiveAssetTableProps {
  assets: readonly PassiveAssetSummary[];
}

export function PassiveAssetTable({ assets }: PassiveAssetTableProps) {
  return (
    <div className="passive-table-wrap">
      <table className="passive-table">
        <thead>
          <tr>
            <th>Passive asset</th>
            <th>Observation state</th>
            <th>Organization attribution</th>
            <th>Evidence timeline</th>
            <th>Safety boundary</th>
          </tr>
        </thead>
        <tbody>
          {assets.map((asset) => (
            <tr key={asset.id}>
              <td>
                <Link
                  className="passive-link"
                  href={`/passive-exposure/${asset.id}`}
                >
                  {asset.asset_value}
                </Link>
                <strong>{readable(asset.asset_kind)}</strong>
                <span className="passive-muted">{asset.asset_key}</span>
              </td>
              <td>
                <span className={`passive-state passive-state-${asset.state}`}>
                  {readable(asset.state)}
                </span>
                <div className="passive-badges">
                  {asset.observed_states.map((state) => (
                    <span key={state}>{readable(state)}</span>
                  ))}
                </div>
                {asset.has_conflict ? (
                  <span className="passive-conflict">Conflicting sources</span>
                ) : null}
              </td>
              <td>
                <strong>{readable(asset.organization_link_status)}</strong>
                <span className="passive-muted">
                  {asset.exact_organization_id
                    ? `Exact: ${asset.exact_organization_id}`
                    : `${asset.candidate_organization_ids.length} candidate(s)`}
                </span>
                <div className="passive-badges">
                  {asset.attribution_risks.map((risk) => (
                    <span key={risk}>{readable(risk)}</span>
                  ))}
                </div>
              </td>
              <td>
                <strong>Last seen {formatTimestamp(asset.last_seen_at)}</strong>
                <span className="passive-muted">
                  First seen {formatTimestamp(asset.first_seen_at)}
                </span>
                <span className="passive-muted">
                  {asset.source_count} source(s), {asset.independent_source_count}{" "}
                  independent group(s)
                </span>
              </td>
              <td>
                <strong>Exposure not assessed</strong>
                <span className="passive-muted">
                  {asset.active ? "Current-capable metadata" : "Inactive metadata"}
                </span>
                <span className="passive-muted">
                  {asset.historical_only ? "Historical only" : "Not historical only"}
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
