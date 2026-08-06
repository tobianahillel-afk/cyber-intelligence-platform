import Link from "next/link";

import type { PublicResource } from "./types";

interface PublicResourceTableProps {
  resources: readonly PublicResource[];
}

export function PublicResourceTable({ resources }: PublicResourceTableProps) {
  return (
    <div className="public-footprint-table-wrap">
      <table className="public-footprint-table">
        <thead>
          <tr>
            <th>Organization and resource</th>
            <th>Collection state</th>
            <th>Evidence</th>
            <th>Latest observation</th>
            <th>Source</th>
          </tr>
        </thead>
        <tbody>
          {resources.map((resource) => (
            <tr key={resource.id}>
              <td>
                <Link className="public-resource-link" href={`/research/${resource.id}`}>
                  {resource.title ?? hostname(resource.canonical_url)}
                </Link>
                <span className="public-footprint-muted">{resource.organization_name}</span>
                <span className="public-footprint-url">{resource.canonical_url}</span>
              </td>
              <td>
                <div className="public-footprint-badges">
                  <span className={`retrieval-${resource.retrieval_state}`}>
                    {readable(resource.retrieval_state)}
                  </span>
                  <span>{readable(resource.kind)}</span>
                  <span>{readable(resource.access_state)}</span>
                </div>
              </td>
              <td>
                <strong>{resource.version_count} version(s)</strong>
                <span className="public-footprint-muted">
                  {resource.claim_count} claim(s)
                </span>
              </td>
              <td>
                <strong>{formatTimestamp(resource.latest_fetched_at ?? resource.last_seen_at)}</strong>
                <span className="public-footprint-muted">
                  {resource.latest_mime_type ?? "No fetched content"}
                </span>
              </td>
              <td>
                <span className="source-pill">{resource.source_id}</span>
                <span className="public-footprint-muted">
                  {readable(resource.discovery_method)}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function formatTimestamp(value: string | null): string {
  if (!value) {
    return "Not observed";
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

export function readable(value: string): string {
  return value.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

export function shortHash(value: string): string {
  return `${value.slice(0, 12)}…${value.slice(-8)}`;
}

function hostname(value: string): string {
  try {
    return new URL(value).hostname;
  } catch {
    return value;
  }
}
