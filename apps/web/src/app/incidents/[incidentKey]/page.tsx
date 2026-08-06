import Link from "next/link";
import { notFound } from "next/navigation";

import {
  IncidentApiError,
  loadIncidentDetail,
} from "@/features/incidents/api";
import {
  formatTimestamp,
  readable,
} from "@/features/incidents/incident-table";

interface IncidentDetailPageProps {
  params: Promise<{ incidentKey: string }>;
}

export default async function IncidentDetailPage({
  params,
}: IncidentDetailPageProps) {
  const { incidentKey } = await params;
  const detail = await loadDetail(incidentKey);
  const incident = detail.incident;

  return (
    <section className="page-stack">
      <div className="page-heading">
        <div>
          <p className="eyebrow">Canonical public incident record</p>
          <h1>{incident.title}</h1>
          <p>{incident.summary}</p>
        </div>
        <Link className="live-label" href="/incidents">
          Back to incidents
        </Link>
      </div>

      <div className="incident-warning">{detail.safety_disclaimer}</div>

      <div className="summary-grid" aria-label="Incident detail summary">
        <article className="summary-card">
          <span>Status</span>
          <strong>{readable(incident.status)}</strong>
        </article>
        <article className="summary-card">
          <span>Claims</span>
          <strong>{incident.claim_count}</strong>
        </article>
        <article className="summary-card">
          <span>Independent sources</span>
          <strong>{incident.independent_source_count}</strong>
        </article>
        <article className="summary-card">
          <span>Official confirmation</span>
          <strong>{incident.officially_confirmed ? "Present" : "Absent"}</strong>
        </article>
      </div>

      <section className="panel incident-overview">
        <div className="panel-heading">
          <div>
            <h2>Resolution and chronology</h2>
            <p>
              Occurrence, discovery, publication and confirmation dates remain separate.
            </p>
          </div>
        </div>
        <dl className="incident-definition-list">
          <div>
            <dt>Incident key</dt>
            <dd>{incident.incident_key}</dd>
          </div>
          <div>
            <dt>Type</dt>
            <dd>{readable(incident.incident_type)}</dd>
          </div>
          <div>
            <dt>Organization link</dt>
            <dd>{readable(incident.organization_link_status)}</dd>
          </div>
          <div>
            <dt>Claimed organizations</dt>
            <dd>{detail.claimed_organization_names.join(", ") || "None"}</dd>
          </div>
          <div>
            <dt>Occurrence start</dt>
            <dd>{formatTimestamp(incident.occurrence_start_at)}</dd>
          </div>
          <div>
            <dt>Occurrence end</dt>
            <dd>{formatTimestamp(incident.occurrence_end_at)}</dd>
          </div>
          <div>
            <dt>Discovered</dt>
            <dd>{formatTimestamp(incident.discovered_at)}</dd>
          </div>
          <div>
            <dt>First published</dt>
            <dd>{formatTimestamp(incident.first_published_at)}</dd>
          </div>
          <div>
            <dt>Confirmed</dt>
            <dd>{formatTimestamp(incident.confirmed_at)}</dd>
          </div>
          <div>
            <dt>Last updated</dt>
            <dd>{formatTimestamp(incident.last_updated_at)}</dd>
          </div>
          <div>
            <dt>Denial present</dt>
            <dd>{incident.has_denial ? "Yes" : "No"}</dd>
          </div>
          <div>
            <dt>Retraction present</dt>
            <dd>{incident.has_retraction ? "Yes" : "No"}</dd>
          </div>
        </dl>
      </section>

      <section className="panel" aria-labelledby="incident-history-title">
        <div className="panel-heading">
          <div>
            <h2 id="incident-history-title">Immutable claim history</h2>
            <p>
              Every correction and retraction remains visible with its source,
              independence group and original publication dates.
            </p>
          </div>
        </div>
        <div className="incident-claim-list">
          {detail.claims.map((claim) => (
            <article className="incident-claim" key={claim.id}>
              <header>
                <div>
                  <div className="incident-claim-labels">
                    <span>{readable(claim.claim_type)}</span>
                    <span>{readable(claim.source_kind)}</span>
                    {!claim.active ? <span>Inactive</span> : null}
                    {claim.historical_only ? <span>Historical</span> : null}
                  </div>
                  <h3>{claim.title}</h3>
                </div>
                <time>{formatTimestamp(claim.modified_at)}</time>
              </header>
              <p>{claim.summary}</p>
              <dl className="incident-claim-facts">
                <div>
                  <dt>Source</dt>
                  <dd>{claim.source_id}</dd>
                </div>
                <div>
                  <dt>Published</dt>
                  <dd>{formatTimestamp(claim.published_at)}</dd>
                </div>
                <div>
                  <dt>Confirmed</dt>
                  <dd>{formatTimestamp(claim.confirmed_at)}</dd>
                </div>
                <div>
                  <dt>Confidence</dt>
                  <dd>{Math.round(claim.confidence * 100)}%</dd>
                </div>
                <div>
                  <dt>Organization link</dt>
                  <dd>{readable(claim.organization_link_status)}</dd>
                </div>
                <div>
                  <dt>Independence key</dt>
                  <dd>{claim.independence_key}</dd>
                </div>
                <div>
                  <dt>Supersedes</dt>
                  <dd>{claim.supersedes_record_key ?? "No prior source revision"}</dd>
                </div>
                <div>
                  <dt>Metadata only</dt>
                  <dd>{claim.metadata_only ? "Yes" : "No"}</dd>
                </div>
              </dl>
              <a href={claim.source_url} rel="noreferrer" target="_blank">
                Open published source
              </a>
            </article>
          ))}
        </div>
      </section>
    </section>
  );
}

async function loadDetail(incidentKey: string) {
  try {
    return await loadIncidentDetail(incidentKey);
  } catch (error) {
    if (error instanceof IncidentApiError && error.status === 404) {
      notFound();
    }
    throw error;
  }
}
