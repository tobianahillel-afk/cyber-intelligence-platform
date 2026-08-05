import Link from "next/link";
import { notFound } from "next/navigation";

import { ContractApiError, loadContractDetail } from "@/features/contracts/api";
import {
  DateBasisBadge,
  formatDate,
  formatMoney,
  formatTimestamp,
  readable,
} from "@/features/contracts/contract-table";

interface ContractDetailPageProps {
  params: Promise<{ id: string }>;
}

export default async function ContractDetailPage({ params }: ContractDetailPageProps) {
  const { id } = await params;
  const detail = await loadDetail(id);
  const contract = detail.contract;
  const dates = [
    { label: "Award", value: contract.award_date, basis: "published" as const },
    {
      label: "Conclusion",
      value: contract.conclusion_date,
      basis: contract.conclusion_date_basis,
    },
    {
      label: "Notification",
      value: contract.notification_date,
      basis: contract.notification_date_basis,
    },
    { label: "Start", value: contract.start_date, basis: contract.start_date_basis },
    { label: "End", value: contract.end_date, basis: contract.end_date_basis },
    { label: "Renewal", value: contract.renewal_date, basis: contract.renewal_date_basis },
  ];

  return (
    <section className="page-stack">
      <div className="detail-breadcrumb">
        <Link href="/contracts">← Contracts and renewals</Link>
      </div>
      <div className="page-heading contract-detail-heading">
        <div>
          <p className="eyebrow">{detail.procedure_status} procedure</p>
          <h1>{contract.title}</h1>
          <p>{contract.buyer_name}</p>
          <div className="contract-tags">
            {contract.service_families.map((family) => (
              <span key={family}>{readable(family)}</span>
            ))}
          </div>
        </div>
        <div className="contract-detail-value">
          <span>{readable(contract.status)}</span>
          <strong>{formatMoney(contract.amount_value, contract.currency)}</strong>
          <small>{contract.amount_type ? readable(contract.amount_type) : "Amount not typed"}</small>
        </div>
      </div>

      <div className="contract-date-grid" aria-label="Contract dates">
        {dates.map((item) => (
          <article key={item.label}>
            <span>{item.label}</span>
            <strong>{formatDate(item.value)}</strong>
            <DateBasisBadge basis={item.basis} />
          </article>
        ))}
      </div>

      <div className="contract-detail-grid">
        <section className="panel" aria-labelledby="parties-title">
          <div className="panel-heading compact-heading">
            <div>
              <h2 id="parties-title">Published parties</h2>
              <p>Provider identity is never confirmed from a name alone.</p>
            </div>
          </div>
          <div className="party-list">
            {detail.parties.map((party) => (
              <article key={`${party.role}-${party.published_name}`}>
                <div>
                  <strong>{party.published_name}</strong>
                  <span>{readable(party.role)}</span>
                </div>
                <dl>
                  <div>
                    <dt>Resolution</dt>
                    <dd>{readable(party.resolution_status)}</dd>
                  </div>
                  <div>
                    <dt>Official identifier</dt>
                    <dd>{party.official_identifier ?? "Not published"}</dd>
                  </div>
                  <div>
                    <dt>Confidence</dt>
                    <dd>{Math.round(party.confidence * 100)}%</dd>
                  </div>
                </dl>
              </article>
            ))}
          </div>
        </section>

        <section className="panel" aria-labelledby="classification-title">
          <div className="panel-heading compact-heading">
            <div>
              <h2 id="classification-title">Cyber service classification</h2>
              <p>Deterministic matched terms retained for explainability.</p>
            </div>
          </div>
          <div className="classification-list">
            {detail.service_classifications.map((classification) => (
              <article key={classification.family}>
                <strong>{readable(classification.family)}</strong>
                <span>{classification.matched_terms.join(", ")}</span>
                <small>{Math.round(classification.confidence * 100)}% confidence</small>
              </article>
            ))}
          </div>
        </section>
      </div>

      <section className="panel" aria-labelledby="timeline-title">
        <div className="panel-heading compact-heading">
          <div>
            <h2 id="timeline-title">Immutable publication timeline</h2>
            <p>
              {detail.publications.length} revision(s) from {contract.source_ids.join(", ")}.
            </p>
          </div>
        </div>
        <ol className="publication-timeline">
          {detail.publications.map((publication) => (
            <li key={publication.id}>
              <div className="timeline-marker" aria-hidden="true" />
              <article>
                <div className="timeline-heading">
                  <div>
                    <span>{publication.source_id.toUpperCase()}</span>
                    <strong>{readable(publication.kind)}</strong>
                  </div>
                  <time>{formatTimestamp(publication.published_at ?? publication.collected_at)}</time>
                </div>
                <h3>{publication.title}</h3>
                <p>
                  Record {publication.source_record_key} · Procedure {publication.procedure_status}
                </p>
                <a href={publication.source_url} rel="noreferrer" target="_blank">
                  Open official publication ↗
                </a>
              </article>
            </li>
          ))}
        </ol>
      </section>

      <section className="contract-technical-note" aria-label="Contract provenance">
        <strong>Canonical keys</strong>
        <span>{detail.contract_key}</span>
        <span>{detail.procedure_key}</span>
        <small>
          First publication {formatTimestamp(detail.first_published_at)} · Latest publication{" "}
          {formatTimestamp(detail.latest_published_at)}
        </small>
      </section>
    </section>
  );
}

async function loadDetail(id: string) {
  try {
    return await loadContractDetail(id);
  } catch (error) {
    if (error instanceof ContractApiError && error.status === 404) {
      notFound();
    }
    throw error;
  }
}
