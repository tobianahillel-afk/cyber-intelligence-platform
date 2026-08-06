export type IndicatorType =
  | "ipv4"
  | "ipv6"
  | "domain"
  | "url"
  | "file_hash"
  | "certificate_fingerprint"
  | "email_address";

export type IndicatorState =
  | "malicious"
  | "suspicious"
  | "historical"
  | "expired"
  | "sinkholed"
  | "benign"
  | "shared_infrastructure"
  | "unknown"
  | "retracted";

export type TelemetrySourceKind =
  | "stix_taxii"
  | "phishing_feed"
  | "passive_dns"
  | "malware_metadata"
  | "certificate_feed"
  | "provider"
  | "other";

export type SensorScope =
  | "global"
  | "regional"
  | "sector"
  | "customer_tenant"
  | "provider_aggregate"
  | "unknown";

export interface ThreatIndicatorSummary {
  id: string;
  indicator_key: string;
  indicator_type: IndicatorType;
  indicator_value: string;
  state: IndicatorState;
  observed_states: IndicatorState[];
  first_seen_at: string | null;
  last_seen_at: string | null;
  expires_at: string | null;
  last_updated_at: string;
  source_count: number;
  independent_source_count: number;
  active: boolean;
  shared_infrastructure: boolean;
  historical_only: boolean;
  has_conflict: boolean;
}

export interface ThreatIndicatorPage {
  items: ThreatIndicatorSummary[];
  total: number;
  limit: number;
  offset: number;
}

export interface ThreatIndicatorRelation {
  relation_type: string;
  target_key: string;
  confidence: number;
}

export interface ThreatIndicatorSnapshot {
  id: string;
  source_id: string;
  source_kind: TelemetrySourceKind;
  source_record_key: string;
  source_url: string;
  state: IndicatorState;
  published_at: string;
  modified_at: string;
  first_seen_at: string | null;
  last_seen_at: string | null;
  expires_at: string | null;
  independence_key: string;
  sensor_scope: SensorScope;
  confidence: number;
  source_precedence: number;
  active: boolean;
  shared_infrastructure: boolean;
  historical_only: boolean;
  metadata_only: boolean;
  supersedes_record_key: string | null;
  relations: ThreatIndicatorRelation[];
}

export interface ThreatIndicatorDetail {
  indicator: ThreatIndicatorSummary;
  snapshots: ThreatIndicatorSnapshot[];
  safety_disclaimer: string;
}
