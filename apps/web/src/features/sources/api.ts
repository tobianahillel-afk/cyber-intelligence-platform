import "server-only";

import type {
  ProviderOnboarding,
  ProviderOnboardingPage,
  ProviderOnboardingState,
} from "./types";

const DEFAULT_API_BASE_URL = "http://127.0.0.1:8000";

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
  } catch {
    throw new ProviderOnboardingApiError("Provider onboarding API is unavailable", 503);
  }
  if (!response.ok) {
    throw new ProviderOnboardingApiError(await responseMessage(response), response.status);
  }
  return (await response.json()) as T;
}

async function responseMessage(response: Response): Promise<string> {
  try {
    const payload = (await response.json()) as { detail?: string };
    return payload.detail ?? `Provider onboarding API returned ${response.status}`;
  } catch {
    return `Provider onboarding API returned ${response.status}`;
  }
}
