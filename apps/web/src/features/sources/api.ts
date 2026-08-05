import "server-only";

import type {
  PriorityRefreshResult,
  ProviderOnboarding,
  ProviderOnboardingPage,
  ProviderOnboardingState,
  SourcePortfolioEntry,
  SourcePortfolioPage,
} from "./types";

const DEFAULT_API_BASE_URL = "http://127.0.0.1:8000";
const DEVELOPMENT_CONTROL_TOKEN = "development-control-token";

export class ProviderOnboardingApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
  ) {
    super(message);
  }
}

interface ActorPayload {
  actor: string;
}

interface HumanCheckpointPayload extends ActorPayload {
  state: ProviderOnboardingState;
  note?: string;
}

interface SecretReferencePayload extends ActorPayload {
  name: string;
  reference: string;
}

export async function loadProviderCatalog(): Promise<ProviderOnboardingPage> {
  return requestJson<ProviderOnboardingPage>("/v1/provider-onboarding/providers");
}

export async function loadSourcePortfolio(): Promise<SourcePortfolioPage> {
  return controlRequestJson<SourcePortfolioPage>("/v1/source-portfolio/sources");
}

export async function requestSourcePriorityRefresh(
  sourceId: string,
  payload: ActorPayload,
): Promise<PriorityRefreshResult> {
  return controlRequestJson<PriorityRefreshResult>(
    `/v1/source-portfolio/sources/${encodeURIComponent(sourceId)}/priority-refresh`,
    { method: "POST", body: JSON.stringify(payload) },
  );
}

export async function changeSourcePortfolioState(
  sourceId: string,
  action: "pause" | "resume" | "disable" | "enable",
  payload: ActorPayload,
): Promise<SourcePortfolioEntry> {
  return controlRequestJson<SourcePortfolioEntry>(
    `/v1/source-portfolio/sources/${encodeURIComponent(sourceId)}/${action}`,
    { method: "POST", body: JSON.stringify(payload) },
  );
}

export async function cancelSourceBackfill(
  sourceId: string,
  payload: ActorPayload,
): Promise<SourcePortfolioEntry> {
  return controlRequestJson<SourcePortfolioEntry>(
    `/v1/source-portfolio/sources/${encodeURIComponent(sourceId)}/backfills/cancel`,
    { method: "POST", body: JSON.stringify(payload) },
  );
}

export async function startProvider(
  sourceId: string,
  payload: ActorPayload,
): Promise<ProviderOnboarding> {
  return postProvider(sourceId, "start", payload);
}

export async function recordHumanCheckpoint(
  sourceId: string,
  payload: HumanCheckpointPayload,
): Promise<ProviderOnboarding> {
  return postProvider(sourceId, "human-checkpoint", {
    actor: payload.actor,
    state: payload.state,
    note: payload.note || null,
  });
}

export async function registerSecretReference(
  sourceId: string,
  payload: SecretReferencePayload,
): Promise<ProviderOnboarding> {
  return postProvider(sourceId, "secret-reference", payload);
}

export async function verifyProvider(
  sourceId: string,
  payload: ActorPayload,
): Promise<ProviderOnboarding> {
  return postProvider(sourceId, "verify", payload);
}

export async function revokeProvider(
  sourceId: string,
  payload: ActorPayload,
): Promise<ProviderOnboarding> {
  return postProvider(sourceId, "revoke", payload);
}

async function postProvider<T extends object>(
  sourceId: string,
  action: string,
  payload: T,
): Promise<ProviderOnboarding> {
  return requestJson<ProviderOnboarding>(
    `/v1/provider-onboarding/providers/${encodeURIComponent(sourceId)}/${action}`,
    {
      method: "POST",
      body: JSON.stringify(payload),
    },
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
    throw new ProviderOnboardingApiError(
      "Production source control requires CIP_CONTROL_PLANE_TOKEN",
      500,
    );
  }
  return DEVELOPMENT_CONTROL_TOKEN;
}

async function controlRequestJson<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  headers.set("X-CIP-Control-Token", controlPlaneToken());
  return requestJson<T>(path, { ...init, headers });
}

async function requestJson<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  headers.set("accept", "application/json");
  if (init.body) {
    headers.set("content-type", "application/json");
  }

  let response: Response;
  try {
    response = await fetch(`${apiBaseUrl()}${path}`, {
      ...init,
      cache: "no-store",
      headers,
    });
  } catch {
    throw new ProviderOnboardingApiError("Source control API is unavailable", 503);
  }
  if (!response.ok) {
    throw new ProviderOnboardingApiError(await responseMessage(response), response.status);
  }
  return (await response.json()) as T;
}

async function responseMessage(response: Response): Promise<string> {
  try {
    const payload = (await response.json()) as { detail?: string };
    return payload.detail ?? `Source control API returned ${response.status}`;
  } catch {
    return `Source control API returned ${response.status}`;
  }
}
