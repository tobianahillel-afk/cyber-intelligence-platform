import Link from "next/link";

import { formatTimestamp, readable } from "./change-table";
import type { ChangeDetail } from "./types";

interface ChangeDetailPanelProps {
  detail: ChangeDetail;
}

export function ChangeDetailPanel({ detail }: ChangeDetailPanelProps) {
  const { event } = detail;
  return (
    <div className="page-stack">
      <div className="change-warning">{detail.evidence_disclaimer}</div>

      <div className="summary-grid" aria-label="Change event summary">
        <article className="summary-card">
          <span>Status</span>
          <strong>{readable(event.status)}</strong>
        </article>
        <article className="summary-card">
          <span>Current claims</span>
          <strong>{event.claim_count}</strong>
        </article>
        <article className="summary-card">
          <span>Independent sources</span>
          <strong>{event.independent_source_count}</strong>
        </article>
        <article className="summary-card">
          <span>Organization link</span>
          <strong>{readable(event.organization_link_status)}</strong>
        </article>
      </div>

      <section className="panel change-detail-grid">
        <div>
          <h2>Event chronology</h2>
          <dl className="change-definition-list">
            <dt>Event type</dt>
            <dd>{readable(event.event_type)}</dd>
            <dt>Event time</dt>
            <dd>{formatTimestamp(event.event_at)}</dd>
            <dt>First publication</dt>
            <dd>{formatTimestamp(event.first_published_at)}</dd>
            <dt>Last update</dt>
            <dd>{formatTimestamp(event.last_updated_at)}</dd>
            <dt>Official confirmation</dt>
            <dd>{event.officially_confirmed ? "Present" : "Not present"}</dd>
          </dl>
        </div>
        <div>
          <h2>Organization context</h2>
          <p>{event.organization_id ?? "No exact organization ID resolved."}</p>
          <p>
            Claimed names: {detail.claimed_organization_names.join(", ") || "None"}
          </p>
          <div className="change-badges">
            {event.has_dispute ? <span>Dispute</span> : null}
            {event.has_correction ? <span>Correction</span> : null}
            {event.has_retraction ? <span>Retraction</span> : null}
            {event.historical_only ? <span>Historical</span> : null}
          </div>
        </div>
      </section>

      <section className="panel">
        <div className="panel-heading">
          <div>
            <h2>Immutable evidence history</h2>
            <p>Every persisted revision remains visible for chronology and audit.</p>
          </div>
        </div>
        <div className="change-claim-list">
          {detail.claims.map((claim) => (
            <article key={claim.id} className="change-claim-card">
              <div className="change-claim-heading">
                <div>
                  <strong>{claim.title}</strong>
                  <span>{readable(claim.claim_type)} · {readable(claim.source_kind)}</span>
                </div>
                <a href={claim.source_url} rel="noreferrer" target="_blank">
                  Source
                </a>
              </div>
              <p>{claim.excerpt}</p>
              <dl className="change-definition-list compact">
                <dt>Published</dt><dd>{formatTimestamp(claim.published_at)}</dd>
                <dt>Modified</dt><dd>{formatTimestamp(claim.modified_at)}</dd>
                <dt>Event</dt><dd>{formatTimestamp(claim.event_at)}</dd>
                <dt>Syndication</dt><dd>{claim.syndication_group_key ?? "Independent"}</dd>
                <dt>Confidence</dt><dd>{Math.round(claim.confidence * 100)}%</dd>
              </dl>
            </article>
          ))}
        </div>
      </section>

      <section className="panel">
        <div className="panel-heading">
          <div>
            <h2>Separate service mappings</h2>
            <p>These analyst mappings are not raw evidence and do not create opportunities.</p>
          </div>
        </div>
        {detail.service_mappings.length > 0 ? (
          <div className="change-mapping-grid">
            {detail.service_mappings.map((mapping) => (
              <article key={mapping.id} className="change-mapping-card">
                <strong>{readable(mapping.service_family)}</strong>
                <p>{mapping.rationale}</p>
                <span>{Math.round(mapping.confidence * 100)}% mapping confidence</span>
              </article>
            ))}
          </div>
        ) : (
          <p>No service mapping has been persisted for this event.</p>
        )}
      </section>

      <Link className="change-back-link" href="/corporate-changes">
        Back to corporate changes
      </Link>
    </div>
  );
}
