import Link from "next/link";

import type { RelationshipSummary } from "./types";
import { readable } from "./relationship-filters";

interface RelationshipTableProps {
  relationships: readonly RelationshipSummary[];
}

export function RelationshipTable({ relationships }: RelationshipTableProps) {
  return (
    <div className="relationship-table-wrap">
      <table className="relationship-table">
        <thead>
          <tr>
            <th>Relationship</th>
            <th>State</th>
            <th>Evidence</th>
            <th>Identity</th>
            <th>Timeline</th>
          </tr>
        </thead>
        <tbody>
          {relationships.map((relationship) => (
            <tr key={relationship.id}>
              <td>
                <Link
                  className="relationship-link"
                  href={`/relationships/${encodeURIComponent(relationship.relationship_key)}`}
                >
                  {displayName(relationship.source_name)} → {displayName(relationship.target_name)}
                </Link>
                <strong>{readable(relationship.role)}</strong>
                <span className="relationship-muted">Directed relationship</span>
              </td>
              <td>
                <span className={`relationship-status relationship-status-${relationship.status}`}>
                  {readable(relationship.status)}
                </span>
                <span className="relationship-muted">
                  {relationship.contract_backed_current
                    ? "Current contract evidence"
                    : "No current contract conclusion"}
                </span>
              </td>
              <td>
                <strong>{readable(relationship.strongest_evidence_class)}</strong>
                <span className="relationship-muted">
                  {relationship.evidence_count} evidence revision(s) · {relationship.independent_source_count} source(s)
                </span>
                <div className="relationship-badges">
                  {relationship.has_role_conflict ? <span>Role conflict</span> : null}
                  {relationship.has_dispute ? <span>Dispute</span> : null}
                  {relationship.has_correction ? <span>Correction</span> : null}
                  {relationship.has_retraction ? <span>Retraction</span> : null}
                  {relationship.historical_only ? <span>Historical</span> : null}
                </div>
              </td>
              <td>
                <strong>
                  {readable(relationship.source_link_status)} → {readable(relationship.target_link_status)}
                </strong>
                <span className="relationship-muted">
                  {relationship.source_organization_id ?? "unresolved"} → {relationship.target_organization_id ?? "unresolved"}
                </span>
              </td>
              <td>
                <strong>{formatTimestamp(relationship.valid_from)}</strong>
                <span className="relationship-muted">
                  Until {formatTimestamp(relationship.valid_until)}
                </span>
                <span className="relationship-muted">
                  Updated {formatTimestamp(relationship.last_updated_at)}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function displayName(value: string | null): string {
  return value ?? "Unresolved organization";
}

export function formatTimestamp(value: string | null): string {
  if (!value) return "Unknown";
  return new Intl.DateTimeFormat("en-GB", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    timeZone: "UTC",
  }).format(new Date(value));
}
