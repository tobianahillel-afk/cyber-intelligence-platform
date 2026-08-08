export type GraphNodeType =
  | "organization"
  | "establishment"
  | "group"
  | "brand"
  | "alias"
  | "identifier"
  | "domain"
  | "asset"
  | "technology"
  | "product"
  | "incident"
  | "vulnerability"
  | "provider"
  | "material_change";

export interface GraphNodeSummary {
  id: string;
  node_key: string;
  node_type: GraphNodeType;
  display_name: string;
  organization_id: string | null;
  source_count: number;
  confidence: number;
  current: boolean;
  suppressed: boolean;
  first_observed_at: string;
  last_observed_at: string;
}

export interface GraphEdgeSummary {
  id: string;
  edge_key: string;
  source_node_key: string;
  target_node_key: string;
  edge_type: string;
  source_module: string;
  source_evidence_class: string;
  review_state: string;
  confidence: number;
  current: boolean;
  suppressed: boolean;
  valid_from: string | null;
  valid_until: string | null;
  first_observed_at: string;
  last_observed_at: string;
}

export interface GraphNodeSnapshot {
  id: string;
  snapshot_key: string;
  source_module: string;
  source_entity_type: string;
  source_record_key: string;
  source_url: string | null;
  organization_id: string | null;
  observed_at: string;
  valid_from: string | null;
  valid_until: string | null;
  confidence: number;
  active: boolean;
  suppressed: boolean;
}

export interface GraphNodePage {
  items: GraphNodeSummary[];
  total: number;
  limit: number;
  offset: number;
}

export interface GraphNodeDetail {
  node: GraphNodeSummary;
  snapshots: GraphNodeSnapshot[];
  outgoing_edges: GraphEdgeSummary[];
  incoming_edges: GraphEdgeSummary[];
  as_of: string | null;
  evidence_disclaimer: string;
}

export interface ResolutionCandidate {
  id: string;
  node_key: string;
  candidate_organization_id: string;
  method: string;
  score: number;
  reasons: string[];
  conflicting_organization_ids: string[];
  state: string;
  requires_review: boolean;
  created_at: string;
  updated_at: string;
}

export interface ResolutionCandidatePage {
  items: ResolutionCandidate[];
  total: number;
  limit: number;
  offset: number;
}

export interface ResolutionDecision {
  id: string;
  candidate_id: string;
  node_key: string;
  decision_type: string;
  actor: string;
  reason: string;
  organization_id: string | null;
  reverses_decision_id: string | null;
  blast_radius_fingerprint: string;
  decided_at: string;
}

export interface BlastRadius {
  node_key: string;
  target_organization_key: string | null;
  graph_nodes: number;
  graph_edges: number;
  organization_identities: number;
  business_relationships: number;
  applicability_assessments: number;
  commercial_signals: number;
  opportunities: number;
  downstream_record_count: number;
  requires_explicit_confirmation: boolean;
  fingerprint: string;
}

export interface ResolutionCandidateDetail {
  candidate: ResolutionCandidate;
  decisions: ResolutionDecision[];
  blast_radius: BlastRadius;
}
