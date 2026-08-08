export type RelationshipRole =
  | "provider"
  | "customer"
  | "partner"
  | "supplier"
  | "reseller"
  | "distributor"
  | "integrator"
  | "auditor"
  | "insurer"
  | "mssp_mdr"
  | "cloud_hosting_provider"
  | "technology_vendor"
  | "subcontractor"
  | "other";

export type RelationshipStatus =
  | "under_review"
  | "claimed"
  | "inferred"
  | "active"
  | "historical"
  | "disputed"
  | "corrected"
  | "retracted"
  | "stale";

export type RelationshipEvidenceClass =
  | "claimed"
  | "observed"
  | "contracted"
  | "historical"
  | "inferred";

export type RelationshipSourceKind =
  | "procurement"
  | "official_disclosure"
  | "case_study"
  | "partner_directory"
  | "certificate"
  | "passive_observation"
  | "regulatory_filing"
  | "licensed_metadata"
  | "other";

export type RelationshipLinkStatus =
  | "unresolved"
  | "exact"
  | "candidate"
  | "review_required"
  | "rejected";

export interface RelationshipSummary {
  id: string;
  relationship_key: string;
  role: RelationshipRole;
  status: RelationshipStatus;
  source_organization_id: string | null;
  target_organization_id: string | null;
  source_link_status: RelationshipLinkStatus;
  target_link_status: RelationshipLinkStatus;
  source_name: string | null;
  target_name: string | null;
  valid_from: string | null;
  valid_until: string | null;
  first_published_at: string;
  last_updated_at: string;
  last_observed_at: string;
  evidence_count: number;
  independent_source_count: number;
  strongest_evidence_class: RelationshipEvidenceClass;
  confidence: number;
  has_contract_evidence: boolean;
  contract_backed_current: boolean;
  next_renewal_at: string | null;
  has_role_conflict: boolean;
  has_dispute: boolean;
  has_correction: boolean;
  has_retraction: boolean;
  historical_only: boolean;
}

export interface RelationshipPage {
  items: RelationshipSummary[];
  total: number;
  limit: number;
  offset: number;
}

export interface RelationshipEvidence {
  id: string;
  source_id: string;
  source_kind: RelationshipSourceKind;
  source_record_key: string;
  source_url: string;
  claim_type: "assertion" | "dispute" | "correction" | "retraction";
  role: RelationshipRole;
  evidence_class: RelationshipEvidenceClass;
  title: string;
  excerpt: string;
  claimed_source_organization_name: string | null;
  claimed_target_organization_name: string | null;
  source_organization_id: string | null;
  target_organization_id: string | null;
  source_link_status: RelationshipLinkStatus;
  target_link_status: RelationshipLinkStatus;
  published_at: string;
  modified_at: string;
  observed_at: string;
  valid_from: string | null;
  valid_until: string | null;
  expires_at: string | null;
  contract_reference: string | null;
  product_context: string | null;
  service_context: string | null;
  renewal_at: string | null;
  independence_key: string;
  confidence: number;
  active: boolean;
  historical_only: boolean;
  supersedes_record_key: string | null;
}

export interface RelationshipContext {
  id: string;
  context_type: "product" | "service" | "contract";
  value: string;
  reference: string | null;
  confidence: number;
  created_at: string;
}

export interface RelationshipDetail {
  relationship: RelationshipSummary;
  claimed_source_organization_names: string[];
  claimed_target_organization_names: string[];
  evidence: RelationshipEvidence[];
  contexts: RelationshipContext[];
  evidence_disclaimer: string;
}
