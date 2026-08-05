import "server-only";

import type {
  ContractStatus,
  ProcurementContractDetail,
  ProcurementContractPage,
} from "./types";

const DEFAULT_API_BASE_URL = "http://127.0.0.1:8000";
const DEVELOPMENT_CONTROL_TOKEN = "development-control-token";

export class ContractApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
  ) {
    super(message);
  }
}

interface ContractQuery {
  statuses?: readonly ContractStatus[];
  family?: string;
  renewalFrom?: string;
  renewalTo?: string;
  limit?: number;
  offset?: number;
}

export async function loadContractPage(
  query: ContractQuery = {},
): Promise<ProcurementContractPage> {
  const parameters = new URLSearchParams();
  for (const status of query.statuses ?? []) {
    parameters.append("status", status);
  }
  if (query.family) {
    parameters.set("family", query.family);
  }
  if (query.renewalFrom) {
    parameters.set("renewal_from", query.renewalFrom);
  }
  if (query.renewalTo) {
    parameters.set("renewal_to", query.renewalTo);
  }
  parameters.set("limit", String(query.limit ?? 100));
  parameters.set("offset", String(query.offset ?? 0));
  return controlRequestJson<ProcurementContractPage>(
    `/v1/procurement-history/contracts?${parameters.toString()}`,
  );
}

export async function loadContractDetail(id: string): Promise<ProcurementContractDetail> {
  return controlRequestJson<ProcurementContractDetail>(
    `/v1/procurement-history/contracts/${encodeURIComponent(id)}`,
  );
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
    throw new ContractApiError(
      "Production contract access requires CIP_CONTROL_PLANE_TOKEN",
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
    throw new ContractApiError("Procurement history API is unavailable", 503);
  }
  if (!response.ok) {
    throw new ContractApiError(await responseMessage(response), response.status);
  }
  return (await response.json()) as T;
}

async function responseMessage(response: Response): Promise<string> {
  try {
    const payload = (await response.json()) as { detail?: string };
    return payload.detail ?? `Procurement history API returned ${response.status}`;
  } catch {
    return `Procurement history API returned ${response.status}`;
  }
}
