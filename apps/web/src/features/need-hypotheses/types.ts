export type NeedHypothesisClass =
  | "explicit_procurement"
  | "contract_renewal_or_replacement"
  | "program_build_or_transformation"
  | "capability_gap"
  | "incident_urgency"
  | "regulatory_deadline_or_gap"
  | "technology_risk_or_lifecycle"
  | "external_exposure"
  | "organizational_change"
  | "provider_dissatisfaction_or_transition"
  | "skills_and_training_need"
  | "research_only_weak_signal";

export type CyberServiceFamily =
  | "security_strategy_vciso"
  | "risk_assessment_audit"
  | "grc_compliance"
  | "penetration_testing"
  | "red_team_purple_team"
  | "vulnerability_management_asm"
  | "soc_siem_mdr_detection"
  | "incident_response_dfir"
  | "resilience_bcp_drp"
  | "iam_pam_zero_trust"
  | "cloud_security"
  | "application_security_devsecops"
  | "network_security_sase"
  | "data_security_privacy"
  | "third_party_supply_chain"
  | "ot_ics_iot_security"
  | "security_awareness_training"
  | "product_integration_migration"
  | "cyber_insurance_readiness";

export type NeedUrgency = "immediate" | "high" | "medium" | "low";
export type NeedHorizon = "immediate" | "near_term" | "medium_term" | "long_term";
export type SignalPolarity = "supporting" | "contradicting" | "negative";

export interface SourceContribution {
  independence_key: string;
  polarity: SignalPolarity;
  signal_ids: readonly string[];
  max_confidence: number;
  contribution: number;
}

export interface NeedHypothesis {
  id: string;
  organization_id: string;
  organization: string;
  family: "cyber_service_need" | "siem_soc_buying_intent";
  status: "proposed" | "active" | "dismissed";
  hypothesis_class: NeedHypothesisClass;
  service_families: readonly CyberServiceFamily[];
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
