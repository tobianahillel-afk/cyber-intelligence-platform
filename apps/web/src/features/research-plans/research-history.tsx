import type { ResearchPlanDetail } from "./types";

interface ResearchHistoryProps {
  detail: ResearchPlanDetail;
}

export function ResearchHistory({ detail }: ResearchHistoryProps) {
  return (
    <div className="research-history-grid">
      <section className="research-history-card">
        <h3>Plan decisions</h3>
        {detail.plan_decisions.length > 0 ? (
          <ol className="research-timeline">
            {detail.plan_decisions.map((decision) => (
              <li key={decision.decision_key}>
                <strong>{label(decision.decision_type)}</strong>
                <span>
                  {label(decision.previous_state)} → {label(decision.resulting_state)}
                </span>
                <small>
                  {decision.actor} · {formatDate(decision.decided_at)}
                </small>
                <p>{decision.reason}</p>
              </li>
            ))}
          </ol>
        ) : (
          <p className="muted-copy">No lifecycle decision recorded.</p>
        )}
      </section>

      <section className="research-history-card">
        <h3>Plan revisions</h3>
        {detail.revisions.length > 0 ? (
          <ol className="research-timeline">
            {detail.revisions.map((revision) => (
              <li key={revision.revision_key}>
                <strong>{label(revision.state)}</strong>
                <span>{revision.change_reason}</span>
                <small>
                  {revision.actor} · {formatDate(revision.created_at)}
                </small>
              </li>
            ))}
          </ol>
        ) : (
          <p className="muted-copy">No revision history recorded.</p>
        )}
      </section>

      <section className="research-history-card">
        <h3>Evidence results</h3>
        {detail.results.length > 0 ? (
          <ol className="research-timeline">
            {detail.results.map((result) => (
              <li key={result.result_key}>
                <strong>{label(result.result_type)}</strong>
                <span>{result.summary ?? result.evidence_reference}</span>
                <small>
                  {result.source_id} · {formatDate(result.recorded_at)}
                </small>
                <code>{result.provenance_reference}</code>
              </li>
            ))}
          </ol>
        ) : (
          <p className="muted-copy">No validated evidence reference captured.</p>
        )}
      </section>

      <section className="research-history-card">
        <h3>Attempts</h3>
        {detail.attempts.length > 0 ? (
          <ol className="research-timeline">
            {detail.attempts.map((attempt) => (
              <li key={attempt.attempt_key}>
                <strong>{label(attempt.state)}</strong>
                <span>{label(attempt.mode)}</span>
                <small>
                  {attempt.actor} · {formatDate(attempt.started_at)}
                </small>
                <p>
                  External action: {attempt.external_action_started ? "recorded" : "not started"}
                </p>
              </li>
            ))}
          </ol>
        ) : (
          <p className="muted-copy">No analyst attempt recorded.</p>
        )}
      </section>
    </div>
  );
}

function label(value: string): string {
  return value.replaceAll("_", " ").replaceAll("-", " ");
}

function formatDate(value: string): string {
  return new Intl.DateTimeFormat("en", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}
