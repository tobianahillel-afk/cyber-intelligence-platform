import Link from "next/link";

import type { OpportunityListItem } from "./types";

interface OpportunityTableProps {
  opportunities: readonly OpportunityListItem[];
  now: Date;
}

function formatLabel(value: string) {
  return value.replaceAll("_", " ");
}

function formatAge(value: string, now: Date) {
  const ageMs = Math.max(now.getTime() - new Date(value).getTime(), 0);
  const minutes = Math.floor(ageMs / 60_000);
  if (minutes < 60) return `${minutes} min`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours} h`;
  return `${Math.floor(hours / 24)} d`;
}

export function OpportunityTable({ opportunities, now }: OpportunityTableProps) {
  return (
    <div className="table-wrapper">
      <table>
        <caption className="sr-only">Current commercial cybersecurity opportunities</caption>
        <thead>
          <tr>
            <th scope="col">Priority</th>
            <th scope="col">Organization</th>
            <th scope="col">Opportunity</th>
            <th scope="col">Trigger</th>
            <th scope="col">Freshness</th>
            <th scope="col">Evidence</th>
            <th scope="col">Review</th>
          </tr>
        </thead>
        <tbody>
          {opportunities.map((opportunity) => (
            <tr key={opportunity.id}>
              <td>
                <strong>{Math.round(opportunity.score)}</strong>
                <span className="cell-secondary">
                  {Math.round(opportunity.confidence * 100)}% confidence
                </span>
              </td>
              <td>
                <Link href={`/opportunities/${opportunity.id}`}>
                  <strong>{opportunity.organization}</strong>
                </Link>
                <span className="cell-secondary">{opportunity.country ?? "Country unknown"}</span>
              </td>
              <td>
                <span className="badge">{formatLabel(opportunity.family)}</span>
                <span className="cell-secondary">{opportunity.recommended_offer}</span>
              </td>
              <td>{opportunity.trigger}</td>
              <td>
                {formatAge(opportunity.last_evidence_at, now)}
                <span className="cell-secondary">
                  Updated {formatAge(opportunity.updated_at, now)} ago
                </span>
              </td>
              <td>
                <span className={`badge badge-${opportunity.data_quality}`}>
                  {opportunity.data_quality}
                </span>
                <span className="cell-secondary">
                  {opportunity.evidence_count} item(s)
                </span>
              </td>
              <td>
                <span className="badge badge-muted">{formatLabel(opportunity.state)}</span>
                <span className="cell-secondary">{opportunity.next_action}</span>
                <Link className="text-link" href={`/opportunities/${opportunity.id}`}>
                  Review details
                </Link>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
