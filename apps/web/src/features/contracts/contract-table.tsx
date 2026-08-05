import Link from "next/link";

import type { DateBasis, ProcurementContract } from "./types";

interface ContractTableProps {
  contracts: readonly ProcurementContract[];
}

export function ContractTable({ contracts }: ContractTableProps) {
  return (
    <div className="contract-table-wrap">
      <table className="contract-table">
        <thead>
          <tr>
            <th>Buyer and scope</th>
            <th>Published providers</th>
            <th>Value</th>
            <th>Renewal timing</th>
            <th>Evidence</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          {contracts.map((contract) => (
            <tr key={contract.id}>
              <td>
                <Link className="contract-title-link" href={`/contracts/${contract.id}`}>
                  {contract.title}
                </Link>
                <span className="contract-muted">{contract.buyer_name}</span>
                <div className="contract-tags">
                  {contract.service_families.map((family) => (
                    <span key={family}>{readable(family)}</span>
                  ))}
                </div>
              </td>
              <td>
                {contract.provider_names.length > 0 ? (
                  <ul className="compact-list">
                    {contract.provider_names.map((name) => (
                      <li key={name}>{name}</li>
                    ))}
                  </ul>
                ) : (
                  <span className="contract-muted">No published awardee</span>
                )}
              </td>
              <td>{formatMoney(contract.amount_value, contract.currency)}</td>
              <td>
                <strong>{formatDate(contract.renewal_date)}</strong>
                <DateBasisBadge basis={contract.renewal_date_basis} />
              </td>
              <td>
                <div className="source-badges">
                  {contract.source_ids.map((source) => (
                    <span key={source}>{source.toUpperCase()}</span>
                  ))}
                </div>
                <span className="contract-muted">
                  Confidence {Math.round(contract.confidence * 100)}%
                </span>
              </td>
              <td>
                <span className={`contract-status status-${contract.status}`}>
                  {readable(contract.status)}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function DateBasisBadge({ basis }: { basis: DateBasis }) {
  return <span className={`date-basis basis-${basis}`}>{readable(basis)}</span>;
}

export function formatDate(value: string | null): string {
  if (!value) {
    return "Not published";
  }
  return new Intl.DateTimeFormat("en-GB", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    timeZone: "UTC",
  }).format(new Date(`${value}T00:00:00Z`));
}

export function formatTimestamp(value: string | null): string {
  if (!value) {
    return "Not published";
  }
  return new Intl.DateTimeFormat("en-GB", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    timeZone: "UTC",
  }).format(new Date(value));
}

export function formatMoney(value: string | null, currency: string | null): string {
  if (!value || !currency) {
    return "Not published";
  }
  const amount = Number(value);
  if (!Number.isFinite(amount)) {
    return `${value} ${currency}`;
  }
  return new Intl.NumberFormat("en-GB", {
    style: "currency",
    currency,
    maximumFractionDigits: 0,
  }).format(amount);
}

export function readable(value: string): string {
  return value.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}
