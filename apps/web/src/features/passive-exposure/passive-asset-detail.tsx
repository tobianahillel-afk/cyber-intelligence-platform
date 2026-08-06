import Link from "next/link";

import { PassiveObservationHistory } from "./passive-observation-history";
import { formatTimestamp, readable } from "./passive-asset-table";
import type { PassiveAssetDetail } from "./types";

interface PassiveAssetDetailViewProps {
  detail: PassiveAssetDetail;
}

export function PassiveAssetDetailView({ detail }: PassiveAssetDetailViewProps) {
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
      <AssetSummary detail={detail} />
      <PassiveObservationHistory observations={detail.observations} />
    </section>
  );
}

function AssetSummary({ detail }: PassiveAssetDetailViewProps) {
  const asset = detail.asset;

  return (
    <>
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
          <Fact label="Asset type" value={readable(asset.asset_kind)} />
          <Fact
            label="Observed states"
            value={asset.observed_states.map(readable).join(", ")}
          />
          <Fact label="First seen" value={formatTimestamp(asset.first_seen_at)} />
          <Fact label="Last seen" value={formatTimestamp(asset.last_seen_at)} />
          <Fact label="Expires" value={formatTimestamp(asset.expires_at)} />
          <Fact
            label="Independent groups"
            value={String(asset.independent_source_count)}
          />
          <Fact
            label="Exact organization"
            value={asset.exact_organization_id ?? "None"}
          />
          <Fact
            label="Candidate organizations"
            value={
              asset.candidate_organization_ids.length > 0
                ? asset.candidate_organization_ids.join(", ")
                : "None"
            }
          />
          <Fact
            label="Attribution risks"
            value={
              asset.attribution_risks.length > 0
                ? asset.attribution_risks.map(readable).join(", ")
                : "None recorded"
            }
          />
          <Fact
            label="Link reasons"
            value={
              asset.organization_link_reasons.length > 0
                ? asset.organization_link_reasons.join(" · ")
                : "No resolved organization link"
            }
          />
        </dl>
      </section>
    </>
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
