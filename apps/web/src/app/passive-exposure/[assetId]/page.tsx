import Link from "next/link";
import { notFound } from "next/navigation";

import {
  loadPassiveAssetDetail,
  PassiveExposureApiError,
} from "@/features/passive-exposure/api";
import {
  formatTimestamp,
  readable,
} from "@/features/passive-exposure/passive-asset-table";

interface PassiveAssetDetailPageProps {
  params: Promise<{ assetId: string }>;
}

export default async function PassiveAssetDetailPage({
  params,
}: PassiveAssetDetailPageProps) {
  const { assetId } = await params;
  const detail = await loadDetail(assetId);
  const asset = detail.asset;

  return (
    <section className="page-stack">
      <div className="page-heading">
        <div>
          <p className="eyebrow">Canonical passive asset</p>
          <h1>{asset.asset_value}</h1>
          <p>{asset.asset_key}</p>
        </div>
        <Link className="live-label" href="/passive-exposure">
          Back to passive assets
        </Link>
      </div>

      <div className="passive-warning">{detail.safety_disclaimer}</div>

      <div className="summary-grid" aria-label="Passive asset detail summary">
        <article className="summary-card">
          <span>Current state</span>
          <strong>{readable(asset.state)}</strong>
        </article>
        <article className="summary-card">
          <span>Organization link</span>
          <strong>{readable(asset.organization_link_status)}</strong>
        </article>
        <article className="summary-card">
          <span>Sources</span>
          <strong>{asset.source_count}</strong>
        </article>
        <article className="summary-card">
          <span>Exposure assessment</span>
          <strong>Not assessed</strong>
        </article>
      </div>

      <section className="panel">
        <div className="panel-heading">
          <div>
            <h2>Current reconciled observation</h2>
            <p>Attribution and chronology remain source-aware and reversible.</p>
          </div>
        </div>
        <dl className="passive-definition-list">
          <div>
            <dt>Asset type</dt>
            <dd>{readable(asset.asset_kind)}</dd>
          </div>
          <div>
            <dt>Observed states</dt>
            <dd>{asset.observed_states.map(readable).join(", ")}</dd>
          </div>
          <div>
            <dt>First seen</dt>
            <dd>{formatTimestamp(asset.first_seen_at)}</dd>
          </div>
          <div>
            <dt>Last seen</dt>
            <dd>{formatTimestamp(asset.last_seen_at)}</dd>
          </div>
          <div>
            <dt>Expires</dt>
            <dd>{formatTimestamp(asset.expires_at)}</dd>
          </div>
          <div>
            <dt>Independent groups</dt>
            <dd>{asset.independent_source_count}</dd>
          </div>
          <div>
            <dt>Exact organization</dt>
            <dd>{asset.exact_organization_id ?? "None"}</dd>
          </div>
          <div>
            <dt>Candidate organizations</dt>
            <dd>
              {asset.candidate_organization_ids.length > 0
                ? asset.candidate_organization_ids.join(", ")
                : "None"}
            </dd>
          </div>
          <div>
            <dt>Attribution risks</dt>
            <dd>
              {asset.attribution_risks.length > 0
                ? asset.attribution_risks.map(readable).join(", ")
                : "None recorded"}
            </dd>
          </div>
          <div>
            <dt>Link reasons</dt>
            <dd>
              {asset.organization_link_reasons.length > 0
                ? asset.organization_link_reasons.join(" · ")
                : "No resolved organization link"}
            </dd>
          </div>
        </dl>
      </section>

      <section className="panel" aria-labelledby="passive-history-title">
        <div className="panel-heading">
          <div>
            <h2 id="passive-history-title">Immutable observation history</h2>
            <p>
              Corrections, retractions, reassignment risks and technology evidence
              remain visible without becoming vulnerability applicability.
            </p>
          </div>
        </div>
        <div className="passive-observation-list">
          {detail.observations.map((observation) => (
            <article className="passive-observation" key={observation.id}>
              <header>
                <div>
                  <div className="passive-badges">
                    <span>{readable(observation.state)}</span>
                    <span>{readable(observation.observation_kind)}</span>
                    <span>{readable(observation.organization_link_status)}</span>
                    {!observation.active ? <span>Inactive</span> : null}
                    {observation.historical_only ? <span>Historical only</span> : null}
                  </div>
                  <h3>{observation.source_id}</h3>
                </div>
                <time>{formatTimestamp(observation.modified_at)}</time>
              </header>
              <dl className="passive-observation-facts">
                <div>
                  <dt>Observed</dt>
                  <dd>{formatTimestamp(observation.observed_at)}</dd>
                </div>
                <div>
                  <dt>Published</dt>
                  <dd>{formatTimestamp(observation.published_at)}</dd>
                </div>
                <div>
                  <dt>Expires</dt>
                  <dd>{formatTimestamp(observation.expires_at)}</dd>
                </div>
                <div>
                  <dt>Confidence</dt>
                  <dd>{Math.round(observation.confidence * 100)}%</dd>
                </div>
                <div>
                  <dt>Link method</dt>
                  <dd>{readable(observation.organization_link_method)}</dd>
                </div>
                <div>
                  <dt>Link confidence</dt>
                  <dd>{Math.round(observation.organization_link_confidence * 100)}%</dd>
                </div>
                <div>
                  <dt>Service</dt>
                  <dd>
                    {observation.port !== null && observation.protocol
                      ? `${observation.port}/${observation.protocol}`
                      : "Not applicable"}
                  </dd>
                </div>
                <div>
                  <dt>Supersedes</dt>
                  <dd>
                    {observation.supersedes_record_key ?? "No prior source revision"}
                  </dd>
                </div>
              </dl>
              {observation.technology ? (
                <div className="passive-technology">
                  <strong>{readable(observation.technology.evidence_level)}</strong>
                  <span>
                    {observation.technology.product_name ?? "Unknown product"}
                    {observation.technology.product_version
                      ? ` ${observation.technology.product_version}`
                      : ""}
                  </span>
                  {observation.technology.component_name ? (
                    <span>{observation.technology.component_name}</span>
                  ) : null}
                  <small>Observed metadata only; vulnerability applicability not assessed.</small>
                </div>
              ) : null}
              {observation.attribution_risks.length > 0 ? (
                <div className="passive-badges">
                  {observation.attribution_risks.map((risk) => (
                    <span key={risk}>{readable(risk)}</span>
                  ))}
                </div>
              ) : null}
              {observation.organization_link_reasons.length > 0 ? (
                <p>{observation.organization_link_reasons.join(" · ")}</p>
              ) : null}
              <a href={observation.source_url} rel="noreferrer" target="_blank">
                Open published source
              </a>
            </article>
          ))}
        </div>
      </section>
    </section>
  );
}

async function loadDetail(assetId: string) {
  try {
    return await loadPassiveAssetDetail(assetId);
  } catch (error) {
    if (error instanceof PassiveExposureApiError && error.status === 404) {
      notFound();
    }
    throw error;
  }
}
