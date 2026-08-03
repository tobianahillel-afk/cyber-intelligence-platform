import { demoOpportunities } from "@/features/opportunities/demo-data";
import { OpportunityTable } from "@/features/opportunities/opportunity-table";

const summary = [
  { label: "Urgent review", value: "1" },
  { label: "New in 24 hours", value: "3" },
  { label: "High confidence", value: "2" },
  { label: "Renewal windows", value: "1" },
] as const;

export default function OpportunityInboxPage() {
  return (
    <section className="page-stack">
      <div className="page-heading">
        <div>
          <p className="eyebrow">Analyst workspace</p>
          <h1>Opportunity Inbox</h1>
          <p>
            Review evidence-backed cybersecurity needs, timing and relevant professional
            roles before any commercial action.
          </p>
        </div>
        <span className="fixture-label">Demonstration data</span>
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
            <p>Sorted by explainable score, confidence and newest evidence.</p>
          </div>
          <button type="button" disabled>
            Create saved view
          </button>
        </div>
        <OpportunityTable opportunities={demoOpportunities} />
      </section>
    </section>
  );
}
