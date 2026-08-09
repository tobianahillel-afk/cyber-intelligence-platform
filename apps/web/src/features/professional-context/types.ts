export interface ProfessionalPerson {
  person_key: string;
  display_name: string | null;
  confidence: number;
  review_state: string;
  lawful_basis: string;
  processing_purpose: string;
  current: boolean;
  suppressed: boolean;
  deleted: boolean;
  last_observed_at: string;
  retention_until: string;
  current_role: string | null;
  current_team: string | null;
  organization_id: string | null;
}

export interface ProfessionalRole {
  claim_key: string;
  role_title: string | null;
  team_name: string | null;
  organization_id: string | null;
  claimed_organization_name: string | null;
  employment_state: string;
  confidence: number;
  review_state: string;
  first_observed_at: string;
  last_observed_at: string;
  retention_until: string;
  suppressed: boolean;
  deleted: boolean;
}

export interface ReportingLine {
  claim_key: string;
  subject_person_key: string;
  manager_person_key: string;
  organization_id: string | null;
  confidence: number;
  review_state: string;
  current: boolean;
  suppressed: boolean;
  deleted: boolean;
  first_observed_at: string;
  last_observed_at: string;
}

export interface ProfessionalContact {
  contact_key: string;
  channel_type: string;
  value: string | null;
  organization_id: string | null;
  confidence: number;
  review_state: string;
  current: boolean;
  suppressed: boolean;
  deleted: boolean;
  last_observed_at: string;
  retention_until: string;
}

export interface CommunityContext {
  context_key: string;
  community_name: string;
  context_type: string;
  context_value: string | null;
  acquisition_mode: string;
  organization_id: string | null;
  confidence: number;
  review_state: string;
  current: boolean;
  suppressed: boolean;
  deleted: boolean;
  last_observed_at: string;
}

export interface ServiceRelevance {
  mapping_key: string;
  service_family: string;
  rationale: string;
  confidence: number;
  review_state: string;
  source_claim_keys: string[];
}

export interface ProfessionalEvidence {
  evidence_type: string;
  source_id: string;
  source_record_key: string | null;
  source_url: string | null;
  observed_at: string;
  claim_type: string | null;
  review_state: string;
  suppressed: boolean;
  deleted: boolean;
  retention_until: string;
}

export interface ProfessionalPersonPage {
  items: ProfessionalPerson[];
  total: number;
  limit: number;
  offset: number;
}

export interface ProfessionalPersonDetail {
  person: ProfessionalPerson;
  roles: ProfessionalRole[];
  reporting_as_subject: ReportingLine[];
  reporting_as_manager: ReportingLine[];
  contacts: ProfessionalContact[];
  community_context: CommunityContext[];
  service_relevance: ServiceRelevance[];
  evidence_history: ProfessionalEvidence[];
  evidence_disclaimer: string;
}

export interface OrganizationProfessionalMap {
  organization_id: string;
  people: ProfessionalPerson[];
  reporting_lines: ReportingLine[];
  organization_contacts: ProfessionalContact[];
  community_context: CommunityContext[];
  privacy_disclaimer: string;
}
