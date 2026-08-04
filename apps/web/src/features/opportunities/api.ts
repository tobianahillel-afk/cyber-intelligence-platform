import "server-only";

import type {
  OpportunityDetail,
  OpportunityPage,
  OpportunityReviewAction,
  OpportunityState,
} from "./types";

const DEFAULT_API_BASE_URL = "http://127.0.0.1:8000";

export class OpportunityApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
  ) {
    super(message);
  }
}

interface OpportunityQuery {
  states?: readonly OpportunityState[];
  minScore?: number;
  limit?: number;
  offset?: number;
}

interface ReviewPayload {
  action: OpportunityReviewAction;
  actor: string;
  note?: string;
  snoozedUntil?: string;
}

interface ComponentOverridePayload {
  actor: string;
  value?: number;
  weight?: number;
  reason?: string;
}

export async function loadOpportunityPage(query: OpportunityQuery = {}): Promise<OpportunityPage> {
  const parameters = new URLSearchParams();
  for (const state of query.states ?? []) {
    parameters.append("state", state);
  }
  if (query.minScore !== undefined) {
    parameters.set("min_score", String(query.minScore));
  }
  parameters.set("limit", String(query.limit ?? 50));
  parameters.set("offset", String(query.offset ?? 0));
  return requestJson<OpportunityPage>(`/v1/opportunities?${parameters.toString()}`);
}

export async function loadOpportunityDetail(id: string): Promise<OpportunityDetail> {
  return requestJson<OpportunityDetail>(`/v1/opportunities/${encodeURIComponent(id)}`);
}

export async function submitOpportunityReview(
  id: string,
  payload: ReviewPayload,
): Promise<void> {
  await requestJson(`/v1/opportunities/${encodeURIComponent(id)}/review`, {
    method: "POST",
    body: JSON.stringify({
      action: payload.action,
      actor: payload.actor,
      note: payload.note || null,
      snoozed_until: payload.snoozedUntil || null,
    }),
  });
}

export async function submitComponentOverride(
  opportunityId: string,
  componentId: string,
  payload: ComponentOverridePayload,
): Promise<void> {
  await requestJson(
    `/v1/opportunities/${encodeURIComponent(opportunityId)}/score-components/${encodeURIComponent(componentId)}`,
    {
      method: "PATCH",
      body: JSON.stringify({
        actor: payload.actor,
        value: payload.value,
        weight: payload.weight,
        reason: payload.reason || null,
      }),
    },
  );
}

function apiBaseUrl(): string {
  return (process.env.CIP_API_BASE_URL ?? DEFAULT_API_BASE_URL).replace(/\/$/, "");
}

async function requestJson<T>(path: string, init: RequestInit = {}): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${apiBaseUrl()}${path}`, {
      ...init,
      cache: "no-store",
      headers: {
        accept: "application/json",
        ...(init.body ? { "content-type": "application/json" } : {}),
        ...init.headers,
      },
    });
  } catch (error) {
    throw new OpportunityApiError("Opportunity API is unavailable", 503, {
      cause: error,
    });
  }
  if (!response.ok) {
    throw new OpportunityApiError(
      await responseMessage(response),
      response.status,
    );
  }
  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}

async function responseMessage(response: Response): Promise<string> {
  try {
    const payload = (await response.json()) as { detail?: string };
    return payload.detail ?? `Opportunity API returned ${response.status}`;
  } catch {
    return `Opportunity API returned ${response.status}`;
  }
}
