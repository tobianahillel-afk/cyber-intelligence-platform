import { loadOpportunityPage } from "@/features/opportunities/api";
import { OpportunityTable } from "@/features/opportunities/opportunity-table";
import type { OpportunityState } from "@/features/opportunities/types";

const allowedStates = new Set<OpportunityState>([
  "needs_review",
  "qualified",
  "rejected",
  "snoozed",
  "enrichment_requested",
]);

interface OpportunityInboxPageProps {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}

export default async function OpportunityInboxPage({
  searchParams,
}: OpportunityInboxPageProps) {
  const parameters = await searchParams;
  const states = parseStates(parameters.state);
  const minScore = parseScore(parameters.min_score);
  const page = await loadOpportunityPage({ states, minScore });
  const now = new Date(page.generated_at);
  const newSince = now.getTime() - 24 * 60 * 60 * 1_000;
  const summary = [
    {
      label: "Urgent review",
      value: page.items.filter(
        (item) => item.state === "needs_review" && item.score >= 70,
      ).length,
    },
    {
      label: "New in 24 hours",
      value: page.items.filter((item) => new Date(item.updated_at).getTime() >= newSince).length,
    },
    {
      label: "High confidence",
      value: page.items.filter((item) => item.confidence >= 0.8).length,
    },
    {
      label: "Needs enrichment",
      value: page.items.filter(
        (item) => item.data_quality === "partial" || item.state === "enrichment_requested",
      ).length,
    },
  ] as const;

  return (
    <section className="page-stack">
      <div className="page-heading">
        <div>
          <p className="eyebrow">Analyst workspace</p>
          <h1>Opportunity Inbox</h1>
          <p>
            Review evidence-backed cybersecurity service opportunities before any commercial
            action. Scores are calculated from persisted signals, explainable need hypotheses and
            versioned rules.
          </p>
        </div>
        <span className="live-label">Live PostgreSQL data</span>
      </div>

      <div className="summary-grid" aria-label="Opportunity summary">
        {summary.map((item) => (
          <article className="summary-card" key={item.label}>
            <span>{item.label}</span>
            <strong>{item.value}</strong>
          </article>
        ))}
      </div>

      <section className="panel" aria-labelledby="inbox-title">
        <div className="panel-heading">
          <div>
            <h2 id="inbox-title">Prioritized opportunities</h2>
            <p>
              {page.total} result(s), sorted by explainable score and newest evidence.
            </p>
          </div>
          <form className="filter-form">
            <label>
              State
              <select name="state" defaultValue={states[0] ?? ""}>
                <option value="">All states</option>
                <option value="needs_review">Needs review</option>
                <option value="qualified">Qualified</option>
                <option value="enrichment_requested">Enrichment requested</option>
                <option value="snoozed">Snoozed</option>
                <option value="rejected">Rejected</option>
              </select>
            </label>
            <label>
              Minimum score
              <input name="min_score" type="number" min="0" max="100" defaultValue={minScore} />
            </label>
            <button type="submit">Apply</button>
          </form>
        </div>
        {page.items.length > 0 ? (
          <OpportunityTable opportunities={page.items} now={now} />
        ) : (
          <div className="empty-state">
            <h3>No matching opportunities</h3>
            <p>
              The inbox contains no persisted opportunity matching these filters. Signals must
              be normalized, fused into explainable need hypotheses and evaluated before an item
              appears here.
            </p>
          </div>
        )}
      </section>
    </section>
  );
}

function parseStates(value: string | string[] | undefined): OpportunityState[] {
  const values = Array.isArray(value) ? value : value ? [value] : [];
  return values.filter((item): item is OpportunityState =>
    allowedStates.has(item as OpportunityState),
  );
}

function parseScore(value: string | string[] | undefined): number {
  const raw = Array.isArray(value) ? value[0] : value;
  const parsed = Number(raw ?? 0);
  return Number.isFinite(parsed) ? Math.min(100, Math.max(0, parsed)) : 0;
}
