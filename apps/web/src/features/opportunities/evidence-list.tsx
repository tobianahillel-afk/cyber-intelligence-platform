import type { OpportunityEvidence } from "./types";

interface EvidenceListProps {
  evidence: readonly OpportunityEvidence[];
}

export function EvidenceList({ evidence }: EvidenceListProps) {
  return (
    <section className="panel detail-section" aria-labelledby="evidence-title">
      <div className="panel-heading">
        <div>
          <h2 id="evidence-title">Evidence</h2>
          <p>Every opportunity remains traceable to its original public or licensed source.</p>
        </div>
        <span className="badge badge-muted">{evidence.length} item(s)</span>
      </div>
      <div className="evidence-list">
        {evidence.map((item) => (
          <article className="evidence-card" key={item.id}>
            <div className="evidence-heading">
              <div>
                <strong>{item.source_id}</strong>
                <span className="cell-secondary">
                  {item.source_record_key ?? "No source record key"}
                </span>
              </div>
              <span>{Math.round(item.confidence * 100)}% confidence</span>
            </div>
            <p>{item.summary}</p>
            <dl className="inline-definition-list">
              <div>
                <dt>Published</dt>
                <dd>{formatDate(item.published_at)}</dd>
              </div>
              <div>
                <dt>Collected</dt>
                <dd>{formatDate(item.collected_at)}</dd>
              </div>
              <div>
                <dt>Observed</dt>
                <dd>{formatDate(item.observed_at)}</dd>
              </div>
            </dl>
            <a href={item.source_url} rel="noreferrer" target="_blank">
              Open source reference
            </a>
          </article>
        ))}
      </div>
    </section>
  );
}

function formatDate(value: string | null): string {
  if (!value) {
    return "Not provided";
  }
  return new Intl.DateTimeFormat("en-GB", {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone: "UTC",
  }).format(new Date(value));
}
