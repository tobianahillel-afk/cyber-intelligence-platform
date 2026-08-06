import Link from "next/link";
import { notFound } from "next/navigation";

import {
  loadThreatIndicatorDetail,
  ThreatTelemetryApiError,
} from "@/features/threat-telemetry/api";
import {
  formatTimestamp,
  readable,
} from "@/features/threat-telemetry/indicator-table";

interface IndicatorDetailPageProps {
  params: Promise<{ indicatorId: string }>;
}

export default async function IndicatorDetailPage({
  params,
}: IndicatorDetailPageProps) {
  const { indicatorId } = await params;
  const detail = await loadDetail(indicatorId);
  const indicator = detail.indicator;

  return (
    <section className="page-stack">
      <div className="page-heading">
        <div>
          <p className="eyebrow">Canonical telemetry record</p>
          <h1>{indicator.indicator_value}</h1>
          <p>{indicator.indicator_key}</p>
        </div>
        <Link className="live-label" href="/threat-intelligence">
          Back to indicators
        </Link>
      </div>

      <div className="threat-warning">{detail.safety_disclaimer}</div>

      <div className="summary-grid" aria-label="Indicator detail summary">
        <article className="summary-card">
          <span>Current state</span>
          <strong>{readable(indicator.state)}</strong>
        </article>
        <article className="summary-card">
          <span>Source count</span>
          <strong>{indicator.source_count}</strong>
        </article>
        <article className="summary-card">
          <span>Independent groups</span>
          <strong>{indicator.independent_source_count}</strong>
        </article>
        <article className="summary-card">
          <span>Conflict</span>
          <strong>{indicator.has_conflict ? "Present" : "Absent"}</strong>
        </article>
      </div>

      <section className="panel">
        <div className="panel-heading">
          <div>
            <h2>Current reconciled state</h2>
            <p>Times and classifications remain source-aware and reversible.</p>
          </div>
        </div>
        <dl className="threat-definition-list">
          <div>
            <dt>Type</dt>
            <dd>{readable(indicator.indicator_type)}</dd>
          </div>
          <div>
            <dt>Observed states</dt>
            <dd>{indicator.observed_states.map(readable).join(", ")}</dd>
          </div>
          <div>
            <dt>First seen</dt>
            <dd>{formatTimestamp(indicator.first_seen_at)}</dd>
          </div>
          <div>
            <dt>Last seen</dt>
            <dd>{formatTimestamp(indicator.last_seen_at)}</dd>
          </div>
          <div>
            <dt>Expires</dt>
            <dd>{formatTimestamp(indicator.expires_at)}</dd>
          </div>
          <div>
            <dt>Last updated</dt>
            <dd>{formatTimestamp(indicator.last_updated_at)}</dd>
          </div>
          <div>
            <dt>Shared infrastructure</dt>
            <dd>{indicator.shared_infrastructure ? "Yes" : "No"}</dd>
          </div>
          <div>
            <dt>Historical only</dt>
            <dd>{indicator.historical_only ? "Yes" : "No"}</dd>
          </div>
          <div>
            <dt>Active</dt>
            <dd>{indicator.active ? "Yes" : "No"}</dd>
          </div>
        </dl>
      </section>

      <section className="panel" aria-labelledby="indicator-history-title">
        <div className="panel-heading">
          <div>
            <h2 id="indicator-history-title">Immutable source history</h2>
            <p>
              Corrections, expiration, sinkhole and benign reclassification remain
              visible with source scope and relationship provenance.
            </p>
          </div>
        </div>
        <div className="threat-snapshot-list">
          {detail.snapshots.map((snapshot) => (
            <article className="threat-snapshot" key={snapshot.id}>
              <header>
                <div>
                  <div className="threat-badges">
                    <span>{readable(snapshot.state)}</span>
                    <span>{readable(snapshot.source_kind)}</span>
                    <span>{readable(snapshot.sensor_scope)}</span>
                    {!snapshot.active ? <span>Inactive</span> : null}
                    {snapshot.shared_infrastructure ? <span>Shared</span> : null}
                  </div>
                  <h3>{snapshot.source_id}</h3>
                </div>
                <time>{formatTimestamp(snapshot.modified_at)}</time>
              </header>
              <dl className="threat-snapshot-facts">
                <div>
                  <dt>Published</dt>
                  <dd>{formatTimestamp(snapshot.published_at)}</dd>
                </div>
                <div>
                  <dt>First seen</dt>
                  <dd>{formatTimestamp(snapshot.first_seen_at)}</dd>
                </div>
                <div>
                  <dt>Last seen</dt>
                  <dd>{formatTimestamp(snapshot.last_seen_at)}</dd>
                </div>
                <div>
                  <dt>Expires</dt>
                  <dd>{formatTimestamp(snapshot.expires_at)}</dd>
                </div>
                <div>
                  <dt>Confidence</dt>
                  <dd>{Math.round(snapshot.confidence * 100)}%</dd>
                </div>
                <div>
                  <dt>Independence key</dt>
                  <dd>{snapshot.independence_key}</dd>
                </div>
                <div>
                  <dt>Supersedes</dt>
                  <dd>{snapshot.supersedes_record_key ?? "No prior source revision"}</dd>
                </div>
                <div>
                  <dt>Metadata only</dt>
                  <dd>{snapshot.metadata_only ? "Yes" : "No"}</dd>
                </div>
              </dl>
              {snapshot.relations.length > 0 ? (
                <div className="threat-relations">
                  {snapshot.relations.map((relation) => (
                    <span key={`${relation.relation_type}:${relation.target_key}`}>
                      {readable(relation.relation_type)} · {relation.target_key} ·{" "}
                      {Math.round(relation.confidence * 100)}%
                    </span>
                  ))}
                </div>
              ) : null}
              <a href={snapshot.source_url} rel="noreferrer" target="_blank">
                Open published source
              </a>
            </article>
          ))}
        </div>
      </section>
    </section>
  );
}

async function loadDetail(indicatorId: string) {
  try {
    return await loadThreatIndicatorDetail(indicatorId);
  } catch (error) {
    if (error instanceof ThreatTelemetryApiError && error.status === 404) {
      notFound();
    }
    throw error;
  }
}
