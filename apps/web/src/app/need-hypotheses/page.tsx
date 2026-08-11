import Link from "next/link";

import { NeedHypothesisApiError, loadNeedHypotheses } from "@/features/need-hypotheses/api";
import type {
  CyberServiceFamily,
  NeedHypothesis,
  NeedHypothesisClass,
} from "@/features/need-hypotheses/types";

export const dynamic = "force-dynamic";

const hypothesisClasses: readonly NeedHypothesisClass[] = [
  "explicit_procurement",
  "contract_renewal_or_replacement",
  "program_build_or_transformation",
  "capability_gap",
  "incident_urgency",
  "regulatory_deadline_or_gap",
  "technology_risk_or_lifecycle",
  "external_exposure",
  "organizational_change",
  "provider_dissatisfaction_or_transition",
  "skills_and_training_need",
  "research_only_weak_signal",
];

const serviceFamilies: readonly CyberServiceFamily[] = [
  "security_strategy_vciso",
  "risk_assessment_audit",
  "grc_compliance",
  "penetration_testing",
  "red_team_purple_team",
  "vulnerability_management_asm",
  "soc_siem_mdr_detection",
  "incident_response_dfir",
  "resilience_bcp_drp",
  "iam_pam_zero_trust",
  "cloud_security",
  "application_security_devsecops",
  "network_security_sase",
  "data_security_privacy",
  "third_party_supply_chain",
  "ot_ics_iot_security",
  "security_awareness_training",
  "product_integration_migration",
  "cyber_insurance_readiness",
];

interface NeedHypothesisPageProps {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}

