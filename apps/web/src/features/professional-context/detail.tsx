import type {
  ProfessionalEvidence,
  ProfessionalPersonDetail,
  ReportingLine,
} from "./types";

interface ProfessionalDetailProps {
  detail: ProfessionalPersonDetail;
}

export function ProfessionalDetail({ detail }: ProfessionalDetailProps) {
  return (
    <div className="professional-detail-stack">
      <div className="professional-warning">{detail.evidence_disclaimer}</div>
      <section className="panel">
        <h2>Professional roles and teams</h2>
        <div className="professional-card-grid">
          {detail.roles.map((role) => (
            <article className="professional-card" key={role.claim_key}>
              <span>{role.employment_state.replaceAll("_", " ")}</span>
              <h3>{role.role_title ?? "[deleted]"}</h3>
              <p>{role.team_name ?? "Team not evidenced"}</p>
              <small>{role.review_state.replaceAll("_", " ")}</small>
            </article>
          ))}
        </div>
      </section>
      <section className="panel">
        <h2>Reporting-line claims</h2>
        <ReportingClaims
          incoming={detail.reporting_as_manager}
          outgoing={detail.reporting_as_subject}
        />
      </section>
      <section className="panel">
        <h2>Published business contact context</h2>
        <div className="professional-card-grid">
          {detail.contacts.map((contact) => (
            <article className="professional-card" key={contact.contact_key}>
              <span>{contact.channel_type.replaceAll("_", " ")}</span>
              <h3>{contact.value ?? "[deleted]"}</h3>
              <p>{contact.current ? "Current evidence" : "Historical / review only"}</p>
              <small>Never grants outreach authorization.</small>
            </article>
          ))}
        </div>
      </section>
      <section className="panel">
        <h2>Public / consented community context</h2>
        <div className="professional-card-grid">
          {detail.community_context.map((item) => (
            <article className="professional-card" key={item.context_key}>
              <span>{item.acquisition_mode.replaceAll("_", " ")}</span>
              <h3>{item.community_name}</h3>
              <p>{item.context_value ?? "[deleted]"}</p>
              <small>{item.context_type.replaceAll("_", " ")}</small>
            </article>
          ))}
        </div>
      </section>
      <section className="panel">
        <h2>Service-family relevance</h2>
        <div className="professional-card-grid">
          {detail.service_relevance.map((item) => (
            <article className="professional-card" key={item.mapping_key}>
              <span>{item.service_family.replaceAll("_", " ")}</span>
              <p>{item.rationale}</p>
              <small>Analyst context only — not a need or opportunity.</small>
            </article>
          ))}
        </div>
      </section>
      <EvidenceHistory items={detail.evidence_history} />
    </div>
  );
}

function ReportingClaims({
  incoming,
  outgoing,
}: {
  incoming: ReportingLine[];
  outgoing: ReportingLine[];
}) {
  const items = [
    ...outgoing.map((item) => ({ ...item, direction: "reports to" })),
    ...incoming.map((item) => ({ ...item, direction: "reported by" })),
  ];
  return (
    <div className="professional-card-grid">
      {items.map((item) => (
        <article className="professional-card" key={`${item.direction}:${item.claim_key}`}>
          <span>{item.direction}</span>
          <h3>
            {item.direction === "reports to"
              ? shortKey(item.manager_person_key)
              : shortKey(item.subject_person_key)}
          </h3>
          <p>{item.current ? "Current claim" : "Historical / inactive claim"}</p>
          <small>No transitive hierarchy inference.</small>
        </article>
      ))}
    </div>
  );
}

function EvidenceHistory({ items }: { items: ProfessionalEvidence[] }) {
  return (
    <section className="panel">
      <h2>Source and correction history</h2>
      <div className="professional-evidence-list">
        {items.map((item, index) => (
          <article key={`${item.evidence_type}:${item.observed_at}:${index}`}>
            <strong>{item.evidence_type.replaceAll("_", " ")}</strong>
            <span>{item.source_id}</span>
            <span>{item.claim_type?.replaceAll("_", " ") ?? "reference"}</span>
            <time dateTime={item.observed_at}>{formatDate(item.observed_at)}</time>
            <small>
              {item.deleted ? "redacted" : item.source_record_key ?? "source key redacted"}
            </small>
          </article>
        ))}
      </div>
    </section>
  );
}

function shortKey(value: string): string {
  return value.length > 38 ? `${value.slice(0, 35)}…` : value;
}

function formatDate(value: string): string {
  return new Intl.DateTimeFormat("en-GB", { dateStyle: "medium" }).format(new Date(value));
}
