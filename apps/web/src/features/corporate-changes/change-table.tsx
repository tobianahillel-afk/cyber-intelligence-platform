import Link from "next/link";

import type { ChangeSummary } from "./types";

interface ChangeTableProps {
  changes: readonly ChangeSummary[];
}

export function ChangeTable({ changes }: ChangeTableProps) {
  return (
    <div className="change-table-wrap">
      <table className="change-table">
        <thead>
          <tr>
            <th>Material change</th>
            <th>Status</th>
            <th>Evidence</th>
            <th>Organization</th>
            <th>Timeline</th>
          </tr>
        </thead>
        <tbody>
          {changes.map((change) => (
            <tr key={change.id}>
              <td>
                <Link
                  className="change-link"
                  href={`/corporate-changes/${encodeURIComponent(change.event_key)}`}
                >
                  {change.title}
                </Link>
                <strong>{readable(change.event_type)}</strong>
                <span className="change-muted">{change.excerpt}</span>
              </td>
              <td>
                <span className={`change-status change-status-${change.status}`}>
                  {readable(change.status)}
                </span>
                <span className="change-muted">
                  {change.officially_confirmed
                    ? "Official evidence present"
                    : "No official confirmation"}
                </span>
              </td>
              <td>
                <strong>{change.claim_count} current claim(s)</strong>
                <span className="change-muted">
                  {change.independent_source_count} independent source(s)
                </span>
                <div className="change-badges">
                  {change.has_dispute ? <span>Dispute</span> : null}
                  {change.has_correction ? <span>Correction</span> : null}
                  {change.has_retraction ? <span>Retraction</span> : null}
                  {change.historical_only ? <span>Historical</span> : null}
                </div>
              </td>
              <td>
                <strong>{readable(change.organization_link_status)}</strong>
                <span className="change-muted">
                  {change.organization_id ?? "No resolved organization ID"}
                </span>
              </td>
              <td>
                <strong>{formatTimestamp(change.event_at)}</strong>
                <span className="change-muted">
                  Updated {formatTimestamp(change.last_updated_at)}
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
