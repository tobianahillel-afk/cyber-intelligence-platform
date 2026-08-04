export type OpportunityState =
  | "needs_review"
  | "qualified"
  | "rejected"
  | "snoozed"
  | "enrichment_requested";

export type OpportunityReviewAction =
  | "qualify"
  | "reject"
  | "snooze"
  | "request_enrichment"
  | "reopen";

export type OpportunityDataQuality = "complete" | "partial";

export interface OpportunityListItem {
  id: string;
  organization_id: string;
  organization: string;
  country: string | null;
  family: "siem_soc_buying_intent";
  state: OpportunityState;
  data_quality: OpportunityDataQuality;
  recommended_offer: string;
  score: number;
  confidence: number;
  trigger: string;
  last_evidence_at: string;
  updated_at: string;
  relevant_roles: readonly string[];
  next_action: string;
  evidence_count: number;
  snoozed_until: string | null;
}

export interface OpportunityPage {
  items: readonly OpportunityListItem[];
  total: number;
  limit: number;
  offset: number;
  generated_at: string;
}

export interface OpportunityEvidence {
  id: string;
  source_id: string;
  source_url: string;
  source_record_key: string | null;
  summary: string;
  confidence: number;
  collected_at: string;
  published_at: string | null;
  observed_at: string | null;
}

export interface OpportunityScoreComponent {
  id: string;
  rule_id: string;
  value: number;
  weight: number;
  contribution: number;
  kind: "positive" | "penalty";
  reason: string;
  evidence_ids: readonly string[];
  analyst_overridden: boolean;
  original_value: number | null;
  original_weight: number | null;
}

export interface OpportunityReview {
  id: string;
  action: string;
  previous_state: OpportunityState;
  new_state: OpportunityState;
  actor: string;
  note: string | null;
  occurred_at: string;
  snoozed_until: string | null;
}

export interface OpportunityDetail {
  opportunity: OpportunityListItem;
  hypothesis_id: string;
  hypothesis_status: string;
  rule_id: string;
  rule_version: string;
  rationale: string;
  generated_at: string;
  expires_at: string | null;
  score_version: string;
  config_version: string;
  raw_score: number;
  calculation_hash: string;
  review_note: string | null;
  rejected_reason: string | null;
  components: readonly OpportunityScoreComponent[];
  evidence: readonly OpportunityEvidence[];
  reviews: readonly OpportunityReview[];
}
