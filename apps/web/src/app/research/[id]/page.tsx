import Link from "next/link";
import { notFound } from "next/navigation";

import {
  PublicFootprintApiError,
  loadPublicResourceDetail,
} from "@/features/public-footprint/api";
import {
  formatTimestamp,
  readable,
  shortHash,
} from "@/features/public-footprint/resource-table";

interface PublicResourceDetailPageProps {
  params: Promise<{ id: string }>;
}

export default async function PublicResourceDetailPage({
  params,
}: PublicResourceDetailPageProps) {
  const { id } = await params;
  const detail = await loadDetail(id);
  const resource = detail.resource;

  return (
    <section className="page-stack">
      <div className="detail-breadcrumb">
        <Link href="/research">← Corporate public footprint</Link>
      </div>
      <div className="page-heading public-resource-detail-heading">
        <div>
          <p className="eyebrow">{readable(resource.kind)}</p>
          <h1>{resource.title ?? resource.organization_name}</h1>
          <p>{resource.organization_name}</p>
          <a href={resource.canonical_url} rel="noreferrer" target="_blank">
            {resource.canonical_url} ↗
          </a>
        </div>
        <div className="public-resource-state-card">
          <span>{readable(resource.retrieval_state)}</span>
          <strong>{resource.version_count} version(s)</strong>
          <small>{resource.claim_count} persisted claim(s)</small>
        </div>
      </div>

      <div className="summary-grid" aria-label="Public resource summary">
        <article className="summary-card">
          <span>First discovered</span>
          <strong>{formatTimestamp(resource.first_discovered_at)}</strong>
        </article>
        <article className="summary-card">
          <span>Last seen</span>
          <strong>{formatTimestamp(resource.last_seen_at)}</strong>
        </article>
        <article className="summary-card">
          <span>Access state</span>
          <strong>{readable(resource.access_state)}</strong>
        </article>
        <article className="summary-card">
          <span>Discovery method</span>
          <strong>{readable(resource.discovery_method)}</strong>
        </article>
      </div>

      <section className="panel" aria-labelledby="claims-title">
        <div className="panel-heading compact-heading">
          <div>
            <h2 id="claims-title">Evidence claims</h2>
            <p>
              Claims retain their evidence basis, resolution state and confidence. Search-result
              metadata alone cannot produce a confirmed claim.
            </p>
          </div>
        </div>
        {detail.claims.length > 0 ? (
          <div className="public-claim-grid">
            {detail.claims.map((claim) => (
              <article key={claim.id}>
                <div className="public-claim-heading">
                  <span>{readable(claim.claim_type)}</span>
                  <strong>{Math.round(claim.confidence * 100)}%</strong>
                </div>
                <h3>{claim.statement}</h3>
                {claim.excerpt ? <p>{claim.excerpt}</p> : null}
                <dl>
                  <div>
                    <dt>Resolution</dt>
                    <dd>{readable(claim.resolution_status)}</dd>
                  </div>
                  <div>
                    <dt>Evidence basis</dt>
                    <dd>{readable(claim.evidence_basis)}</dd>
                  </div>
                  <div>
                    <dt>Updated</dt>
                    <dd>{formatTimestamp(claim.updated_at)}</dd>
                  </div>
                </dl>
              </article>
            ))}
          </div>
        ) : (
          <div className="empty-state compact-empty-state">
            <h3>No extracted claim</h3>
            <p>The resource remains available as public evidence without inferred facts.</p>
          </div>
        )}
      </section>

      <section className="panel" aria-labelledby="versions-title">
        <div className="panel-heading compact-heading">
          <div>
            <h2 id="versions-title">Immutable version timeline</h2>
            <p>
              Content hashes and predecessor links show what changed without retaining unrestricted
              raw content.
            </p>
          </div>
        </div>
        <ol className="public-version-timeline">
          {detail.versions.map((version, index) => (
            <li key={version.id}>
              <div className="timeline-marker" aria-hidden="true" />
              <article>
                <div className="public-version-heading">
                  <div>
                    <span>{index === 0 ? "Latest version" : `Version ${detail.versions.length - index}`}</span>
                    <strong>{formatTimestamp(version.fetched_at)}</strong>
                  </div>
                  <span>{version.mime_type}</span>
                </div>
                <h3>{version.title ?? resource.title ?? resource.organization_name}</h3>
                {version.excerpt ? <p>{version.excerpt}</p> : null}
                <dl>
                  <div>
                    <dt>Content hash</dt>
                    <dd>{shortHash(version.content_hash_sha256)}</dd>
                  </div>
                  <div>
                    <dt>Extracted text hash</dt>
                    <dd>
                      {version.extracted_text_hash_sha256
                        ? shortHash(version.extracted_text_hash_sha256)
                        : "Not indexed"}
                    </dd>
                  </div>
                  <div>
                    <dt>Size</dt>
                    <dd>{formatBytes(version.byte_size)}</dd>
                  </div>
                  <div>
                    <dt>Supersedes</dt>
                    <dd>{version.supersedes_version_id ?? "Initial observed version"}</dd>
                  </div>
                </dl>
                <a href={version.source_url} rel="noreferrer" target="_blank">
                  Open governed source ↗
                </a>
              </article>
            </li>
          ))}
        </ol>
      </section>

      <section className="public-footprint-technical-note" aria-label="Resource provenance">
        <strong>Canonical evidence identity</strong>
        <span>{detail.identity_key}</span>
        <span>{detail.corroboration_group_key}</span>
        <small>
          Source {resource.source_id} · Record {resource.source_record_key} · Updated{" "}
          {formatTimestamp(resource.updated_at)}
        </small>
      </section>
    </section>
  );
}

async function loadDetail(id: string) {
  try {
    return await loadPublicResourceDetail(id);
  } catch (error) {
    if (error instanceof PublicFootprintApiError && error.status === 404) {
      notFound();
    }
    throw error;
  }
}

function formatBytes(value: number): string {
  if (value < 1_000) return `${value} B`;
  if (value < 1_000_000) return `${(value / 1_000).toFixed(1)} kB`;
  return `${(value / 1_000_000).toFixed(1)} MB`;
}