export default async function NeedHypothesisPage({ searchParams }: NeedHypothesisPageProps) {
  const parameters = await searchParams;
  const hypothesisClass = parseEnum(parameters.class, hypothesisClasses);
  const serviceFamily = parseEnum(parameters.family, serviceFamilies);
  const minConfidence = parseConfidence(parameters.min_confidence);

  let items: readonly NeedHypothesis[];
  try {
    const response = await loadNeedHypotheses({
      hypothesisClass,
      serviceFamily,
      minConfidence,
    });
    items = response.items;
  } catch (error) {
    return <ApiUnavailable message={messageFromError(error)} />;
  }

  const summary = [
    {
      label: "Current hypotheses",
      value: items.length,
    },
    {
      label: "Immediate / high urgency",
      value: items.filter((item) => item.urgency === "immediate" || item.urgency === "high").length,
    },
    {
      label: "Contested",
      value: items.filter(
        (item) => item.conflicting_signal_ids.length > 0 || item.negative_signal_ids.length > 0,
      ).length,
    },
    {
      label: "Research only",
      value: items.filter((item) => item.hypothesis_class === "research_only_weak_signal").length,
    },
  ] as const;

  return (
    <section className="page-stack">
      <div className="page-heading">
        <div>
          <p className="eyebrow">Signal fusion</p>
          <h1>Need hypotheses</h1>
          <p>
            Inspect explainable cybersecurity service needs derived from evidence-backed signals.
            Corroboration, contradictions, freshness and weak research-only signals remain visible.
          </p>
        </div>
        <span className="live-label">Persisted fusion data</span>
      </div>

      <div className="summary-grid" aria-label="Need hypothesis summary">
        {summary.map((item) => (
          <article className="summary-card" key={item.label}>
            <span>{item.label}</span>
            <strong>{item.value}</strong>
          </article>
        ))}
      </div>

      <section className="panel" aria-labelledby="hypothesis-workspace-title">
        <div className="panel-heading">
          <div>
            <h2 id="hypothesis-workspace-title">Explainable fusion workspace</h2>
            <p>{items.length} persisted hypothesis track(s) match the current filters.</p>
          </div>
          <form className="filter-form">
            <label>
              Need class
              <select name="class" defaultValue={hypothesisClass ?? ""}>
                <option value="">All classes</option>
                {hypothesisClasses.map((value) => (
                  <option key={value} value={value}>
                    {formatLabel(value)}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Service family
              <select name="family" defaultValue={serviceFamily ?? ""}>
                <option value="">All families</option>
                {serviceFamilies.map((value) => (
                  <option key={value} value={value}>
                    {formatLabel(value)}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Minimum confidence
              <input
                name="min_confidence"
                type="number"
                min="0"
                max="1"
                step="0.05"
                defaultValue={minConfidence}
              />
            </label>
            <button type="submit">Apply</button>
          </form>
        </div>

        {items.length > 0 ? (
          <div className="hypothesis-list">
            {items.map((item) => (
              <HypothesisCard hypothesis={item} key={item.id} />
            ))}
          </div>
        ) : (
          <div className="empty-state">
            <h3>No matching hypotheses</h3>
            <p>
              No persisted need hypothesis matches these filters. Discovery metadata and weak or
              uncorroborated signals are intentionally not promoted to confirmed commercial needs.
            </p>
          </div>
        )}
      </section>
    </section>
  );
}

function HypothesisCard({ hypothesis }: { hypothesis: NeedHypothesis }) {
  const urgent = hypothesis.urgency === "immediate" || hypothesis.urgency === "high";
  const researchOnly = hypothesis.hypothesis_class === "research_only_weak_signal";
  return (
    <article className="hypothesis-card">
      <div className="hypothesis-heading">
        <div>
          <p className="eyebrow">{formatLabel(hypothesis.hypothesis_class)}</p>
          <h3>
            <Link href={`/need-hypotheses/${hypothesis.id}`}>{hypothesis.organization}</Link>
          </h3>
        </div>
        <div className="detail-badges">
          <span className={urgent ? "hypothesis-pill hypothesis-pill-urgent" : "hypothesis-pill"}>
            {formatLabel(hypothesis.urgency)} urgency
          </span>
          <span
            className={
              researchOnly ? "hypothesis-pill hypothesis-pill-research" : "hypothesis-pill"
            }
          >
            {Math.round(hypothesis.confidence * 100)}% confidence
          </span>
        </div>
      </div>

      <div className="hypothesis-meta">
        {hypothesis.service_families.map((family) => (
          <span key={family}>{formatLabel(family)}</span>
        ))}
        <span>{formatLabel(hypothesis.horizon)} horizon</span>
        <span>{formatLabel(hypothesis.status)}</span>
      </div>

      <p className="hypothesis-rationale">{hypothesis.rationale}</p>

      <div className="hypothesis-counts">
        <span>{hypothesis.signal_ids.length} supporting signal(s)</span>
        <span>{hypothesis.evidence_ids.length} evidence item(s)</span>
        <span>{hypothesis.conflicting_signal_ids.length} contradiction(s)</span>
        <span>{hypothesis.negative_signal_ids.length} negative signal(s)</span>
        <span>{hypothesis.source_contributions.length} independence group(s)</span>
      </div>

      {hypothesis.applicable_offers.length > 0 ? (
        <div className="hypothesis-offers">
          <strong>Applicable offers</strong>
          <ul>
            {hypothesis.applicable_offers.map((offer) => (
              <li key={offer}>{offer}</li>
            ))}
          </ul>
        </div>
      ) : null}

      <div className="hypothesis-contributions">
        <div className="hypothesis-contribution-heading">
          <strong>Source contribution / ablation view</strong>
          <span className="hypothesis-secondary">
            Rule {hypothesis.rule_id} v{hypothesis.rule_version} · taxonomy {hypothesis.taxonomy_version}
          </span>
        </div>
        {hypothesis.source_contributions.length > 0 ? (
          <ul>
            {hypothesis.source_contributions.map((contribution) => (
              <li key={contribution.independence_key}>
                <strong>{contribution.independence_key}</strong>: {formatLabel(contribution.polarity)},
                contribution {formatSigned(contribution.contribution)}, max confidence {Math.round(
                  contribution.max_confidence * 100,
                )}% across {contribution.signal_ids.length} signal(s)
              </li>
            ))}
          </ul>
        ) : (
          <span className="hypothesis-secondary">No contribution breakdown persisted.</span>
        )}
      </div>

      <span className="hypothesis-secondary">
        Generated {formatDate(hypothesis.generated_at)} · expires {formatDate(hypothesis.expires_at)}
      </span>
    </article>
  );
}

function ApiUnavailable({ message }: { message: string }) {
  return (
    <section className="page-stack">
      <div className="panel hypothesis-error">
        <p className="eyebrow">Backend unavailable</p>
        <h1>Need hypotheses cannot be loaded</h1>
        <p>{message}</p>
      </div>
    </section>
  );
}

function parseEnum<T extends string>(
  value: string | string[] | undefined,
  allowed: readonly T[],
): T | undefined {
  const candidate = Array.isArray(value) ? value[0] : value;
  return candidate && allowed.includes(candidate as T) ? (candidate as T) : undefined;
}

function parseConfidence(value: string | string[] | undefined): number {
  const candidate = Array.isArray(value) ? value[0] : value;
  const parsed = Number(candidate ?? 0);
  return Number.isFinite(parsed) ? Math.min(1, Math.max(0, parsed)) : 0;
}

function formatLabel(value: string): string {
  return value.replaceAll("_", " ");
}

function formatSigned(value: number): string {
  return `${value >= 0 ? "+" : ""}${value.toFixed(2)}`;
}

function formatDate(value: string): string {
  return new Intl.DateTimeFormat("en-GB", {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone: "UTC",
  }).format(new Date(value));
}

function messageFromError(error: unknown): string {
  return error instanceof NeedHypothesisApiError || error instanceof Error
    ? error.message
    : "Unexpected need hypothesis API failure";
}
