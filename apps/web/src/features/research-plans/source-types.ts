export interface ResearchSourceOption {
  rank: number;
  source_id: string;
  tool_id: string;
  mode: string;
  authorized: boolean;
  executable: boolean;
  manual_link_allowed: boolean;
  freshness_score: number;
  value_score: number;
  estimated_cost: number;
  quota_remaining: number | null;
  risk_level: string;
}

export interface ResearchSourceOptions {
  purpose: string;
  data_category: string;
  items: readonly ResearchSourceOption[];
}
