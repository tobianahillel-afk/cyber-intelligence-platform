import "server-only";

import type {
  NeedHypothesis,
  NeedHypothesisClass,
  NeedHypothesisListResponse,
  NeedHypothesisStatus,
} from "./types";

const DEFAULT_API_BASE_URL = "http://127.0.0.1:8000";

interface NeedHypothesisQuery {
  organizationId?: string;
  hypothesisClass?: NeedHypothesisClass;
  status?: NeedHypothesisStatus;
  serviceFamily?: string;
  minConfidence?: number;
  limit?: number;
}

export class NeedHypothesisApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
  }
}

export async function loadNeedHypotheses(
  query: NeedHypothesisQuery = {},
): Promise<NeedHypothesisListResponse> {
  const parameters = new URLSearchParams();
  if (query.organizationId) parameters.set("organization_id", query.organizationId);
  if (query.hypothesisClass) parameters.set("hypothesis_class", query.hypothesisClass);
  if (query.status) parameters.set("status", query.status);
  if (query.serviceFamily) parameters.set("service_family", query.serviceFamily);
  if (query.minConfidence !== undefined) {
    parameters.set("min_confidence", String(query.minConfidence));
  }
  parameters.set("limit", String(query.limit ?? 100));
  return requestJson<NeedHypothesisListResponse>(
    `/v1/need-hypotheses?${parameters.toString()}`,
  );
}

export async function loadNeedHypothesis(id: string): Promise<NeedHypothesis> {
  return requestJson<NeedHypothesis>(`/v1/need-hypotheses/${encodeURIComponent(id)}`);
}

function apiBaseUrl(): string {
  return (process.env.CIP_API_BASE_URL ?? DEFAULT_API_BASE_URL).replace(/\/$/, "");
}

async function requestJson<T>(path: string): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${apiBaseUrl()}${path}`, {
      cache: "no-store",
      headers: { accept: "application/json" },
    });
  } catch {
    throw new NeedHypothesisApiError("Need-hypothesis API is unavailable", 503);
  }
  if (!response.ok) {
    throw new NeedHypothesisApiError(await responseMessage(response), response.status);
  }
  return (await response.json()) as T;
}

async function responseMessage(response: Response): Promise<string> {
  try {
    const payload = (await response.json()) as { detail?: string };
    return payload.detail ?? `Need-hypothesis API returned ${response.status}`;
  } catch {
    return `Need-hypothesis API returned ${response.status}`;
  }
}
