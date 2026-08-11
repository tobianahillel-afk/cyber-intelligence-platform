import { loadNeedHypotheses } from "@/features/need-hypotheses/api";
import { NeedHypothesisTable } from "@/features/need-hypotheses/need-hypothesis-table";
import type {
  NeedHypothesisClass,
  NeedHypothesisStatus,
} from "@/features/need-hypotheses/types";

const classes = [
  "explicit_procurement",
  "contract_renewal_replacement",
  "program_build_transformation",
  "capability_gap",
  "incident_urgency",
  "regulatory_deadline_gap",
  "technology_risk_lifecycle",
  "external_exposure",
  "organizational_change",
  "provider_dissatisfaction_transition",
  "skills_training",
  "research_only_weak_signal",
] as const satisfies readonly NeedHypothesisClass[];
const classSet = new Set<NeedHypothesisClass>(classes);
const statusSet = new Set<NeedHypothesisStatus>(["proposed", "active", "dismissed"]);

interface NeedHypothesisPageProps {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}

export default async function NeedHypothesisPage({ searchParams }: NeedHypothesisPageProps) {
  const parameters = await searchParams;
  const hypothesisClass = parseClass(first(parameters.hypothesis_class));
  const status = parseStatus(first(parameters.status));
  const serviceFamily = first(parameters.service_family);
  const minConfidence = parseConfidence(first(parameters.min_confidence));
  const response = await loadNeedHypotheses({
    hypothesisClass,
    status,
    serviceFamily: serviceFamily || undefined,
    minConfidence,
    limit: 200,
  });
  const items = response.items;
  const highConfidence = items.filter((item) => item.confidence >= 0.75).length;
  const explicit = items.filter(
    (item) => item.hypothesis_class === "explicit_procurement",
  ).length;
  const contested = items.filter(
    (item) => item.conflicting_signal_ids.length + item.negative_signal_ids.length > 0,
  ).length;

  return (
    <section className="page-stack">
      <div className="page-heading">
        <div>
          <p className="eyebrow">Evidence fusion</p>
          <h1>Need Hypotheses</h1>
          <p>
            Inspect evidence-backed cyber needs before any downstream opportunity decision.
            Corroboration, contradictions, negative evidence and weak-signal caps remain visible.
          </p>
        </div>
        <span className="live-label">Hypothesis ≠ opportunity</span>
      </div>

      <div className="summary-grid" aria-label="Need hypothesis summary">
        <article className="summary-card">
          <span>Visible hypotheses</span>
          <strong>{items.length}</strong>
        </article>
        <article className="summary-card">
          <span>High confidence</span>
          <strong>{highConfidence}</strong>
        </article>
        <article className="summary-card">
          <span>Explicit procurement</span>
          <strong>{explicit}</strong>
        </article>
        <article className="summary-card">
          <span>Contested</span>
          <strong>{contested}</strong>
        </article>
      </div>

      <section className="panel" aria-labelledby="hypothesis-list-title">
        <div className="panel-heading hypothesis-panel-heading">
          <div>
            <h2 id="hypothesis-list-title">Analyst fusion workspace</h2>
            <p>Ordered by confidence, with source contribution and evidence balance preserved.</p>
          </div>
          <form className="filter-form hypothesis-filters">
            <label>
              Class
              <select name="hypothesis_class" defaultValue={hypothesisClass ?? ""}>
                <option value="">All classes</option>
                {classes.map((value) => (
                  <option key={value} value={value}>
                    {readable(value)}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Status
              <select name="status" defaultValue={status ?? ""}>
                <option value="">All statuses</option>
                <option value="proposed">Proposed</option>
                <option value="active">Active</option>
                <option value="dismissed">Dismissed</option>
              </select>
            </label>
            <label>
              Service family
              <input
                name="service_family"
                defaultValue={serviceFamily}
                placeholder="e.g. cloud_security"
              />
            </label>
            <label>
              Minimum confidence
              <input
                name="min_confidence"
                defaultValue={minConfidence ?? ""}
                inputMode="decimal"
                placeholder="0.75"
              />
            </label>
            <button type="submit">Apply</button>
          </form>
        </div>
        {items.length > 0 ? (
          <NeedHypothesisTable hypotheses={items} />
        ) : (
          <div className="empty-state">
            <h3>No matching hypotheses</h3>
            <p>
              No persisted need hypothesis matches these filters. Absence of a hypothesis is not
              treated as evidence that the organization has no cyber need.
            </p>
          </div>
        )}
      </section>
    </section>
  );
}

function first(value: string | string[] | undefined): string {
  return (Array.isArray(value) ? value[0] : value) ?? "";
}

function parseClass(value: string): NeedHypothesisClass | undefined {
  return classSet.has(value as NeedHypothesisClass) ? (value as NeedHypothesisClass) : undefined;
}

function parseStatus(value: string): NeedHypothesisStatus | undefined {
  return statusSet.has(value as NeedHypothesisStatus) ? (value as NeedHypothesisStatus) : undefined;
}

function parseConfidence(value: string): number | undefined {
  if (!value) return undefined;
  const parsed = Number(value);
  return Number.isFinite(parsed) && parsed >= 0 && parsed <= 1 ? parsed : undefined;
}

function readable(value: string): string {
  return value.replaceAll("_", " ");
}
