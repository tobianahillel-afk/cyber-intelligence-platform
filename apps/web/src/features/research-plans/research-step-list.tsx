import type { ResearchPlanDetail, ResearchStep, ResearchStepDecision } from "./types";

interface ResearchStepListProps {
  detail: ResearchPlanDetail;
}

export function ResearchStepList({ detail }: ResearchStepListProps) {
  const decisions = latestDecisions(detail.step_decisions);

  if (detail.steps.length === 0) {
    return (
      <div className="empty-state">
        <h3>No planned research steps</h3>
        <p>The plan has no persisted steps yet. This page never invents or executes a tool.</p>
      </div>
    );
  }

  return (
    <div className="research-step-list">
      {[...detail.steps]
        .sort((left, right) => left.sequence - right.sequence)
        .map((step) => (
          <ResearchStepCard key={step.id} step={step} decision={decisions.get(step.id)} />
        ))}
    </div>
  );
}

interface ResearchStepCardProps {
  step: ResearchStep;
  decision: ResearchStepDecision | undefined;
}

function ResearchStepCard({ step, decision }: ResearchStepCardProps) {
  const runtime = decision?.runtime_snapshot ?? {};
  return (
    <article className="research-step-card">
      <header>
        <span className="research-step-sequence">{step.sequence}</span>
        <div>
          <h3>{step.step_key}</h3>
          <p>
            {label(step.mode)} · {step.source_id} · {step.tool_id}
          </p>
        </div>
        <span className={`research-state research-state-${step.state}`}>{label(step.state)}</span>
      </header>

      <dl className="research-step-facts">
        <div>
          <dt>Purpose</dt>
          <dd>{label(step.purpose)}</dd>
        </div>
        <div>
          <dt>Data</dt>
          <dd>{label(step.data_category)}</dd>
        </div>
        <div>
          <dt>Risk / cost</dt>
          <dd>
            {step.risk_level} / {step.estimated_cost.toFixed(2)}
          </dd>
        </div>
        <div>
          <dt>Last eligibility</dt>
          <dd>{decision ? (decision.allowed ? "eligible" : "blocked") : "not evaluated"}</dd>
        </div>
      </dl>

      {decision && !decision.allowed ? (
        <div className="research-block-reasons">
          {decision.reasons.map((reason) => (
            <span key={reason}>{label(reason)}</span>
          ))}
        </div>
      ) : null}

      {Object.keys(runtime).length > 0 ? (
        <p className="research-runtime-note">
          Runtime snapshot: {runtimeSummary(runtime)}
        </p>
      ) : null}

      {step.mode === "manual_link" && step.target_url ? (
        <a
          className="research-manual-link"
          href={step.target_url}
          target="_blank"
          rel="noreferrer"
        >
          Open approved manual link
        </a>
      ) : null}
      {step.query_text ? <code className="research-query">{step.query_text}</code> : null}
    </article>
  );
}

function latestDecisions(
  decisions: readonly ResearchStepDecision[],
): Map<string, ResearchStepDecision> {
  const result = new Map<string, ResearchStepDecision>();
  for (const decision of decisions) {
    const stepId = String(decision.runtime_snapshot.step_id ?? "");
    if (stepId && !result.has(stepId)) {
      result.set(stepId, decision);
    }
  }
  return result;
}

function runtimeSummary(runtime: Record<string, unknown>): string {
  const enabled = Object.entries(runtime)
    .filter(([, value]) => value === true)
    .map(([key]) => label(key));
  const blocked = Object.entries(runtime)
    .filter(([, value]) => value === false)
    .map(([key]) => `not ${label(key)}`);
  return [...enabled, ...blocked].join(" · ") || "persisted local state";
}

function label(value: string): string {
  return value.replaceAll("_", " ").replaceAll("-", " ");
}
