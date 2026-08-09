import { loadProfessionalPeople } from "@/features/professional-context/api";
import { parseProfessionalFilters } from "@/features/professional-context/filter-state";
import { ProfessionalFilters } from "@/features/professional-context/filters";
import { ProfessionalPersonTable } from "@/features/professional-context/person-table";

interface ProfessionalContextPageProps {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}

export default async function ProfessionalContextPage({
  searchParams,
}: ProfessionalContextPageProps) {
  const raw = await searchParams;
  const filters = parseProfessionalFilters(raw);
  const page = await loadProfessionalPeople(filters);
  const summary = [
    { label: "Professional references", value: page.total },
    {
      label: "Review required on page",
      value: page.items.filter((item) => item.review_state === "review_required").length,
    },
    {
      label: "Current role on page",
      value: page.items.filter((item) => Boolean(item.current_role)).length,
    },
    {
      label: "Redacted on page",
      value: page.items.filter((item) => item.deleted).length,
    },
  ] as const;

  return (
    <section className="page-stack">
      <div className="page-heading">
        <div>
          <p className="eyebrow">Professional organization context</p>
          <h1>Roles, teams and public business context</h1>
          <p>
            Review source-aware professional evidence without merging people by name or
            turning contact relevance into outreach authorization.
          </p>
        </div>
        <span className="live-label">Persisted evidence only</span>
      </div>

      <div className="professional-warning">
        Same name ≠ same person. Role claim ≠ verified employment. Public profile ≠ source
        automation authorization. Contact relevance ≠ outreach authorization.
      </div>

      <div className="summary-grid" aria-label="Professional context summary">
        {summary.map((item) => (
          <article className="summary-card" key={item.label}>
            <span>{item.label}</span>
            <strong>{item.value}</strong>
          </article>
        ))}
      </div>

      <section className="panel" aria-labelledby="professional-people-title">
        <div className="panel-heading professional-heading">
          <div>
            <h2 id="professional-people-title">Professional references</h2>
            <p>Current projections remain linked to their source and retention context.</p>
          </div>
          <ProfessionalFilters values={filters} />
        </div>
        {page.items.length ? (
          <ProfessionalPersonTable people={page.items} />
        ) : (
          <div className="empty-state">
            <h3>No matching professional reference</h3>
            <p>Adjust the filters or wait for governed evidence ingestion.</p>
          </div>
        )}
      </section>
    </section>
  );
}
