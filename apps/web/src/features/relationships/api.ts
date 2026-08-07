import "server-only";

import type {
  RelationshipDetail,
  RelationshipEvidenceClass,
  RelationshipLinkStatus,
  RelationshipPage,
  RelationshipRole,
  RelationshipSourceKind,
  RelationshipStatus,
} from "./types";

const DEFAULT_API_BASE_URL = "http://127.0.0.1:8000";
const DEVELOPMENT_CONTROL_TOKEN = "development-control-token";

export interface RelationshipQuery {
  status?: RelationshipStatus;
  role?: RelationshipRole;
  evidenceClass?: RelationshipEvidenceClass;
  sourceKind?: RelationshipSourceKind;
  sourceLinkStatus?: RelationshipLinkStatus;
  targetLinkStatus?: RelationshipLinkStatus;
  organizationId?: string;
  contractBackedCurrent?: boolean;
  historicalOnly?: boolean;
  query?: string;
  limit?: number;
  offset?: number;
}

export async function loadRelationshipPage(
  query: RelationshipQuery = {},
): Promise<RelationshipPage> {
  const parameters = new URLSearchParams();
  setOptional(parameters, "status", query.status);
  setOptional(parameters, "role", query.role);
  setOptional(parameters, "evidence_class", query.evidenceClass);
  setOptional(parameters, "source_kind", query.sourceKind);
  setOptional(parameters, "source_link_status", query.sourceLinkStatus);
  setOptional(parameters, "target_link_status", query.targetLinkStatus);
  setOptional(parameters, "organization_id", query.organizationId);
  setBoolean(parameters, "contract_backed_current", query.contractBackedCurrent);
  setBoolean(parameters, "historical_only", query.historicalOnly);
  setOptional(parameters, "q", query.query);
  parameters.set("limit", String(query.limit ?? 100));
  parameters.set("offset", String(query.offset ?? 0));
  return controlRequestJson<RelationshipPage>(
    `/v1/relationships?${parameters.toString()}`,
  );
}

export async function loadRelationshipDetail(
  relationshipKey: string,
): Promise<RelationshipDetail> {
  return controlRequestJson<RelationshipDetail>(
    `/v1/relationships/${encodeURIComponent(relationshipKey)}`,
  );
}

function setOptional(
  parameters: URLSearchParams,
  key: string,
  value: string | undefined,
) {
  if (value) parameters.set(key, value);
}

function setBoolean(
  parameters: URLSearchParams,
  key: string,
  value: boolean | undefined,
) {
  if (value !== undefined) parameters.set(key, String(value));
}

function apiBaseUrl(): string {
  return (process.env.CIP_API_BASE_URL ?? DEFAULT_API_BASE_URL).replace(/\/$/, "");
}

function controlPlaneToken(): string {
  const token = process.env.CIP_CONTROL_PLANE_TOKEN;
  if (token) return token;
  if (process.env.NODE_ENV === "production") {
    throw new Error("Production relationship access requires CIP_CONTROL_PLANE_TOKEN");
  }
  return DEVELOPMENT_CONTROL_TOKEN;
}

async function controlRequestJson<T>(path: string): Promise<T> {
  const response = await fetch(`${apiBaseUrl()}${path}`, {
    cache: "no-store",
    headers: {
      accept: "application/json",
      "X-CIP-Control-Token": controlPlaneToken(),
    },
  });
  if (!response.ok) throw new Error(await responseMessage(response));
  return (await response.json()) as T;
}

async function responseMessage(response: Response): Promise<string> {
  try {
    const payload = (await response.json()) as { detail?: string };
    return payload.detail ?? `Relationship API returned ${response.status}`;
  } catch {
    return `Relationship API returned ${response.status}`;
  }
}
