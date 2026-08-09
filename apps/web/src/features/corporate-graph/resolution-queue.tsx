import Link from "next/link";

import type { ResolutionCandidate } from "./types";

interface ResolutionQueueProps {
  candidates: ResolutionCandidate[];
}

export function ResolutionQueue({ candidates }: ResolutionQueueProps) {
  if (candidates.length === 0) {
    return (
      <div className="empty-state">
        <h3>No matching resolution candidate</h3>
        <p>Only persisted graph evidence is queried here.</p>
      </div>
    );
  }
  return (
    <div className="resolution-list">
      {candidates.map((candidate) => (
        <article className="resolution-card" key={candidate.id}>
          <div>
            <span className={`graph-badge ${candidate.requires_review ? "graph-badge-review" : "graph-badge-current"}`}>
              {candidate.requires_review ? "review required" : candidate.state}
            </span>
            <h3>{candidate.node_key}</h3>
            <p>{candidate.reasons.join(" · ")}</p>
          </div>
          <dl>
            <div>
              <dt>Method</dt>
              <dd>{candidate.method.replaceAll("_", " ")}</dd>
            </div>
            <div>
              <dt>Candidate organization</dt>
              <dd><code>{candidate.candidate_organization_id}</code></dd>
            </div>
            <div>
              <dt>Score</dt>
              <dd>{Math.round(candidate.score * 100)}%</dd>
            </div>
            <div>
              <dt>Conflicts</dt>
              <dd>{candidate.conflicting_organization_ids.length}</dd>
            </div>
          </dl>
          <Link className="graph-review-link" href={`/graph/resolution/${candidate.id}`}>
            Inspect blast radius
          </Link>
        </article>
      ))}
    </div>
  );
}
