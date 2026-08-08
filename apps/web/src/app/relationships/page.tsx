import { loadRelationshipPage } from "@/features/relationships/api";
import { parseRelationshipFilters } from "@/features/relationships/filter-state";
import { RelationshipFilters } from "@/features/relationships/relationship-filters";
import { RelationshipTable } from "@/features/relationships/relationship-table";

interface RelationshipsPageProps {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}

export default async function RelationshipsPage({ searchParams }: RelationshipsPageProps) {
  const filters = parseRelationshipFilters(await searchParams);
  const page = await loadRelationshipPage(filters);
  const summary = [
    { label: "Relationships", value: page.total },
    {
      label: "Contract-backed on page",
      value: page.items.filter((item) => item.contract_backed_current).length,
    },
    {
      label: "Claimed / inferred",
      value: page.items.filter(
        (item) => item.status === "claimed" || item.status === "inferred",
      ).length,
    },
    {
      label: "Review / disputed",
      value: page.items.filter(
        (item) => item.status === "under_review" || item.status === "disputed",
      ).length,
    },
  ] as const;

  return (
    <section className="page-stack">
      <div className="page-heading">
        <div>
          <p className="eyebrow">Temporal organization relationship intelligence</p>
          <h1>Providers, partners and dependencies</h1>
          <p>
            Review directed business and technology relationships while keeping claims,
            observations, contracts, historical evidence and inference distinct.
          </p>
        </div>
        <span className="live-label">Persisted evidence only</span>
      </div>

      <div className="relationship-warning">
        Marketing claims are not contracts. Historical or inferred relationships are not
        current incumbents, and relationship evidence is not a service need or outreach
        authorization.
      </div>

      <div className="summary-grid" aria-label="Relationship intelligence summary">
        {summary.map((item) => (
          <article className="summary-card" key={item.label}>
            <span>{item.label}</span>
            <strong>{item.value}</strong>
          </article>
        ))}
      </div>

      <section className="panel" aria-labelledby="relationship-title">
        <div className="panel-heading relationship-heading">
          <div>
            <h2 id="relationship-title">Reconciled relationships</h2>
            <p>{page.total} relationship(s), ordered by latest persisted evidence.</p>
          </div>
          <RelationshipFilters values={filters} />
        </div>
        {page.items.length > 0 ? (
          <RelationshipTable relationships={page.items} />
        ) : (
          <div className="empty-state">
            <h3>No matching relationship</h3>
            <p>These filters query stored evidence and never launch collection.</p>
          </div>
        )}
      </section>
    </section>
  );
}
