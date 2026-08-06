import Link from "next/link";

import type { IncidentSummary } from "./types";

interface IncidentTableProps {
  incidents: readonly IncidentSummary[];
}

export function IncidentTable({ incidents }: IncidentTableProps) {
  return (
    <div className="incident-table-wrap">
      <table className="incident-table">
        <thead>
          <tr>
            <th>Incident</th>
            <th>Resolution</th>
            <th>Evidence</th>
            <th>Organization link</th>
            <th>Last change</th>
          </tr>
        </thead>
        <tbody>
          {incidents.map((incident) => (
            <tr key={incident.id}>
              <td>
                <Link
                  className="incident-link"
                  href={`/incidents/${encodeURIComponent(incident.incident_key)}`}
                >
                  {incident.title}
                </Link>
                <strong>{readable(incident.incident_type)}</strong>
                <span className="incident-muted">{incident.summary}</span>
              </td>
              <td>
                <span className={`incident-status incident-status-${incident.status}`}>
                  {readable(incident.status)}
                </span>
                <span className="incident-muted">
                  {incident.officially_confirmed
                    ? "Official confirmation present"
                    : "No official confirmation"}
                </span>
              </td>
              <td>
                <strong>{incident.claim_count} claim(s)</strong>
                <span className="incident-muted">
                  {incident.independent_source_count} independent source(s)
                </span>
                <div className="incident-badges">
                  {incident.has_denial ? <span>Denial</span> : null}
                  {incident.has_retraction ? <span>Retraction</span> : null}
                  {incident.historical_only ? <span>Historical</span> : null}
                </div>
              </td>
              <td>
                <strong>{readable(incident.organization_link_status)}</strong>
                <span className="incident-muted">
                  {incident.organization_id ?? "No resolved organization ID"}
                </span>
              </td>
              <td>
                {formatTimestamp(incident.last_updated_at)}
                <span className="incident-muted">
                  First published {formatTimestamp(incident.first_published_at)}
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
