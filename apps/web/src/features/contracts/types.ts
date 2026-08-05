export type ContractStatus = "awarded" | "active" | "completed" | "cancelled" | "unknown";
export type DateBasis = "published" | "derived" | "estimated" | "unknown";

export interface ProcurementContract {
  id: string;
  procedure_id: string;
  buyer_organization_id: string;
  buyer_name: string;
  title: string;
  status: ContractStatus;
  amount_value: string | null;
  amount_upper_value: string | null;
  currency: string | null;
  amount_type: string | null;
  award_date: string | null;
  conclusion_date: string | null;
  conclusion_date_basis: DateBasis;
  notification_date: string | null;
  notification_date_basis: DateBasis;
  start_date: string | null;
  start_date_basis: DateBasis;
  end_date: string | null;
  end_date_basis: DateBasis;
  renewal_date: string | null;
  renewal_date_basis: DateBasis;
  confidence: number;
  provider_names: string[];
  service_families: string[];
  source_ids: string[];
  updated_at: string;
}

export interface ProcurementContractPage {
  items: ProcurementContract[];
  total: number;
  limit: number;
  offset: number;
  generated_at: string;
}

export interface ProcurementParty {
  role: string;
  published_name: string;
  resolution_status: string;
  confidence: number;
  organization_id: string | null;
  official_identifier: string | null;
}

export interface ProcurementServiceFamily {
  family: string;
  matched_terms: string[];
  confidence: number;
}

export interface ProcurementPublication {
  id: string;
  source_id: string;
  source_record_key: string;
  kind: string;
  procedure_status: string;
  title: string;
  source_url: string;
  published_at: string | null;
  collected_at: string;
  details: Record<string, unknown>;
}

export interface ProcurementContractDetail {
  contract: ProcurementContract;
  contract_key: string;
  procedure_key: string;
  procedure_title: string;
  procedure_status: string;
  first_published_at: string | null;
  latest_published_at: string | null;
  parties: ProcurementParty[];
  service_classifications: ProcurementServiceFamily[];
  publications: ProcurementPublication[];
}
