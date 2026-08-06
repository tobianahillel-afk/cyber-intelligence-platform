import "server-only";

import type {
  IncidentClaimType,
  IncidentDetail,
  IncidentPage,
  IncidentSourceKind,
  IncidentStatus,
  IncidentType,
  OrganizationLinkStatus,
} from "./types";

const DEFAULT_API_BASE_URL = "http://127.0.0.1:8000";
const DEVELOPMENT_CONTROL_TOKEN = "development-control-token";

export class IncidentApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
  ) {
    super(message);
  }
}

interface IncidentQuery {
  status?: IncidentStatus;
  incidentType?: IncidentType;
  claimType?: IncidentClaimType;
  sourceKind?: IncidentSourceKind;
  organizationLinkStatus?: OrganizationLinkStatus;
  officiallyConfirmed?: boolean;
  historicalOnly?: boolean;
  query?: string;
  limit?: number;
  offset?: number;
}

export async function loadIncidentPage(
  query: IncidentQuery = {},
): Promise<IncidentPage> {
  const parameters = new URLSearchParams();
  setOptional(parameters, "status", query.status);
  setOptional(parameters, "incident_type", query.incidentType);
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
  return controlRequestJson<IncidentPage>(
    `/v1/incidents?${parameters.toString()}`,
  );
}

export async function loadIncidentDetail(
  incidentKey: string,
): Promise<IncidentDetail> {
  return controlRequestJson<IncidentDetail>(
    `/v1/incidents/${encodeURIComponent(incidentKey)}`,
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
    throw new IncidentApiError(
      "Production incident access requires CIP_CONTROL_PLANE_TOKEN",
      500,
    );
  }
  return DEVELOPMENT_CONTROL_TOKEN;
}

async function controlRequestJson<T>(path: string): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${apiBaseUrl()}${path}`, {
      cache: "no-store",
      headers: {
        accept: "application/json",
        "X-CIP-Control-Token": controlPlaneToken(),
      },
    });
  } catch {
    throw new IncidentApiError("Incident API is unavailable", 503);
  }
  if (!response.ok) {
    throw new IncidentApiError(await responseMessage(response), response.status);
  }
  return (await response.json()) as T;
}

async function responseMessage(response: Response): Promise<string> {
  try {
    const payload = (await response.json()) as { detail?: string };
    return payload.detail ?? `Incident API returned ${response.status}`;
  } catch {
    return `Incident API returned ${response.status}`;
  }
}
