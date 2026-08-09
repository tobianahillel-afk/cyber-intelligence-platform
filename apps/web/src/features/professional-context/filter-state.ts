import type { ProfessionalPeopleQuery } from "./api";

const EMPLOYMENT_STATES = new Set([
  "current",
  "historical",
  "stale",
  "disputed",
  "retracted",
  "unknown",
]);
const REVIEW_STATES = new Set([
  "unreviewed",
  "review_required",
  "confirmed",
  "rejected",
]);
const LAWFUL_BASES = new Set([
  "consent",
  "contract",
  "legal_obligation",
  "legitimate_interests",
  "public_task",
  "review_required",
]);

export function parseProfessionalFilters(
  raw: Record<string, string | string[] | undefined>,
): ProfessionalPeopleQuery {
  const employmentState = first(raw.employment_state);
  const reviewState = first(raw.review_state);
  const lawfulBasis = first(raw.lawful_basis);
  return {
    organizationId: first(raw.organization_id),
    employmentState: allowed(employmentState, EMPLOYMENT_STATES),
    reviewState: allowed(reviewState, REVIEW_STATES),
    lawfulBasis: allowed(lawfulBasis, LAWFUL_BASES),
    query: first(raw.q),
    includeSuppressed: parseBoolean(first(raw.include_suppressed)),
    includeDeleted: parseBoolean(first(raw.include_deleted)),
    limit: 100,
    offset: 0,
  };
}

function first(value: string | string[] | undefined): string | undefined {
  return Array.isArray(value) ? value[0] : value;
}

function allowed(value: string | undefined, allowedValues: Set<string>): string | undefined {
  return value && allowedValues.has(value) ? value : undefined;
}

function parseBoolean(value: string | undefined): boolean | undefined {
  if (value === "true") return true;
  if (value === "false") return false;
  return undefined;
}
