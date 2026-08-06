import "server-only";

import type {
  PublicClaimType,
  PublicResourceDetail,
  PublicResourceKind,
  PublicResourcePage,
  ResourceAccessState,
  ResourceRetrievalState,
} from "./types";

const DEFAULT_API_BASE_URL = "http://127.0.0.1:8000";
const DEVELOPMENT_CONTROL_TOKEN = "development-control-token";

export class PublicFootprintApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
  ) {
    super(message);
  }
}

interface PublicFootprintQuery {
  organizationId?: string;
  sourceId?: string;
  kind?: PublicResourceKind;
  accessState?: ResourceAccessState;
  retrievalState?: ResourceRetrievalState;
  claimType?: PublicClaimType;
  query?: string;
  limit?: number;
  offset?: number;
}

export async function loadPublicResourcePage(
  query: PublicFootprintQuery = {},
): Promise<PublicResourcePage> {
  const parameters = new URLSearchParams();
  setOptional(parameters, "organization_id", query.organizationId);
  setOptional(parameters, "source_id", query.sourceId);
  setOptional(parameters, "kind", query.kind);
  setOptional(parameters, "access_state", query.accessState);
  setOptional(parameters, "retrieval_state", query.retrievalState);
  setOptional(parameters, "claim_type", query.claimType);
  setOptional(parameters, "q", query.query);
  parameters.set("limit", String(query.limit ?? 100));
  parameters.set("offset", String(query.offset ?? 0));
  return controlRequestJson<PublicResourcePage>(
    `/v1/public-footprint/resources?${parameters.toString()}`,
  );
}

export async function loadPublicResourceDetail(id: string): Promise<PublicResourceDetail> {
  return controlRequestJson<PublicResourceDetail>(
    `/v1/public-footprint/resources/${encodeURIComponent(id)}`,
  );
}

function setOptional(parameters: URLSearchParams, key: string, value: string | undefined) {
  if (value) {
    parameters.set(key, value);
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
    throw new PublicFootprintApiError(
      "Production public footprint access requires CIP_CONTROL_PLANE_TOKEN",
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
    throw new PublicFootprintApiError("Public footprint API is unavailable", 503);
  }
  if (!response.ok) {
    throw new PublicFootprintApiError(await responseMessage(response), response.status);
  }
  return (await response.json()) as T;
}

async function responseMessage(response: Response): Promise<string> {
  try {
    const payload = (await response.json()) as { detail?: string };
    return payload.detail ?? `Public footprint API returned ${response.status}`;
  } catch {
    return `Public footprint API returned ${response.status}`;
  }
}
