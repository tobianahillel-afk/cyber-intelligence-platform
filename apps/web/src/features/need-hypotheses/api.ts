import "server-only";

import type {
  CyberServiceFamily,
  NeedHypothesis,
  NeedHypothesisClass,
  NeedHypothesisListResponse,
} from "./types";

const DEFAULT_API_BASE_URL = "http://127.0.0.1:8000";

export class NeedHypothesisApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
  ) {
    super(message);
  }
}

interface NeedHypothesisQuery {
  hypothesisClass?: NeedHypothesisClass;
  serviceFamily?: CyberServiceFamily;
  minConfidence?: number;
  limit?: number;
}

export async function loadNeedHypotheses(
  query: NeedHypothesisQuery = {},
): Promise<NeedHypothesisListResponse> {
  const parameters = new URLSearchParams();
  if (query.hypothesisClass) {
    parameters.set("hypothesis_class", query.hypothesisClass);
  }
  if (query.serviceFamily) {
    parameters.set("service_family", query.serviceFamily);
  }
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

function controlPlaneToken(): string | undefined {
  const token = process.env.CIP_CONTROL_PLANE_TOKEN?.trim();
  return token || undefined;
}

async function requestJson<T>(path: string): Promise<T> {
  const token = controlPlaneToken();
  let response: Response;
  try {
    response = await fetch(`${apiBaseUrl()}${path}`, {
      cache: "no-store",
      headers: {
        accept: "application/json",
        ...(token ? { "X-CIP-Control-Token": token } : {}),
      },
    });
  } catch {
    throw new NeedHypothesisApiError("Need hypothesis API is unavailable", 503);
  }
  if (!response.ok) {
    throw new NeedHypothesisApiError(await responseMessage(response), response.status);
  }
  return (await response.json()) as T;
}

async function responseMessage(response: Response): Promise<string> {
  try {
    const payload = (await response.json()) as { detail?: string };
    return payload.detail ?? `Need hypothesis API returned ${response.status}`;
  } catch {
    return `Need hypothesis API returned ${response.status}`;
  }
}
