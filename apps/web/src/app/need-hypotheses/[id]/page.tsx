import Link from "next/link";
import { notFound } from "next/navigation";

import {
  NeedHypothesisApiError,
  loadNeedHypothesis,
} from "@/features/need-hypotheses/api";

interface NeedHypothesisDetailPageProps {
  params: Promise<{ id: string }>;
}

export default async function NeedHypothesisDetailPage({
  params,
}: NeedHypothesisDetailPageProps) {
  const { id } = await params;
  const hypothesis = await loadDetail(id);

  return (
    <section className="page-stack">
      <div className="detail-breadcrumb">
        <Link href="/need-hypotheses">← Need Hypotheses</Link>
      </div>

      <div className="page-heading detail-heading">
        <div>
          <p className="eyebrow">{readable(hypothesis.hypothesis_class)}</p>
          <h1>{hypothesis.organization}</h1>
          <p>{hypothesis.rationale}</p>
        </div>
        <div className="detail-badges">
          <span className="badge">{Math.round(hypothesis.confidence * 100)}% confidence</span>
          <span className={`badge hypothesis-urgency-${hypothesis.urgency}`}>
            {readable(hypothesis.urgency)} urgency
          </span>
          <span className="badge badge-muted">{readable(hypothesis.status)}</span>
        </div>
      </div>

      <section className="panel detail-section" aria-labelledby="hypothesis-summary-title">
        <div className="panel-heading compact-heading">
          <div>
            <h2 id="hypothesis-summary-title">Hypothesis contract</h2>
            <p>Canonical classification, timing and versioned inference metadata.</p>
          </div>
        </div>
        <dl className="detail-grid">
          <Definition label="Class" value={readable(hypothesis.hypothesis_class)} />
          <Definition label="Urgency" value={readable(hypothesis.urgency)} />
          <Definition label="Horizon" value={readable(hypothesis.horizon)} />
          <Definition label="Family" value={readable(hypothesis.family)} />
          <Definition
            label="Services"
            value={hypothesis.service_families.map(readable).join(", ") || "Research only"}
          />
          <Definition
            label="Applicable offers"
            value={hypothesis.applicable_offers.join(", ") || "No offer mapped"}
          />
          <Definition label="Generated" value={formatTimestamp(hypothesis.generated_at)} />
          <Definition label="Expires" value={formatTimestamp(hypothesis.expires_at)} />
        </dl>
      </section>

      <div className="hypothesis-evidence-grid">
        <EvidencePanel
          title="Supporting evidence"
          description="Signals that positively contribute to this hypothesis."
          ids={hypothesis.signal_ids}
        />
        <EvidencePanel
          title="Conflicting evidence"
          description="Signals that directly contradict the hypothesized need."
          ids={hypothesis.conflicting_signal_ids}
        />
        <EvidencePanel
          title="Negative evidence"
          description="Evidence that reduces confidence without asserting the opposite claim."
          ids={hypothesis.negative_signal_ids}
        />
      </div>

      <section className="panel detail-section" aria-labelledby="contribution-title">
        <div className="panel-heading compact-heading">
          <div>
            <h2 id="contribution-title">Independent source contributions</h2>
            <p>
              Correlated evidence is grouped before scoring; contribution values expose the
              source-level ablation effect used by the fusion rule.
            </p>
          </div>
        </div>
        {hypothesis.source_contributions.length > 0 ? (
          <div className="hypothesis-contribution-list">
            {hypothesis.source_contributions.map((item) => (
              <article key={item.independence_key}>
                <div>
                  <strong>{item.independence_key}</strong>
                  <span className={`badge hypothesis-polarity-${item.polarity}`}>
                    {readable(item.polarity)}
                  </span>
                </div>
                <dl>
                  <Definition
                    label="Max confidence"
                    value={`${Math.round(item.max_confidence * 100)}%`}
                  />
                  <Definition
                    label="Contribution"
                    value={`${item.contribution >= 0 ? "+" : ""}${item.contribution.toFixed(3)}`}
                  />
                  <Definition label="Signals" value={String(item.signal_ids.length)} />
                </dl>
              </article>
            ))}
          </div>
        ) : (
          <div className="empty-state">
            <p>No persisted source-contribution breakdown is available.</p>
          </div>
        )}
      </section>

      <section className="panel detail-section" aria-labelledby="provenance-title">
        <div className="panel-heading compact-heading">
          <div>
            <h2 id="provenance-title">Inference provenance</h2>
            <p>Rules are versioned so the same evidence can be replayed deterministically.</p>
          </div>
        </div>
        <dl className="inline-definition-list">
          <Definition label="Rule" value={hypothesis.rule_id} />
          <Definition label="Rule version" value={hypothesis.rule_version} />
          <Definition label="Taxonomy" value={hypothesis.taxonomy_version} />
          <Definition label="Evidence records" value={String(hypothesis.evidence_ids.length)} />
        </dl>
        <p className="hypothesis-policy-note">
          This screen does not create an opportunity or outreach action. Those remain separate,
          human-controlled downstream decisions.
        </p>
      </section>
    </section>
  );
}

function Definition({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt>{label}</dt>
      <dd>{value}</dd>
    </div>
  );
}

function EvidencePanel({
  title,
  description,
  ids,
}: {
  title: string;
  description: string;
  ids: readonly string[];
}) {
  return (
    <section className="panel hypothesis-evidence-panel">
      <div className="panel-heading compact-heading">
        <div>
          <h2>{title}</h2>
          <p>{description}</p>
        </div>
        <strong>{ids.length}</strong>
      </div>
      {ids.length > 0 ? (
        <ul className="hypothesis-id-list">
          {ids.map((value) => (
            <li key={value}>{value}</li>
          ))}
        </ul>
      ) : (
        <p className="hypothesis-none">None</p>
      )}
    </section>
  );
}

async function loadDetail(id: string) {
  try {
    return await loadNeedHypothesis(id);
  } catch (error) {
    if (error instanceof NeedHypothesisApiError && error.status === 404) {
      notFound();
    }
    throw error;
  }
}

function readable(value: string): string {
  return value.replaceAll("_", " ");
}

function formatTimestamp(value: string): string {
  return new Intl.DateTimeFormat("en", {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone: "UTC",
  }).format(new Date(value));
}
