import { decideResolution } from "./actions";
import type { ResolutionCandidateDetail } from "./types";

interface ResolutionDetailProps {
  detail: ResolutionCandidateDetail;
}

export function ResolutionDetail({ detail }: ResolutionDetailProps) {
  const candidate = detail.candidate;
  const reversibleDecision = [...detail.decisions]
    .reverse()
    .find((item) => item.decision_type === "merge" || item.decision_type === "override");
  const canMerge = candidate.state === "pending" || candidate.state === "auto_confirmed";
  const canSplit = candidate.state === "confirmed" && Boolean(reversibleDecision);

  return (
    <div className="graph-detail-stack">
      <div className="graph-warning">
        Review the blast radius before deciding. A stale fingerprint is rejected by the API,
        and probabilistic matches are never applied automatically.
      </div>

      <section className="panel resolution-overview">
        <div>
          <span className={`graph-badge ${candidate.requires_review ? "graph-badge-review" : "graph-badge-current"}`}>
            {candidate.requires_review ? "review required" : candidate.state}
          </span>
          <h2>{candidate.node_key}</h2>
          <p>{candidate.reasons.join(" · ")}</p>
        </div>
        <dl>
          <div><dt>Method</dt><dd>{candidate.method.replaceAll("_", " ")}</dd></div>
          <div><dt>Score</dt><dd>{Math.round(candidate.score * 100)}%</dd></div>
          <div><dt>Target organization</dt><dd><code>{candidate.candidate_organization_id}</code></dd></div>
          <div><dt>Conflicts</dt><dd>{candidate.conflicting_organization_ids.length}</dd></div>
        </dl>
      </section>

      <section className="panel">
        <div className="panel-heading"><h2>Blast-radius preview</h2></div>
        <div className="blast-grid">
          <Metric label="Graph nodes" value={detail.blast_radius.graph_nodes} />
          <Metric label="Graph edges" value={detail.blast_radius.graph_edges} />
          <Metric label="Identity records" value={detail.blast_radius.organization_identities} />
          <Metric label="Business relationships" value={detail.blast_radius.business_relationships} />
          <Metric label="Applicability" value={detail.blast_radius.applicability_assessments} />
          <Metric label="Commercial signals" value={detail.blast_radius.commercial_signals} />
          <Metric label="Opportunities" value={detail.blast_radius.opportunities} />
        </div>
        <code className="blast-fingerprint">{detail.blast_radius.fingerprint}</code>
      </section>

      <section className="panel">
        <div className="panel-heading">
          <div><h2>Analyst decision</h2><p>Every decision is appended to immutable history.</p></div>
        </div>
        {(canMerge || canSplit) ? (
          <form action={decideResolution} className="resolution-decision-form">
            <input name="candidate_id" type="hidden" value={candidate.id} />
            <input name="blast_radius_fingerprint" type="hidden" value={detail.blast_radius.fingerprint} />
            <input name="organization_id" type="hidden" value={candidate.candidate_organization_id} />
            {reversibleDecision ? (
              <input name="reverses_decision_id" type="hidden" value={reversibleDecision.id} />
            ) : null}
            <label>
              Analyst identity
              <input maxLength={200} name="actor" required />
            </label>
            <label>
              Decision rationale
              <textarea maxLength={1000} name="reason" required rows={3} />
            </label>
            <div className="resolution-actions">
              {canMerge ? <button name="decision_type" value="merge">Confirm merge</button> : null}
              {canMerge ? <button className="secondary" name="decision_type" value="reject">Reject match</button> : null}
              {canSplit ? <button className="danger" name="decision_type" value="split">Split binding</button> : null}
            </div>
          </form>
        ) : (
          <p>No direct action is available for the current candidate state.</p>
        )}
      </section>

      <section className="panel">
        <div className="panel-heading"><h2>Decision history</h2></div>
        <div className="graph-history-list">
          {detail.decisions.length ? detail.decisions.map((item) => (
            <article key={item.id}>
              <span className="graph-badge graph-badge-history">{item.decision_type}</span>
              <strong>{item.actor}</strong>
              <p>{item.reason}</p>
              <span className="graph-subline">{new Date(item.decided_at).toISOString()}</span>
            </article>
          )) : <div className="empty-state"><p>No decision recorded yet.</p></div>}
        </div>
      </section>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: number }) {
  return <div><span>{label}</span><strong>{value}</strong></div>;
}
