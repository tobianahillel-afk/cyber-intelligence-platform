export type PublicResourceKind =
  | "sitemap"
  | "feed"
  | "structured_data"
  | "web_page"
  | "document"
  | "repository"
  | "archive_snapshot"
  | "search_result";

export type ResourceAccessState = "public" | "unknown" | "restricted";
export type ResourceRetrievalState =
  | "discovered"
  | "fetched"
  | "not_modified"
  | "changed"
  | "tombstoned"
  | "quarantined";

export type PublicClaimType =
  | "contract_or_project"
  | "technology_or_architecture"
  | "provider_partner_customer"
  | "security_or_compliance_objective"
  | "professional_contact_path"
  | "corporate_change";

export interface PublicResource {
  id: string;
  organization_id: string;
  organization_name: string;
  source_id: string;
  source_record_key: string;
  canonical_url: string;
  source_url: string;
  kind: PublicResourceKind;
  discovery_method: string;
  access_state: ResourceAccessState;
  retrieval_state: ResourceRetrievalState;
  title: string | null;
  first_discovered_at: string;
  last_seen_at: string;
  latest_version_id: string | null;
  latest_fetched_at: string | null;
  latest_mime_type: string | null;
  latest_excerpt: string | null;
  version_count: number;
  claim_count: number;
  updated_at: string;
}

export interface PublicResourcePage {
  items: PublicResource[];
  total: number;
  limit: number;
  offset: number;
  generated_at: string;
}

export interface PublicResourceVersion {
  id: string;
  source_url: string;
  content_hash_sha256: string;
  fetched_at: string;
  published_at: string | null;
  source_updated_at: string | null;
  mime_type: string;
  byte_size: number;
  title: string | null;
  language: string | null;
  extracted_text_hash_sha256: string | null;
  excerpt: string | null;
  source_locator: string | null;
  supersedes_version_id: string | null;
}

export interface PublicClaim {
  id: string;
  resource_version_id: string;
  claim_type: PublicClaimType;
  statement: string;
  evidence_basis: string;
  resolution_status: string;
  confidence: number;
  corroboration_group_key: string;
  source_locator: string | null;
  excerpt: string | null;
  updated_at: string;
}

export interface PublicResourceDetail {
  resource: PublicResource;
  identity_key: string;
  corroboration_group_key: string;
  versions: PublicResourceVersion[];
  claims: PublicClaim[];
}
