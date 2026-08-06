export type IncidentType =
  | "ransomware"
  | "data_breach"
  | "extortion"
  | "business_email_compromise"
  | "service_disruption"
  | "supply_chain"
  | "unauthorized_access"
  | "malware"
  | "unknown";

export type IncidentClaimType =
  | "attacker_allegation"
  | "media_report"
  | "researcher_report"
  | "company_confirmation"
  | "regulator_notice"
  | "cert_notice"
  | "provider_statement"
  | "denial"
  | "correction"
  | "retraction";

export type IncidentStatus =
  | "under_review"
  | "alleged"
  | "reported"
  | "confirmed"
  | "denied"
  | "retracted"
  | "resolved";

export type IncidentSourceKind =
  | "company"
  | "regulator"
  | "cert"
  | "media"
  | "research"
  | "provider"
  | "ransomware_metadata"
  | "other";

export type OrganizationLinkStatus =
  | "unresolved"
  | "exact"
  | "candidate"
  | "review_required"
  | "rejected";

export interface IncidentSummary {
  id: string;
  incident_key: string;
  incident_type: IncidentType;
  title: string;
  summary: string;
  status: IncidentStatus;
  organization_id: string | null;
  organization_link_status: OrganizationLinkStatus;
  occurrence_start_at: string | null;
  occurrence_end_at: string | null;
  discovered_at: string | null;
  first_published_at: string;
  confirmed_at: string | null;
  last_updated_at: string;
  claim_count: number;
  independent_source_count: number;
  officially_confirmed: boolean;
  has_denial: boolean;
  has_retraction: boolean;
  historical_only: boolean;
}

export interface IncidentPage {
  items: IncidentSummary[];
  total: number;
  limit: number;
  offset: number;
}

export interface IncidentClaim {
  id: string;
  source_id: string;
  source_kind: IncidentSourceKind;
  source_record_key: string;
  source_url: string;
  claim_type: IncidentClaimType;
  incident_type: IncidentType;
  title: string;
  summary: string;
  claimed_organization_name: string | null;
  organization_id: string | null;
  organization_link_status: OrganizationLinkStatus;
  published_at: string;
  modified_at: string;
  occurrence_start_at: string | null;
  occurrence_end_at: string | null;
  discovered_at: string | null;
  confirmed_at: string | null;
  independence_key: string;
  confidence: number;
  active: boolean;
  historical_only: boolean;
  metadata_only: boolean;
  supersedes_record_key: string | null;
}

export interface IncidentDetail {
  incident: IncidentSummary;
  claimed_organization_names: string[];
  claims: IncidentClaim[];
  safety_disclaimer: string;
}
