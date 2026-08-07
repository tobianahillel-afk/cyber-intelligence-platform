import "server-only";

import type {
  ChangeClaimType,
  ChangeDetail,
  ChangeEventStatus,
  ChangeEventType,
  ChangePage,
  ChangeSourceKind,
  OrganizationLinkStatus,
} from "./types";

const DEFAULT_API_BASE_URL = "http://127.0.0.1:8000";
const DEVELOPMENT_CONTROL_TOKEN = "development-control-token";

interface ChangeQuery {
  status?: ChangeEventStatus;
  eventType?: ChangeEventType;
  claimType?: ChangeClaimType;
  sourceKind?: ChangeSourceKind;
  organizationLinkStatus?: OrganizationLinkStatus;
  officiallyConfirmed?: boolean;
  historicalOnly?: boolean;
  query?: string;
  limit?: number;
  offset?: number;
}

export async function loadChangePage(query: ChangeQuery = {}): Promise<ChangePage> {
  const parameters = new URLSearchParams();
  setOptional(parameters, "status", query.status);
  setOptional(parameters, "event_type", query.eventType);
  setOptional(parameters, "claim_type", query.claimType);
  setOptional(parameters, "source_kind", query.sourceKind);
  setOptional(
    parameters,
    "organization_link_status",
    query.organizationLinkStatus,
  );
  setBoolean(parameters, "officially_confirmed", query.officiallyConfirmed);
  setBoolean(parameters, "historical_only", query.historicalOnly);
  setOptional(parameters, "q", query.query);
  parameters.set("limit", String(query.limit ?? 100));
  parameters.set("offset", String(query.offset ?? 0));
  return controlRequestJson<ChangePage>(
    `/v1/corporate-changes?${parameters.toString()}`,
  );
}

export async function loadChangeDetail(eventKey: string): Promise<ChangeDetail> {
  return controlRequestJson<ChangeDetail>(
    `/v1/corporate-changes/${encodeURIComponent(eventKey)}`,
  );
}

function setOptional(
  parameters: URLSearchParams,
  key: string,
  value: string | undefined,
) {
  if (value) {
    parameters.set(key, value);
  }
}

function setBoolean(
  parameters: URLSearchParams,
  key: string,
  value: boolean | undefined,
) {
  if (value !== undefined) {
    parameters.set(key, String(value));
  }
}

function apiBaseUrl(): string {
  return (process.env.CIP_API_BASE_URL ?? DEFAULT_API_BASE_URL).replace(/\/$/, "");
}

function controlPlaneToken(): string {
  const token = process.env.CIP_CONTROL_PLANE_TOKEN;
  if (token) {
    return token;
  }
  if (process.env.NODE_ENV === "production") {
    throw new Error("Production corporate-change access requires CIP_CONTROL_PLANE_TOKEN");
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
  if (!response.ok) {
    throw new Error(await responseMessage(response));
  }
  return (await response.json()) as T;
}

async function responseMessage(response: Response): Promise<string> {
  try {
    const payload = (await response.json()) as { detail?: string };
    return payload.detail ?? `Corporate change API returned ${response.status}`;
  } catch {
    return `Corporate change API returned ${response.status}`;
  }
}
