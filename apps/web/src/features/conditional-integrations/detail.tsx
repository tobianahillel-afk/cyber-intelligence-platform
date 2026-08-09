import type { SourcePortfolioEntry } from "@/features/sources/types";

import { ApprovalForm } from "./approval-form";
import { ConditionalControlPanel } from "./control-panel";
import type {
  ConditionalProviderDetail,
  ConditionalProviderValue,
} from "./types";

export function ConditionalProviderDetailView({
  candidate,
  provider,
  value,
}: {
  candidate: SourcePortfolioEntry;
  provider: ConditionalProviderDetail | null;
  value: ConditionalProviderValue | null;
}) {
  return (
    <div className="conditional-detail-stack">
      <section className="panel">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">{candidate.category.replaceAll("_", " ")}</p>
            <h1>{candidate.display_name}</h1>
            <code>{candidate.source_id}</code>
          </div>
          <span className={`conditional-state state-${provider?.approval.state ?? "missing"}`}>
            {provider?.approval.state ?? "no dossier"}
          </span>
        </div>
        <div className="conditional-safety-banner">
          Candidate visibility ≠ approval ≠ capability ≠ execution ≠ commercial opportunity.
          This workspace does not connect to the provider.
        </div>
      </section>

      <section className="panel">
        <div className="panel-heading">
          <div>
            <h2>Provider-specific approval dossier</h2>
            <p>Every material revision is immutable and records actor plus change reason.</p>
          </div>
        </div>
        <ApprovalForm sourceId={candidate.source_id} approval={provider?.approval ?? null} />
      </section>

      {provider ? (
        <>
          <section className="panel">
            <ConditionalControlPanel
              sourceId={candidate.source_id}
              approval={provider.approval}
              control={provider.control}
            />
          </section>
          <ValuePanel value={value} />
          <AuditPanel provider={provider} />
        </>
      ) : (
        <section className="panel">
          <p className="conditional-boundary-note">
            No provider-specific dossier exists yet. Runtime controls and eligibility preview are
            intentionally unavailable until the first audited dossier revision is saved.
          </p>
        </section>
      )}
    </div>
  );
}

function ValuePanel({ value }: { value: ConditionalProviderValue | null }) {
  if (!value) return null;
  return (
    <section className="panel">
      <div className="panel-heading">
        <div>
          <h2>Observed source-value evidence</h2>
          <p>
            Counts come from existing Source Portfolio execution events. They are contribution
            evidence, not proof of causal uniqueness or authorization to create an opportunity.
          </p>
        </div>
        <span className="live-label">
          {value.evidence_available ? "execution evidence present" : "no execution evidence"}
        </span>
      </div>
      <div className="conditional-value-grid">
        <ValueCard title="This provider" value={value.source} />
        <ValueCard title="Portfolio without this provider" value={value.portfolio_without_source} />
      </div>
    </section>
  );
}

function ValueCard({ title, value }: { title: string; value: ConditionalProviderValue["source"] }) {
  return (
    <article className="conditional-value-card">
      <h3>{title}</h3>
      <dl className="conditional-compact-grid">
        <Metric label="Executions" value={String(value.executions)} />
        <Metric label="Observations" value={String(value.observations_written)} />
        <Metric label="Commercial projections" value={String(value.commercial_projections)} />
        <Metric label="Identity projections" value={String(value.identity_projections)} />
        <Metric label="Request cost" value={value.request_cost.toFixed(2)} />
      </dl>
    </article>
  );
}

function AuditPanel({ provider }: { provider: ConditionalProviderDetail }) {
  return (
    <section className="panel">
      <div className="panel-heading">
        <div>
          <h2>Immutable review and eligibility history</h2>
          <p>
            Latest records first. Eligibility reasons preserve the persisted control-plane state
            used for the decision.
          </p>
        </div>
      </div>
      <div className="conditional-audit-grid">
        <article>
          <h3>Dossier revisions</h3>
          {provider.revisions.map((revision) => (
            <div className="conditional-audit-item" key={revision.revision_key}>
              <strong>{revision.state.replaceAll("_", " ")}</strong>
              <span>{revision.actor}</span>
              <span>{revision.change_reason}</span>
              <time>{formatDate(revision.created_at)}</time>
            </div>
          ))}
        </article>
        <article>
          <h3>Eligibility decisions</h3>
          {provider.execution_decisions.length ? (
            provider.execution_decisions.map((decision) => (
              <div className="conditional-audit-item" key={decision.decision_key}>
                <strong>{decision.allowed ? "allowed" : "blocked"}</strong>
                <span>{decision.reasons.join(" · ")}</span>
                <span>{decision.target_url}</span>
                <time>{formatDate(decision.evaluated_at)}</time>
              </div>
            ))
          ) : (
            <p>No eligibility decision recorded.</p>
          )}
        </article>
      </div>
    </section>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return <div><dt>{label}</dt><dd>{value}</dd></div>;
}

function formatDate(value: string): string {
  return new Intl.DateTimeFormat("en", {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone: "UTC",
  }).format(new Date(value));
}
