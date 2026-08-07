import type { RelationshipQuery } from "./api";
import type {
  RelationshipEvidenceClass,
  RelationshipLinkStatus,
  RelationshipRole,
  RelationshipSourceKind,
  RelationshipStatus,
} from "./types";

export const relationshipStatuses = [
  "under_review",
  "claimed",
  "inferred",
  "active",
  "historical",
  "disputed",
  "corrected",
  "retracted",
  "stale",
] as const satisfies readonly RelationshipStatus[];

export const relationshipRoles = [
  "provider",
  "customer",
  "partner",
  "supplier",
  "reseller",
  "distributor",
  "integrator",
  "auditor",
  "insurer",
  "mssp_mdr",
  "cloud_hosting_provider",
  "technology_vendor",
  "subcontractor",
  "other",
] as const satisfies readonly RelationshipRole[];

export const evidenceClasses = [
  "claimed",
  "observed",
  "contracted",
  "historical",
  "inferred",
] as const satisfies readonly RelationshipEvidenceClass[];

export const sourceKinds = [
  "procurement",
  "official_disclosure",
  "case_study",
  "partner_directory",
  "certificate",
  "passive_observation",
  "regulatory_filing",
  "licensed_metadata",
  "other",
] as const satisfies readonly RelationshipSourceKind[];

export const linkStatuses = [
  "unresolved",
  "exact",
  "candidate",
  "review_required",
  "rejected",
] as const satisfies readonly RelationshipLinkStatus[];

export function parseRelationshipFilters(
  parameters: Record<string, string | string[] | undefined>,
): RelationshipQuery {
  return {
    query: first(parameters.q) || undefined,
    status: parseOption(first(parameters.status), relationshipStatuses),
    role: parseOption(first(parameters.role), relationshipRoles),
    evidenceClass: parseOption(first(parameters.evidence_class), evidenceClasses),
    sourceKind: parseOption(first(parameters.source_kind), sourceKinds),
    sourceLinkStatus: parseOption(
      first(parameters.source_link_status),
      linkStatuses,
    ),
    targetLinkStatus: parseOption(
      first(parameters.target_link_status),
      linkStatuses,
    ),
    organizationId: first(parameters.organization_id) || undefined,
    contractBackedCurrent: parseBoolean(first(parameters.contract_backed_current)),
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
