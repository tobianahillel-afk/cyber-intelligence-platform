export type ChangeEventType =
  | "acquisition"
  | "leadership"
  | "funding"
  | "restructuring"
  | "geographic_expansion"
  | "cloud_digital_program"
  | "regulatory_action"
  | "breach"
  | "audit"
  | "certification"
  | "security_commitment"
  | "other";

export type ChangeEventStatus =
  | "under_review"
  | "speculative"
  | "reported"
  | "confirmed"
  | "disputed"
  | "corrected"
  | "retracted"
  | "stale";

export type ChangeClaimType =
  | "confirmation"
  | "report"
  | "speculation"
  | "dispute"
  | "correction"
  | "retraction";

export type ChangeSourceKind =
  | "official_filing"
  | "regulator"
  | "company"
  | "media"
  | "analyst"
  | "other";

export type OrganizationLinkStatus =
  | "unresolved"
  | "exact"
  | "candidate"
  | "review_required"
  | "rejected";

export interface ChangeSummary {
  id: string;
  event_key: string;
  event_type: ChangeEventType;
  title: string;
  excerpt: string;
  status: ChangeEventStatus;
  organization_id: string | null;
  organization_link_status: OrganizationLinkStatus;
  event_at: string | null;
  first_published_at: string;
  last_updated_at: string;
  claim_count: number;
  independent_source_count: number;
  officially_confirmed: boolean;
  has_dispute: boolean;
  has_correction: boolean;
  has_retraction: boolean;
  historical_only: boolean;
}

export interface ChangePage {
  items: ChangeSummary[];
  total: number;
  limit: number;
  offset: number;
}

export interface ChangeClaim {
  id: string;
  source_id: string;
  source_kind: ChangeSourceKind;
  source_record_key: string;
  article_id: string;
  source_url: string;
  claim_type: ChangeClaimType;
  title: string;
  excerpt: string;
  claimed_organization_name: string | null;
  organization_id: string | null;
  organization_link_status: OrganizationLinkStatus;
  published_at: string;
  modified_at: string;
  event_at: string | null;
  expires_at: string | null;
  independence_key: string;
  syndication_group_key: string | null;
  confidence: number;
  active: boolean;
  historical_only: boolean;
  supersedes_record_key: string | null;
}

export interface ChangeServiceMapping {
  id: string;
  service_family: string;
  rationale: string;
  confidence: number;
  created_at: string;
}

export interface ChangeDetail {
  event: ChangeSummary;
  claimed_organization_names: string[];
  claims: ChangeClaim[];
  service_mappings: ChangeServiceMapping[];
  evidence_disclaimer: string;
}
