import type { OpportunityListItem } from "./types";

interface OpportunityTableProps {
  opportunities: readonly OpportunityListItem[];
}

function formatLabel(value: string) {
  return value.replaceAll("_", " ");
}

export function OpportunityTable({ opportunities }: OpportunityTableProps) {
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
            <th scope="col">Roles</th>
            <th scope="col">Next action</th>
          </tr>
        </thead>
        <tbody>
          {opportunities.map((opportunity) => (
            <tr key={opportunity.id}>
              <td>
                <strong>{opportunity.score}</strong>
                <span className="cell-secondary">{opportunity.confidence}% confidence</span>
              </td>
              <td>
                <strong>{opportunity.organization}</strong>
                <span className="cell-secondary">{opportunity.country}</span>
              </td>
              <td>
                <span className="badge">{formatLabel(opportunity.family)}</span>
                <span className="cell-secondary">{opportunity.recommendedOffer}</span>
              </td>
              <td>
                {opportunity.trigger}
                {opportunity.warning ? (
                  <span className="warning">{opportunity.warning}</span>
                ) : null}
              </td>
              <td>{opportunity.evidenceAge}</td>
              <td>{opportunity.relevantRoles.join(", ")}</td>
              <td>
                <span className="badge badge-muted">{formatLabel(opportunity.state)}</span>
                <span className="cell-secondary">{opportunity.nextAction}</span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
