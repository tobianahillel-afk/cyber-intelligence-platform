import Link from "next/link";

import type { ProfessionalPerson } from "./types";

interface ProfessionalPersonTableProps {
  people: ProfessionalPerson[];
}

export function ProfessionalPersonTable({ people }: ProfessionalPersonTableProps) {
  return (
    <div className="professional-table-wrap">
      <table className="professional-table">
        <thead>
          <tr>
            <th>Professional reference</th>
            <th>Current context</th>
            <th>Review</th>
            <th>Processing</th>
            <th>Freshness</th>
          </tr>
        </thead>
        <tbody>
          {people.map((person) => (
            <tr key={person.person_key}>
              <td>
                <Link href={`/professional-context/${encodeURIComponent(person.person_key)}`}>
                  {person.display_name ?? "[deleted]"}
                </Link>
                <small>{shortKey(person.person_key)}</small>
              </td>
              <td>
                <strong>{person.current_role ?? "No current role"}</strong>
                <small>{person.current_team ?? "Team not evidenced"}</small>
              </td>
              <td>
                <span className={`professional-state state-${person.review_state}`}>
                  {person.review_state.replaceAll("_", " ")}
                </span>
                {person.deleted ? <small>Deleted / redacted</small> : null}
              </td>
              <td>
                <strong>{person.lawful_basis.replaceAll("_", " ")}</strong>
                <small>{person.processing_purpose}</small>
              </td>
              <td>
                <time dateTime={person.last_observed_at}>
                  {formatDate(person.last_observed_at)}
                </time>
                <small>retain to {formatDate(person.retention_until)}</small>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function shortKey(value: string): string {
  return value.length > 34 ? `${value.slice(0, 31)}…` : value;
}

function formatDate(value: string): string {
  return new Intl.DateTimeFormat("en-GB", { dateStyle: "medium" }).format(new Date(value));
}
