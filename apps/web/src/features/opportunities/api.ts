import type { OpportunityDetail, OpportunityPage, OpportunityState } from "./types";

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

function apiBaseUrl(): string {
  return (process.env.CIP_API_BASE_URL ?? DEFAULT_API_BASE_URL).replace(/\/$/, "");
}

async function requestJson<T>(path: string): Promise<T> {
  const response = await fetch(`${apiBaseUrl()}${path}`, {
    cache: "no-store",
    headers: { accept: "application/json" },
  });
  if (!response.ok) {
    throw new OpportunityApiError(
      `Opportunity API returned ${response.status}`,
      response.status,
    );
  }
  return (await response.json()) as T;
}
