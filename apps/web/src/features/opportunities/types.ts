export type OpportunityFamily =
  | "crisis"
  | "exposure"
  | "buying_intent"
  | "renewal"
  | "product_fit";

export type OpportunityState =
  | "candidate"
  | "needs_review"
  | "qualified"
  | "monitoring";

export interface OpportunityListItem {
  id: string;
  organization: string;
  country: string;
  family: OpportunityFamily;
  recommendedOffer: string;
  score: number;
  confidence: number;
  trigger: string;
  evidenceAge: string;
  relevantRoles: readonly string[];
  state: OpportunityState;
  nextAction: string;
  warning?: string;
}
