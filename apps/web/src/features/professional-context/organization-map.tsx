import Link from "next/link";

import type { OrganizationProfessionalMap } from "./types";

interface OrganizationMapProps {
  data: OrganizationProfessionalMap;
}

export function OrganizationMap({ data }: OrganizationMapProps) {
  const names = new Map(data.people.map((person) => [person.person_key, person.display_name]));
  return (
    <div className="professional-detail-stack">
      <div className="professional-warning">{data.privacy_disclaimer}</div>
      <section className="panel">
        <h2>Professional references</h2>
        <div className="professional-card-grid">
          {data.people.map((person) => (
            <article className="professional-card" key={person.person_key}>
              <span>{person.review_state.replaceAll("_", " ")}</span>
              <h3>{person.display_name ?? "[deleted]"}</h3>
              <p>{person.current_role ?? "No current role evidenced"}</p>
              <Link href={`/professional-context/${encodeURIComponent(person.person_key)}`}>
                Review evidence
              </Link>
            </article>
          ))}
        </div>
      </section>
      <section className="panel">
        <h2>Explicit reporting claims</h2>
        <div className="professional-evidence-list">
          {data.reporting_lines.map((line) => (
            <article key={line.claim_key}>
              <strong>{names.get(line.subject_person_key) ?? shortKey(line.subject_person_key)}</strong>
              <span>reports to</span>
              <strong>{names.get(line.manager_person_key) ?? shortKey(line.manager_person_key)}</strong>
              <span>{line.review_state.replaceAll("_", " ")}</span>
              <small>{line.current ? "current claim" : "historical / inactive"}</small>
            </article>
          ))}
        </div>
      </section>
      <section className="panel">
        <h2>Organization-level public contact channels</h2>
        <div className="professional-card-grid">
          {data.organization_contacts.map((contact) => (
            <article className="professional-card" key={contact.contact_key}>
              <span>{contact.channel_type.replaceAll("_", " ")}</span>
              <h3>{contact.value ?? "[deleted]"}</h3>
              <small>Public business context — not outreach authorization.</small>
            </article>
          ))}
        </div>
      </section>
    </div>
  );
}

function shortKey(value: string): string {
  return value.length > 34 ? `${value.slice(0, 31)}…` : value;
}
