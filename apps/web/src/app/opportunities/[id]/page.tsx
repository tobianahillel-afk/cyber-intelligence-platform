import Link from "next/link";
import { notFound } from "next/navigation";

import { OpportunityApiError, loadOpportunityDetail } from "@/features/opportunities/api";
import { EvidenceList } from "@/features/opportunities/evidence-list";
import { ReviewHistory } from "@/features/opportunities/review-history";
import { ReviewPanel } from "@/features/opportunities/review-panel";
import { ScoreComponents } from "@/features/opportunities/score-components";
import type { OpportunityDetail } from "@/features/opportunities/types";

interface OpportunityDetailPageProps {
  params: Promise<{ id: string }>;
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}

export default async function OpportunityDetailPage({
  params,
  searchParams,
}: OpportunityDetailPageProps) {
  const { id } = await params;
  const notices = await searchParams;
  let detail: OpportunityDetail;
  try {
    detail = await loadOpportunityDetail(id);
  } catch (error) {
    if (error instanceof OpportunityApiError && error.status === 404) {
      notFound();
    }
    return <ApiUnavailable message={messageFromError(error)} />;
  }
  const opportunity = detail.opportunity;

  return (
    <section className="page-stack">
      <Link className="back-link" href="/">
        ← Back to Opportunity Inbox
      </Link>
      {typeof notices.updated === "string" ? (
        <div className="status-banner status-success">
          Opportunity updated: {formatLabel(notices.updated)}.
        </div>
      ) : null}
      {typeof notices.error === "string" ? (
        <div className="status-banner status-error">{notices.error}</div>
      ) : null}

      <div className="page-heading detail-heading">
        <div>
          <p className="eyebrow">{formatLabel(opportunity.family)}</p>
          <h1>{opportunity.organization}</h1>
          <p>{opportunity.trigger}</p>
        </div>
        <div className="detail-badges">
          <span className="badge">{formatLabel(opportunity.state)}</span>
          <span className="badge badge-muted">{opportunity.data_quality} data</span>
        </div>
      </div>

      <div className="summary-grid" aria-label="Opportunity summary">
        <SummaryCard label="Priority score" value={opportunity.score.toFixed(1)} />
        <SummaryCard
          label="Confidence"
          value={`${Math.round(opportunity.confidence * 100)}%`}
        />
        <SummaryCard label="Evidence" value={String(opportunity.evidence_count)} />
        <SummaryCard label="Last evidence" value={formatAge(opportunity.last_evidence_at)} />
      </div>

      <section className="panel detail-section" aria-labelledby="hypothesis-title">
        <div className="panel-heading">
          <div>
            <h2 id="hypothesis-title">Need hypothesis</h2>
            <p>{detail.rationale}</p>
          </div>
          <span className="badge badge-muted">
            {detail.rule_id} v{detail.rule_version}
          </span>
        </div>
        <dl className="detail-grid">
          <Definition label="Recommended offer" value={opportunity.recommended_offer} />
          <Definition label="Next action" value={opportunity.next_action} />
          <Definition label="Relevant roles" value={opportunity.relevant_roles.join(", ")} />
          <Definition label="Country" value={opportunity.country ?? "Not established"} />
          <Definition label="Generated" value={formatDate(detail.generated_at)} />
          <Definition label="Expires" value={formatDate(detail.expires_at)} />
          <Definition label="Score version" value={detail.score_version} />
          <Definition label="Configuration" value={detail.config_version} />
        </dl>
        <p className="hash-line">Calculation hash: {detail.calculation_hash}</p>
      </section>

      <ScoreComponents components={detail.components} opportunityId={id} />
      <EvidenceList evidence={detail.evidence} />
      <ReviewPanel opportunityId={id} state={opportunity.state} />
      <ReviewHistory reviews={detail.reviews} />
    </section>
  );
}

function SummaryCard({ label, value }: { label: string; value: string }) {
  return (
    <article className="summary-card">
      <span>{label}</span>
      <strong>{value}</strong>
    </article>
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

function ApiUnavailable({ message }: { message: string }) {
  return (
    <section className="page-stack">
      <Link className="back-link" href="/">
        ← Back to Opportunity Inbox
      </Link>
      <div className="panel unavailable-state">
        <p className="eyebrow">Backend unavailable</p>
        <h1>Opportunity detail cannot be loaded</h1>
        <p>{message}</p>
      </div>
    </section>
  );
}

function messageFromError(error: unknown): string {
  return error instanceof Error ? error.message : "Unexpected opportunity API failure";
}

function formatLabel(value: string): string {
  return value.replaceAll("_", " ");
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

function formatAge(value: string): string {
  const minutes = Math.max(0, Math.floor((Date.now() - new Date(value).getTime()) / 60_000));
  if (minutes < 60) {
    return `${minutes} min`;
  }
  const hours = Math.floor(minutes / 60);
  return hours < 48 ? `${hours} h` : `${Math.floor(hours / 24)} d`;
}
