import { loadChangePage } from "@/features/corporate-changes/api";
import { parseChangeFilters } from "@/features/corporate-changes/change-filter-state";
import { ChangeFiltersForm } from "@/features/corporate-changes/change-filters";
import { ChangeTable } from "@/features/corporate-changes/change-table";

interface CorporateChangesPageProps {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}

export default async function CorporateChangesPage({
  searchParams,
}: CorporateChangesPageProps) {
  const filters = parseChangeFilters(await searchParams);
  const page = await loadChangePage(filters);
  const summary = [
    { label: "Changes", value: page.total },
    {
      label: "Confirmed on page",
      value: page.items.filter((item) => item.officially_confirmed).length,
    },
    {
      label: "Speculative on page",
      value: page.items.filter((item) => item.status === "speculative").length,
    },
    {
      label: "Review required",
      value: page.items.filter(
        (item) => item.organization_link_status === "review_required",
      ).length,
    },
  ] as const;

  return (
    <section className="page-stack">
      <div className="page-heading">
        <div>
          <p className="eyebrow">Corporate and regulatory change intelligence</p>
          <h1>Material public changes</h1>
          <p>
            Review persisted disclosures and reporting while keeping official
            confirmation, independent reporting, syndication, speculation,
            corrections, retractions and service mappings distinct.
          </p>
        </div>
        <span className="live-label">Persisted data only</span>
      </div>

      <div className="change-warning">
        A public mention is not independent corroboration, official confirmation,
        a service need, an opportunity, or authorization to contact an organization.
      </div>

      <div className="summary-grid" aria-label="Corporate change summary">
        {summary.map((item) => (
          <article className="summary-card" key={item.label}>
            <span>{item.label}</span>
            <strong>{item.value}</strong>
          </article>
        ))}
      </div>

      <section className="panel" aria-labelledby="change-title">
        <div className="panel-heading change-heading">
          <div>
            <h2 id="change-title">Reconciled change events</h2>
            <p>{page.total} event(s), ordered by latest persisted evidence.</p>
          </div>
          <ChangeFiltersForm values={filters} />
        </div>
        {page.items.length > 0 ? (
          <ChangeTable changes={page.items} />
        ) : (
          <div className="empty-state">
            <h3>No matching change event</h3>
            <p>These filters search persisted evidence and never launch collection.</p>
          </div>
        )}
      </section>
    </section>
  );
}
