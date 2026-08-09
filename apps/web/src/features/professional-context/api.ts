import "server-only";

import type {
  OrganizationProfessionalMap,
  ProfessionalPersonDetail,
  ProfessionalPersonPage,
} from "./types";

const DEFAULT_API_BASE_URL = "http://127.0.0.1:8000";
const DEVELOPMENT_CONTROL_TOKEN = "development-control-token";

export interface ProfessionalPeopleQuery {
  organizationId?: string;
  employmentState?: string;
  reviewState?: string;
  lawfulBasis?: string;
  query?: string;
  includeSuppressed?: boolean;
  includeDeleted?: boolean;
  limit?: number;
  offset?: number;
}

export async function loadProfessionalPeople(
  query: ProfessionalPeopleQuery = {},
): Promise<ProfessionalPersonPage> {
  const parameters = new URLSearchParams();
  setOptional(parameters, "organization_id", query.organizationId);
  setOptional(parameters, "employment_state", query.employmentState);
  setOptional(parameters, "review_state", query.reviewState);
  setOptional(parameters, "lawful_basis", query.lawfulBasis);
  setOptional(parameters, "q", query.query);
  setBoolean(parameters, "include_suppressed", query.includeSuppressed);
  setBoolean(parameters, "include_deleted", query.includeDeleted);
  parameters.set("limit", String(query.limit ?? 100));
  parameters.set("offset", String(query.offset ?? 0));
  return controlRequestJson<ProfessionalPersonPage>(
    `/v1/professional-context/people?${parameters.toString()}`,
  );
}

export async function loadProfessionalPerson(
  personKey: string,
): Promise<ProfessionalPersonDetail> {
  return controlRequestJson<ProfessionalPersonDetail>(
    `/v1/professional-context/people/${encodeURIComponent(personKey)}`,
  );
}

export async function loadOrganizationProfessionalMap(
  organizationId: string,
): Promise<OrganizationProfessionalMap> {
  return controlRequestJson<OrganizationProfessionalMap>(
    `/v1/professional-context/organizations/${encodeURIComponent(organizationId)}/map`,
  );
}

async function controlRequestJson<T>(path: string): Promise<T> {
  const response = await fetch(`${apiBaseUrl()}${path}`, {
    headers: { "X-CIP-Control-Token": controlToken() },
    cache: "no-store",
  });
  if (!response.ok) {
    throw new Error(`professional context request failed with ${response.status}`);
  }
  return (await response.json()) as T;
}

function apiBaseUrl(): string {
  return (process.env.CIP_API_BASE_URL ?? DEFAULT_API_BASE_URL).replace(/\/$/, "");
}

function controlToken(): string {
  return process.env.CIP_CONTROL_PLANE_TOKEN ?? DEVELOPMENT_CONTROL_TOKEN;
}

function setOptional(
  parameters: URLSearchParams,
  key: string,
  value: string | undefined,
): void {
  if (value) parameters.set(key, value);
}

function setBoolean(
  parameters: URLSearchParams,
  key: string,
  value: boolean | undefined,
): void {
  if (value !== undefined) parameters.set(key, String(value));
}
