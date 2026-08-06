export type VulnerabilityStatus =
  | "published"
  | "updated"
  | "rejected"
  | "withdrawn"
  | "superseded";

export type VulnerabilitySource =
  | "cve_org"
  | "nvd"
  | "cisa_kev"
  | "epss"
  | "osv"
  | "github_advisory"
  | "circl_vulnerability_lookup";

export type ExploitationKind =
  | "proof_of_concept"
  | "observed_exploitation"
  | "known_exploited_catalog"
  | "ransomware_campaign";

export interface VulnerabilitySummary {
  id: string;
  canonical_id: string;
  aliases: string[];
  title: string | null;
  status: VulnerabilityStatus;
  published_at: string | null;
  modified_at: string;
  source_count: number;
  superseded_by: string | null;
  exploitation_kinds: ExploitationKind[];
  maximum_cvss: number | null;
  latest_epss: number | null;
}

export interface VulnerabilityPage {
  items: VulnerabilitySummary[];
  total: number;
  limit: number;
  offset: number;
}

export interface VulnerabilityScore {
  system: string;
  value: number;
  vector: string | null;
  percentile: number | null;
  assessed_at: string | null;
}

export interface AffectedRange {
  ecosystem: string;
  product: string;
  introduced: string | null;
  fixed: string | null;
  last_affected: string | null;
  precision: string;
}

export interface ExploitationAssessment {
  kind: ExploitationKind;
  active: boolean;
  first_seen_at: string | null;
  last_seen_at: string | null;
  due_date: string | null;
  confidence: number;
}

export interface VulnerabilityReference {
  url: string;
  reference_type: string;
}

export interface VulnerabilitySourceSnapshot {
  id: string;
  source: VulnerabilitySource;
  source_record_key: string;
  source_url: string;
  title: string | null;
  description: string | null;
  status: VulnerabilityStatus;
  published_at: string | null;
  modified_at: string;
  superseded_by: string | null;
  source_precedence: number;
  cwes: string[];
  scores: VulnerabilityScore[];
  affected_ranges: AffectedRange[];
  exploitation: ExploitationAssessment[];
  references: VulnerabilityReference[];
}

export interface VulnerabilityDetail {
  vulnerability: VulnerabilitySummary;
  description: string | null;
  snapshots: VulnerabilitySourceSnapshot[];
  exposure_disclaimer: string;
}
