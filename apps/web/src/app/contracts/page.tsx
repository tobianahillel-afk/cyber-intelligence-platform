import { loadContractPage } from "@/features/contracts/api";
import { ContractTable } from "@/features/contracts/contract-table";
import type { ContractStatus } from "@/features/contracts/types";

const allowedStatuses = new Set<ContractStatus>([
  "awarded",
  "active",
  "completed",
  "cancelled",
  "unknown",
]);

interface ContractPageProps {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}

export default async function ContractPage({ searchParams }: ContractPageProps) {
  const parameters = await searchParams;
  const statuses = parseStatuses(parameters.status);
  const family = first(parameters.family);
  const renewalFrom = validDate(first(parameters.renewal_from));
  const renewalTo = validDate(first(parameters.renewal_to));
  const page = await loadContractPage({ statuses, family, renewalFrom, renewalTo });
  const now = new Date(page.generated_at);
  const ninetyDays = now.getTime() + 90 * 24 * 60 * 60 * 1_000;
  const summary = [
    {
      label: "Contracts in scope",
      value: page.total,
    },
    {
      label: "Renewal within 90 days",
      value: page.items.filter((item) => {
        if (!item.renewal_date) return false;
        const renewal = new Date(`${item.renewal_date}T00:00:00Z`).getTime();
        return renewal >= now.getTime() && renewal <= ninetyDays;
      }).length,
    },
    {
      label: "Estimated timing",
      value: page.items.filter((item) => item.renewal_date_basis === "estimated").length,
    },
    {
      label: "Multi-source history",
      value: page.items.filter((item) => item.source_ids.length > 1).length,
    },
  ] as const;

  return (
    <section className="page-stack">
      <div className="page-heading">
        <div>
          <p className="eyebrow">Procurement intelligence</p>
          <h1>Contracts and renewals</h1>
          <p>
            Review published awards, contract revisions and renewal timing from TED, BOAMP and
            DECP. Derived and estimated dates remain visibly distinct from published facts.
          </p>
        </div>
        <span className="live-label">Protected contract history</span>
      </div>

      <div className="summary-grid" aria-label="Contract summary">
        {summary.map((item) => (
          <article className="summary-card" key={item.label}>
            <span>{item.label}</span>
            <strong>{item.value}</strong>
          </article>
        ))}
      </div>

      <section className="panel" aria-labelledby="contract-list-title">
        <div className="panel-heading">
          <div>
            <h2 id="contract-list-title">Procurement contract history</h2>
            <p>{page.total} contract(s), ordered by the nearest known renewal timing.</p>
          </div>
          <form className="filter-form contract-filters">
            <label>
              Status
              <select name="status" defaultValue={statuses[0] ?? ""}>
                <option value="">All statuses</option>
                <option value="awarded">Awarded</option>
                <option value="active">Active</option>
                <option value="completed">Completed</option>
                <option value="cancelled">Cancelled</option>
                <option value="unknown">Unknown</option>
              </select>
            </label>
            <label>
              Service family
              <input name="family" defaultValue={family} placeholder="e.g. penetration_testing" />
            </label>
            <label>
              Renewal from
              <input name="renewal_from" type="date" defaultValue={renewalFrom} />
            </label>
            <label>
              Renewal to
              <input name="renewal_to" type="date" defaultValue={renewalTo} />
            </label>
            <button type="submit">Apply</button>
          </form>
        </div>
        {page.items.length > 0 ? (
          <ContractTable contracts={page.items} />
        ) : (
          <div className="empty-state">
            <h3>No matching contracts</h3>
            <p>
              No persisted contract matches these filters. Historical publications remain stored
              even when no current contract projection can be produced.
            </p>
          </div>
        )}
      </section>
    </section>
  );
}

function parseStatuses(value: string | string[] | undefined): ContractStatus[] {
  const values = Array.isArray(value) ? value : value ? [value] : [];
  return values.filter((item): item is ContractStatus =>
    allowedStatuses.has(item as ContractStatus),
  );
}

function first(value: string | string[] | undefined): string {
  return (Array.isArray(value) ? value[0] : value) ?? "";
}

function validDate(value: string): string {
  return /^\d{4}-\d{2}-\d{2}$/.test(value) ? value : "";
}
