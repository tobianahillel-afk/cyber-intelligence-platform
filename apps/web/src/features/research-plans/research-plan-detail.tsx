import Link from "next/link";

import { ResearchHistory } from "./research-history";
import { ResearchStepList } from "./research-step-list";
import type { ResearchPlanDetail as ResearchPlanDetailData } from "./types";

interface ResearchPlanDetailProps {
  detail: ResearchPlanDetailData;
}

export function ResearchPlanDetail({ detail }: ResearchPlanDetailProps) {
  const { plan, usage } = detail;
  const summary = [
    { label: "Plan state", value: label(plan.state) },
    { label: "Completed steps", value: `${usage.completed_steps}/${plan.max_steps}` },
    {
      label: "Automated budget",
      value: `${usage.automated_steps}/${plan.max_automated_steps}`,
    },
    {
      label: "Cost used",
      value: `${usage.cost_used.toFixed(2)} / ${plan.max_total_cost.toFixed(2)}`,
    },
  ] as const;

  return (
    <section className="page-stack research-plan-page">
      <div className="page-heading">
        <div>
          <p className="eyebrow">Governed analyst research</p>
          <h1>{plan.question}</h1>
          <p>
            Every automated step is re-evaluated from persisted source governance, provider and
            runtime controls. Manual links remain explicit analyst actions.
          </p>
        </div>
        <Link className="research-back-link" href="/research">
          Back to Research
        </Link>
      </div>

      <div className="summary-grid" aria-label="Research plan summary">
        {summary.map((item) => (
          <article className="summary-card" key={item.label}>
            <span>{item.label}</span>
            <strong>{item.value}</strong>
          </article>
        ))}
      </div>

      <section className="panel research-safety-banner">
        Eligible research ≠ captured evidence ≠ commercial signal or opportunity ≠ outreach
        authorization. A manual search link is not automated provider execution.
      </section>

      <section className="panel" aria-labelledby="research-plan-scope-title">
        <div className="panel-heading">
          <div>
            <h2 id="research-plan-scope-title">Approved research boundary</h2>
            <p>
              Purpose, data, source, tool, target and budget scopes used by every eligibility
              decision.
            </p>
          </div>
          <span className={`research-state research-state-${plan.state}`}>{label(plan.state)}</span>
        </div>
        <dl className="research-plan-facts">
          <Fact label="Purpose" value={label(plan.purpose)} />
          <Fact label="Data category" value={label(plan.data_category)} />
          <Fact label="Maximum risk" value={label(plan.max_risk_level)} />
          <Fact label="Expires" value={plan.expires_at ? formatDate(plan.expires_at) : "No expiry"} />
          <Fact label="Sources" value={join(plan.allowed_source_ids)} />
          <Fact label="Tools" value={join(plan.allowed_tool_ids)} />
          <Fact label="Hosts" value={join(plan.allowed_hosts)} />
          <Fact label="Path prefixes" value={join(plan.allowed_path_prefixes)} />
        </dl>
      </section>

      <section className="panel" aria-labelledby="research-steps-title">
        <div className="panel-heading">
          <div>
            <h2 id="research-steps-title">Ordered research steps</h2>
            <p>{detail.steps.length} persisted step(s), with the latest recorded eligibility.</p>
          </div>
        </div>
        <ResearchStepList detail={detail} />
      </section>

      <section className="panel" aria-labelledby="research-history-title">
        <div className="panel-heading">
          <div>
            <h2 id="research-history-title">Audit and evidence history</h2>
            <p>Immutable lifecycle, revision, attempt and evidence-reference chronology.</p>
          </div>
        </div>
        <ResearchHistory detail={detail} />
      </section>
    </section>
  );
}

interface FactProps {
  label: string;
  value: string;
}

function Fact({ label: name, value }: FactProps) {
  return (
    <div>
      <dt>{name}</dt>
      <dd>{value}</dd>
    </div>
  );
}

function join(values: readonly string[]): string {
  return values.length > 0 ? values.join(", ") : "None approved";
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
