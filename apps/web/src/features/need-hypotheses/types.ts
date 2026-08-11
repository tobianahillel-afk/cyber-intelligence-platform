export type NeedHypothesisClass =
  | "explicit_procurement"
  | "contract_renewal_replacement"
  | "program_build_transformation"
  | "capability_gap"
  | "incident_urgency"
  | "regulatory_deadline_gap"
  | "technology_risk_lifecycle"
  | "external_exposure"
  | "organizational_change"
  | "provider_dissatisfaction_transition"
  | "skills_training"
  | "research_only_weak_signal";

export type NeedUrgency = "immediate" | "high" | "medium" | "low";
export type NeedHorizon = "immediate" | "near_term" | "medium_term" | "long_term";
export type NeedHypothesisStatus = "proposed" | "active" | "dismissed";

export interface SourceContribution {
  independence_key: string;
  polarity: "supporting" | "contradicting" | "negative";
  signal_ids: readonly string[];
  max_confidence: number;
  contribution: number;
}

export interface NeedHypothesis {
  id: string;
  organization_id: string;
  organization: string;
  family: string;
  status: NeedHypothesisStatus;
  hypothesis_class: NeedHypothesisClass;
  service_families: readonly string[];
  confidence: number;
  urgency: NeedUrgency;
  horizon: NeedHorizon;
  rationale: string;
  applicable_offers: readonly string[];
  signal_ids: readonly string[];
  evidence_ids: readonly string[];
  conflicting_signal_ids: readonly string[];
  negative_signal_ids: readonly string[];
  source_contributions: readonly SourceContribution[];
  rule_id: string;
  rule_version: string;
  taxonomy_version: string;
  generated_at: string;
  expires_at: string;
}

export interface NeedHypothesisListResponse {
  items: readonly NeedHypothesis[];
}
