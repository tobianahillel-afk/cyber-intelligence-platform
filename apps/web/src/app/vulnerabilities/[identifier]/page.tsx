import Link from "next/link";
import { notFound } from "next/navigation";

import {
  loadVulnerabilityDetail,
  VulnerabilityApiError,
} from "@/features/vulnerabilities/api";
import {
  formatTimestamp,
  readable,
} from "@/features/vulnerabilities/vulnerability-table";

interface VulnerabilityDetailPageProps {
  params: Promise<{ identifier: string }>;
}

export default async function VulnerabilityDetailPage({
  params,
}: VulnerabilityDetailPageProps) {
  const { identifier } = await params;
  const detail = await loadDetail(identifier);
  const vulnerability = detail.vulnerability;

  return (
    <section className="page-stack">
      <div className="page-heading">
        <div>
          <p className="eyebrow">Canonical vulnerability record</p>
          <h1>{vulnerability.canonical_id}</h1>
          <p>{vulnerability.title ?? "Untitled vulnerability"}</p>
        </div>
        <Link className="live-label" href="/vulnerabilities">
          Back to vulnerabilities
        </Link>
      </div>

      <div className="exposure-warning">{detail.exposure_disclaimer}</div>

      <div className="summary-grid" aria-label="Vulnerability detail summary">
        <article className="summary-card">
          <span>Status</span>
          <strong>{readable(vulnerability.status)}</strong>
        </article>
        <article className="summary-card">
          <span>Sources</span>
          <strong>{vulnerability.source_count}</strong>
        </article>
        <article className="summary-card">
          <span>Maximum CVSS</span>
          <strong>{vulnerability.maximum_cvss?.toFixed(1) ?? "Unknown"}</strong>
        </article>
        <article className="summary-card">
          <span>Latest EPSS</span>
          <strong>
            {vulnerability.latest_epss === null
              ? "Unknown"
              : `${(vulnerability.latest_epss * 100).toFixed(1)}%`}
          </strong>
        </article>
      </div>

      <section className="panel vulnerability-description">
        <div className="panel-heading">
          <div>
            <h2>Description and identifiers</h2>
            <p>Current reconciled view with source-specific facts retained below.</p>
          </div>
        </div>
        <p>{detail.description ?? "No reconciled description is available."}</p>
        <dl className="vulnerability-definition-list">
          <div>
            <dt>Aliases</dt>
            <dd>{vulnerability.aliases.join(", ") || "None"}</dd>
          </div>
          <div>
            <dt>Published</dt>
            <dd>{formatTimestamp(vulnerability.published_at)}</dd>
          </div>
          <div>
            <dt>Modified</dt>
            <dd>{formatTimestamp(vulnerability.modified_at)}</dd>
          </div>
          <div>
            <dt>Superseded by</dt>
            <dd>{vulnerability.superseded_by ?? "No supersession"}</dd>
          </div>
        </dl>
      </section>

      <section className="panel" aria-labelledby="source-history-title">
        <div className="panel-heading">
          <div>
            <h2 id="source-history-title">Immutable source history</h2>
            <p>
              Scores, ranges and exploitation assertions remain attached to their original source.
            </p>
          </div>
        </div>
        <div className="vulnerability-snapshot-list">
          {detail.snapshots.map((snapshot) => (
            <article className="vulnerability-snapshot" key={snapshot.id}>
              <header>
                <div>
                  <span className="source-pill">{readable(snapshot.source)}</span>
                  <h3>{snapshot.title ?? snapshot.source_record_key}</h3>
                </div>
                <time>{formatTimestamp(snapshot.modified_at)}</time>
              </header>
              <p>{snapshot.description ?? "No source description."}</p>
              <div className="vulnerability-fact-grid">
                <FactList
                  title="Scores"
                  values={snapshot.scores.map(
                    (score) => `${readable(score.system)}: ${score.value}`,
                  )}
                />
                <FactList title="Weaknesses" values={snapshot.cwes} />
                <FactList
                  title="Exploitation"
                  values={snapshot.exploitation.map(
                    (assessment) =>
                      `${readable(assessment.kind)} (${assessment.active ? "active" : "inactive"})`,
                  )}
                />
                <FactList
                  title="Affected ranges"
                  values={snapshot.affected_ranges.map((range) =>
                    formatRange(
                      range.ecosystem,
                      range.product,
                      range.introduced,
                      range.fixed,
                      range.last_affected,
                    ),
                  )}
                />
              </div>
              <div className="vulnerability-references">
                {snapshot.references.map((reference) => (
                  <a
                    href={reference.url}
                    key={`${reference.reference_type}-${reference.url}`}
                    rel="noreferrer"
                    target="_blank"
                  >
                    {readable(reference.reference_type)}
                  </a>
                ))}
              </div>
            </article>
          ))}
        </div>
      </section>
    </section>
  );
}

interface FactListProps {
  title: string;
  values: readonly string[];
}

function FactList({ title, values }: FactListProps) {
  return (
    <div>
      <strong>{title}</strong>
      {values.length > 0 ? (
        <ul>
          {values.map((value) => (
            <li key={value}>{value}</li>
          ))}
        </ul>
      ) : (
        <span className="vulnerability-muted">None asserted</span>
      )}
    </div>
  );
}

async function loadDetail(identifier: string) {
  try {
    return await loadVulnerabilityDetail(identifier);
  } catch (error) {
    if (error instanceof VulnerabilityApiError && error.status === 404) {
      notFound();
    }
    throw error;
  }
}

function formatRange(
  ecosystem: string,
  product: string,
  introduced: string | null,
  fixed: string | null,
  lastAffected: string | null,
): string {
  const start = introduced ?? "unknown start";
  const end = fixed ? `fixed in ${fixed}` : lastAffected ? `through ${lastAffected}` : "open ended";
  return `${ecosystem}/${product}: ${start}, ${end}`;
}
