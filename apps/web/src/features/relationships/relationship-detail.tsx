import type { RelationshipDetail } from "./types";
import { readable } from "./relationship-filters";
import { formatTimestamp } from "./relationship-table";

interface RelationshipDetailPanelProps {
  detail: RelationshipDetail;
}

export function RelationshipDetailPanel({ detail }: RelationshipDetailPanelProps) {
  const relationship = detail.relationship;
  return (
    <div className="relationship-detail-stack">
      <div className="relationship-warning">{detail.evidence_disclaimer}</div>
      <section className="panel relationship-detail-summary">
        <h2>Directed relationship</h2>
        <dl className="relationship-facts">
          <Fact label="Role" value={readable(relationship.role)} />
          <Fact label="Status" value={readable(relationship.status)} />
          <Fact label="Evidence" value={readable(relationship.strongest_evidence_class)} />
          <Fact
            label="Contract-backed current"
            value={relationship.contract_backed_current ? "Yes" : "No"}
          />
          <Fact label="Valid from" value={formatTimestamp(relationship.valid_from)} />
          <Fact label="Valid until" value={formatTimestamp(relationship.valid_until)} />
          <Fact label="Next renewal" value={formatTimestamp(relationship.next_renewal_at)} />
          <Fact label="Confidence" value={`${Math.round(relationship.confidence * 100)}%`} />
        </dl>
      </section>

      <section className="panel">
        <h2>Evidence history</h2>
        <div className="relationship-evidence-list">
          {detail.evidence.map((item) => (
            <article key={item.id} className="relationship-evidence-card">
              <div className="relationship-evidence-heading">
                <div>
                  <strong>{item.title}</strong>
                  <span>{readable(item.evidence_class)} · {readable(item.claim_type)}</span>
                </div>
                <span>{readable(item.source_kind)}</span>
              </div>
              <p>{item.excerpt}</p>
              <dl className="relationship-facts compact">
                <Fact label="Published" value={formatTimestamp(item.published_at)} />
                <Fact label="Observed" value={formatTimestamp(item.observed_at)} />
                <Fact label="Contract" value={item.contract_reference ?? "None"} />
                <Fact label="Renewal" value={formatTimestamp(item.renewal_at)} />
              </dl>
              <a href={item.source_url} rel="noreferrer" target="_blank">
                Open source evidence
              </a>
            </article>
          ))}
        </div>
      </section>

      <section className="panel">
        <h2>Relationship context</h2>
        {detail.contexts.length > 0 ? (
          <div className="relationship-context-list">
            {detail.contexts.map((context) => (
              <article key={context.id}>
                <strong>{readable(context.context_type)}</strong>
                <span>{context.value}</span>
                <small>{Math.round(context.confidence * 100)}% confidence</small>
              </article>
            ))}
          </div>
        ) : (
          <p>No product, service, or contract context is attached.</p>
        )}
      </section>
    </div>
  );
}

interface FactProps {
  label: string;
  value: string;
}

function Fact({ label, value }: FactProps) {
  return (
    <div>
      <dt>{label}</dt>
      <dd>{value}</dd>
    </div>
  );
}
