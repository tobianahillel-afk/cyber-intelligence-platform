import {
  cancelSourceBackfillAction,
  disableSourceAction,
  pauseSourceAction,
  priorityRefreshSourceAction,
  resumeSourceAction,
} from "@/app/sources/actions";

import type { SourcePortfolioEntry } from "./types";

export function SourcePortfolio({
  sources,
}: {
  sources: readonly SourcePortfolioEntry[];
}) {
  return (
    <div className="portfolio-grid">
      {sources.map((source) => (
        <article className="portfolio-card" key={source.source_id}>
          <div className="portfolio-card-heading">
            <div>
              <p className="eyebrow">{source.category.replaceAll("_", " ")}</p>
              <h3>{source.display_name}</h3>
              <code>{source.source_id}</code>
            </div>
            <span className={`source-status source-status-${source.status}`}>
              {source.status}
            </span>
          </div>

          <dl className="portfolio-health-grid">
            <HealthItem label="Freshness" value={source.health.freshness_state} />
            <HealthItem label="Schema" value={source.health.schema_state} />
            <HealthItem label="Volume" value={source.health.volume_state} />
            <HealthItem label="Fields" value={source.health.field_population_state} />
            <HealthItem label="Circuit" value={source.health.circuit_state} />
            <HealthItem
              label="Backfill"
              value={source.health.current_backfill_state ?? "not_started"}
            />
          </dl>

          <div className="portfolio-metadata">
            <span>Last success: {formatDate(source.health.last_success_at)}</span>
            <span>Failures: {source.health.consecutive_failures}</span>
            <span>
              Quota: {source.health.quota_remaining === null ? "not reported" : source.health.quota_remaining}
            </span>
            <span>Monthly cost: {source.health.monthly_cost_used.toFixed(2)}</span>
          </div>

          {source.adapter ? (
            <div className="portfolio-capabilities">
              <strong>{source.adapter.adapter_id}</strong>
              <span>{source.adapter.modes.join(" · ")}</span>
            </div>
          ) : (
            <p className="portfolio-candidate-note">
              Candidate only. Review and authorization are required before an adapter can execute.
            </p>
          )}

          <SourceActions source={source} />
        </article>
      ))}
    </div>
  );
}

function HealthItem({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt>{label}</dt>
      <dd>{value.replaceAll("_", " ")}</dd>
    </div>
  );
}

function SourceActions({ source }: { source: SourcePortfolioEntry }) {
  if (source.status === "candidate") {
    return null;
  }
  const canRefresh =
    source.status === "executable" && source.adapter?.modes.includes("priority_refresh");
  const backfillActive =
    source.health.current_backfill_state !== null &&
    !["completed", "cancelled"].includes(source.health.current_backfill_state);
  return (
    <div className="portfolio-actions" aria-label={`${source.display_name} runtime actions`}>
      {canRefresh ? (
        <OperatorAction
          action={priorityRefreshSourceAction.bind(null, source.source_id)}
          label="Priority refresh"
        />
      ) : null}
      {source.status === "executable" ? (
        <OperatorAction
          action={pauseSourceAction.bind(null, source.source_id)}
          label="Pause"
        />
      ) : null}
      {source.status === "paused" ? (
        <OperatorAction
          action={resumeSourceAction.bind(null, source.source_id)}
          label="Resume"
        />
      ) : null}
      {backfillActive ? (
        <OperatorAction
          action={cancelSourceBackfillAction.bind(null, source.source_id)}
          label="Cancel backfill"
        />
      ) : null}
      {source.status !== "disabled" ? (
        <OperatorAction
          action={disableSourceAction.bind(null, source.source_id)}
          label="Disable"
          destructive
        />
      ) : null}
    </div>
  );
}

function OperatorAction({
  action,
  label,
  destructive = false,
}: {
  action: (formData: FormData) => Promise<void>;
  label: string;
  destructive?: boolean;
}) {
  return (
    <form action={action}>
      <input type="hidden" name="actor" value="source-operator" />
      <button className={destructive ? "destructive" : undefined} type="submit">
        {label}
      </button>
    </form>
  );
}

function formatDate(value: string | null): string {
  if (!value) {
    return "never";
  }
  return new Intl.DateTimeFormat("en", {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone: "UTC",
  }).format(new Date(value));
}
