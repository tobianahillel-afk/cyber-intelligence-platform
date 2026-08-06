import "server-only";

import type {
  ExploitationKind,
  VulnerabilityDetail,
  VulnerabilityPage,
  VulnerabilitySource,
  VulnerabilityStatus,
} from "./types";

const DEFAULT_API_BASE_URL = "http://127.0.0.1:8000";
const DEVELOPMENT_CONTROL_TOKEN = "development-control-token";

export class VulnerabilityApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
  ) {
    super(message);
  }
}

interface VulnerabilityQuery {
  status?: VulnerabilityStatus;
  source?: VulnerabilitySource;
  exploitationKind?: ExploitationKind;
  query?: string;
  limit?: number;
  offset?: number;
}

export async function loadVulnerabilityPage(
  query: VulnerabilityQuery = {},
): Promise<VulnerabilityPage> {
  const parameters = new URLSearchParams();
  setOptional(parameters, "status", query.status);
  setOptional(parameters, "source", query.source);
  setOptional(parameters, "exploitation_kind", query.exploitationKind);
  setOptional(parameters, "q", query.query);
  parameters.set("limit", String(query.limit ?? 100));
  parameters.set("offset", String(query.offset ?? 0));
  return controlRequestJson<VulnerabilityPage>(
    `/v1/vulnerabilities?${parameters.toString()}`,
  );
}

export async function loadVulnerabilityDetail(
  identifier: string,
): Promise<VulnerabilityDetail> {
  return controlRequestJson<VulnerabilityDetail>(
    `/v1/vulnerabilities/${encodeURIComponent(identifier)}`,
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

function apiBaseUrl(): string {
  return (process.env.CIP_API_BASE_URL ?? DEFAULT_API_BASE_URL).replace(/\/$/, "");
}

function controlPlaneToken(): string {
  const token = process.env.CIP_CONTROL_PLANE_TOKEN;
  if (token) {
    return token;
  }
  if (process.env.NODE_ENV === "production") {
    throw new VulnerabilityApiError(
      "Production vulnerability access requires CIP_CONTROL_PLANE_TOKEN",
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
    throw new VulnerabilityApiError("Vulnerability API is unavailable", 503);
  }
  if (!response.ok) {
    throw new VulnerabilityApiError(await responseMessage(response), response.status);
  }
  return (await response.json()) as T;
}

async function responseMessage(response: Response): Promise<string> {
  try {
    const payload = (await response.json()) as { detail?: string };
    return payload.detail ?? `Vulnerability API returned ${response.status}`;
  } catch {
    return `Vulnerability API returned ${response.status}`;
  }
}
