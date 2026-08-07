import type {
  ChangeClaimType,
  ChangeEventStatus,
  ChangeEventType,
  ChangeSourceKind,
  OrganizationLinkStatus,
} from "./types";

export const changeStatuses = [
  "under_review",
  "speculative",
  "reported",
  "confirmed",
  "disputed",
  "corrected",
  "retracted",
  "stale",
] as const satisfies readonly ChangeEventStatus[];

export const changeEventTypes = [
  "acquisition",
  "leadership",
  "funding",
  "restructuring",
  "geographic_expansion",
  "cloud_digital_program",
  "regulatory_action",
  "breach",
  "audit",
  "certification",
  "security_commitment",
  "other",
] as const satisfies readonly ChangeEventType[];

export const changeClaimTypes = [
  "confirmation",
  "report",
  "speculation",
  "dispute",
  "correction",
  "retraction",
] as const satisfies readonly ChangeClaimType[];

export const changeSourceKinds = [
  "official_filing",
  "regulator",
  "company",
  "media",
  "analyst",
  "other",
] as const satisfies readonly ChangeSourceKind[];

export const organizationLinkStatuses = [
  "unresolved",
  "exact",
  "candidate",
  "review_required",
  "rejected",
] as const satisfies readonly OrganizationLinkStatus[];

export interface ChangeFilterValues {
  query: string;
  status?: ChangeEventStatus;
  eventType?: ChangeEventType;
  claimType?: ChangeClaimType;
  sourceKind?: ChangeSourceKind;
  organizationLinkStatus?: OrganizationLinkStatus;
  officiallyConfirmed?: boolean;
  historicalOnly?: boolean;
}

export function parseChangeFilters(
  parameters: Record<string, string | string[] | undefined>,
): ChangeFilterValues {
  return {
    query: first(parameters.q),
    status: parseOption(first(parameters.status), changeStatuses),
    eventType: parseOption(first(parameters.event_type), changeEventTypes),
    claimType: parseOption(first(parameters.claim_type), changeClaimTypes),
    sourceKind: parseOption(first(parameters.source_kind), changeSourceKinds),
    organizationLinkStatus: parseOption(
      first(parameters.organization_link_status),
      organizationLinkStatuses,
    ),
    officiallyConfirmed: parseBoolean(first(parameters.officially_confirmed)),
    historicalOnly: parseBoolean(first(parameters.historical_only)),
  };
}

function first(value: string | string[] | undefined): string {
  return (Array.isArray(value) ? value[0] : value) ?? "";
}

function parseOption<T extends string>(
  value: string,
  options: readonly T[],
): T | undefined {
  return options.find((option) => option === value);
}

function parseBoolean(value: string): boolean | undefined {
  if (value === "true") return true;
  if (value === "false") return false;
  return undefined;
}
