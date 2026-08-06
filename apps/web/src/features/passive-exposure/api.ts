import "server-only";

import type {
  AttributionRisk,
  OrganizationLinkStatus,
  PassiveAssetDetail,
  PassiveAssetKind,
  PassiveAssetPage,
  PassiveObservationState,
} from "./types";

const DEFAULT_API_BASE_URL = "http://127.0.0.1:8000";
const DEVELOPMENT_CONTROL_TOKEN = "development-control-token";

export class PassiveExposureApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
  ) {
    super(message);
  }
}

interface PassiveAssetQuery {
  assetKind?: PassiveAssetKind;
  state?: PassiveObservationState;
  organizationLinkStatus?: OrganizationLinkStatus;
  attributionRisk?: AttributionRisk;
  organizationId?: string;
  active?: boolean;
  historicalOnly?: boolean;
  hasConflict?: boolean;
  query?: string;
  limit?: number;
  offset?: number;
}

export async function loadPassiveAssetPage(
  query: PassiveAssetQuery = {},
): Promise<PassiveAssetPage> {
  const parameters = new URLSearchParams();
  setOptional(parameters, "asset_kind", query.assetKind);
  setOptional(parameters, "state", query.state);
  setOptional(
    parameters,
    "organization_link_status",
    query.organizationLinkStatus,
  );
  setOptional(parameters, "attribution_risk", query.attributionRisk);
  setOptional(parameters, "organization_id", query.organizationId);
  setBoolean(parameters, "active", query.active);
  setBoolean(parameters, "historical_only", query.historicalOnly);
  setBoolean(parameters, "has_conflict", query.hasConflict);
  setOptional(parameters, "q", query.query);
  parameters.set("limit", String(query.limit ?? 100));
  parameters.set("offset", String(query.offset ?? 0));
  return controlRequestJson<PassiveAssetPage>(
    `/v1/passive-assets?${parameters.toString()}`,
  );
}

export async function loadPassiveAssetDetail(
  assetId: string,
): Promise<PassiveAssetDetail> {
  return controlRequestJson<PassiveAssetDetail>(
    `/v1/passive-assets/${encodeURIComponent(assetId)}`,
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
    throw new PassiveExposureApiError(
      "Production passive exposure access requires CIP_CONTROL_PLANE_TOKEN",
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
    throw new PassiveExposureApiError("Passive exposure API is unavailable", 503);
  }
  if (!response.ok) {
    throw new PassiveExposureApiError(
      await responseMessage(response),
      response.status,
    );
  }
  return (await response.json()) as T;
}

async function responseMessage(response: Response): Promise<string> {
  try {
    const payload = (await response.json()) as { detail?: string };
    return payload.detail ?? `Passive exposure API returned ${response.status}`;
  } catch {
    return `Passive exposure API returned ${response.status}`;
  }
}
