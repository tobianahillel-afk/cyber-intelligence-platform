export type PassiveAssetKind =
  | "domain"
  | "hostname"
  | "ipv4"
  | "ipv6"
  | "certificate"
  | "asn"
  | "cloud_resource";

export type PassiveObservationState =
  | "current"
  | "historical"
  | "expired"
  | "corrected"
  | "retracted"
  | "deleted"
  | "unknown";

export type OrganizationLinkStatus =
  | "unresolved"
  | "exact"
  | "candidate"
  | "review_required"
  | "rejected";

export type AttributionRisk =
  | "shared_hosting"
  | "cdn"
  | "reseller"
  | "subsidiary"
  | "abandoned_domain"
  | "reassigned_address";

export interface PassiveAssetSummary {
  id: string;
  asset_key: string;
  asset_kind: PassiveAssetKind;
  asset_value: string;
  state: PassiveObservationState;
  observed_states: PassiveObservationState[];
  first_seen_at: string;
  last_seen_at: string;
  expires_at: string | null;
  last_updated_at: string;
  source_count: number;
  independent_source_count: number;
  active: boolean;
  historical_only: boolean;
  has_conflict: boolean;
  organization_link_status: OrganizationLinkStatus;
  exact_organization_id: string | null;
  candidate_organization_ids: string[];
  organization_link_reasons: string[];
  attribution_risks: AttributionRisk[];
  exposure_assessment: "not_assessed";
}

export interface PassiveAssetPage {
  items: PassiveAssetSummary[];
  total: number;
  limit: number;
  offset: number;
}

export interface PassiveTechnology {
  evidence_level:
    | "technology_mention"
    | "passive_observation"
    | "observed_version";
  product_name: string | null;
  product_version: string | null;
  component_name: string | null;
}

export interface PassiveObservation {
  id: string;
  source_id: string;
  source_record_key: string;
  source_url: string;
  observation_kind: string;
  state: PassiveObservationState;
  observed_at: string;
  published_at: string;
  modified_at: string;
  expires_at: string | null;
  independence_key: string;
  confidence: number;
  organization_id: string | null;
  organization_link_status: OrganizationLinkStatus;
  organization_link_method: string;
  organization_link_confidence: number;
  organization_link_reasons: string[];
  attribution_risks: AttributionRisk[];
  port: number | null;
  protocol: string | null;
  active: boolean;
  historical_only: boolean;
  metadata_only: boolean;
  passive_only: boolean;
  supersedes_record_key: string | null;
  technology: PassiveTechnology | null;
}

export interface PassiveAssetDetail {
  asset: PassiveAssetSummary;
  observations: PassiveObservation[];
  safety_disclaimer: string;
}
