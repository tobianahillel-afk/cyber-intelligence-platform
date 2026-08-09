import "server-only";

import type {
  ConditionalProviderDetail,
  ConditionalProviderPage,
  ConditionalProviderValue,
  ConditionalRuntimeControl,
  ConditionalExecutionDecision,
} from "./types";

const DEFAULT_API_BASE_URL = "http://127.0.0.1:8000";
const DEVELOPMENT_CONTROL_TOKEN = "development-control-token";

export class ConditionalIntegrationApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
  ) {
    super(message);
  }
}

export interface ApprovalPayload {
  provider_kind: string;
  access_method: string;
  state: string;
  authorization_document_reference: string | null;
  licence_reference: string | null;
  terms_reference: string | null;
  terms_state: string;
  approved_scopes: string[];
  approved_fields: string[];
  approved_purposes: string[];
  approved_data_categories: string[];
  retention_days: number | null;
  automated_collection_allowed: boolean;
  account_reference: string | null;
  reviewed_at: string | null;
  review_due_at: string | null;
  expires_at: string | null;
  revoked_at: string | null;
  paused_reason: string | null;
  actor: string;
  change_reason: string;
}

export interface ControlPayload {
  action: string;
  actor: string;
  reason: string;
}

export interface EligibilityPayload {
  access_method: string;
  purpose: string;
  data_category: string;
  target_url: string;
  requested_scopes: string[];
  requested_fields: string[];
  retention_days: number;
  automated: boolean;
  store_raw_content: boolean;
  account_reference: string | null;
}

export async function loadConditionalProviders(): Promise<ConditionalProviderPage> {
  return controlRequest<ConditionalProviderPage>("/v1/conditional-integrations/providers");
}

export async function loadConditionalProvider(
  sourceId: string,
): Promise<ConditionalProviderDetail | null> {
  try {
    return await controlRequest<ConditionalProviderDetail>(
      `/v1/conditional-integrations/providers/${encodeURIComponent(sourceId)}`,
    );
  } catch (error) {
    if (error instanceof ConditionalIntegrationApiError && error.status === 404) {
      return null;
    }
    throw error;
  }
}

export async function loadConditionalProviderValue(
  sourceId: string,
): Promise<ConditionalProviderValue | null> {
  try {
    return await controlRequest<ConditionalProviderValue>(
      `/v1/conditional-integrations/providers/${encodeURIComponent(sourceId)}/value`,
    );
  } catch (error) {
    if (error instanceof ConditionalIntegrationApiError && error.status === 404) {
      return null;
    }
    throw error;
  }
}

export async function saveConditionalApproval(
  sourceId: string,
  payload: ApprovalPayload,
): Promise<void> {
  await controlRequest(
    `/v1/conditional-integrations/providers/${encodeURIComponent(sourceId)}/approval`,
    { method: "PUT", body: JSON.stringify(payload) },
  );
}

export async function changeConditionalControl(
  sourceId: string,
  payload: ControlPayload,
): Promise<ConditionalRuntimeControl> {
  return controlRequest<ConditionalRuntimeControl>(
    `/v1/conditional-integrations/providers/${encodeURIComponent(sourceId)}/control`,
    { method: "POST", body: JSON.stringify(payload) },
  );
}

export async function evaluateConditionalEligibility(
  sourceId: string,
  payload: EligibilityPayload,
): Promise<ConditionalExecutionDecision> {
  return controlRequest<ConditionalExecutionDecision>(
    `/v1/conditional-integrations/providers/${encodeURIComponent(sourceId)}/eligibility`,
    { method: "POST", body: JSON.stringify(payload) },
  );
}

function apiBaseUrl(): string {
  return (process.env.CIP_API_BASE_URL ?? DEFAULT_API_BASE_URL).replace(/\/$/, "");
}

function controlPlaneToken(): string {
  const token = process.env.CIP_CONTROL_PLANE_TOKEN;
  if (token) return token;
  if (process.env.NODE_ENV === "production") {
    throw new ConditionalIntegrationApiError(
      "Production conditional integration control requires CIP_CONTROL_PLANE_TOKEN",
      500,
    );
  }
  return DEVELOPMENT_CONTROL_TOKEN;
}

async function controlRequest<T = object>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  headers.set("accept", "application/json");
  headers.set("X-CIP-Control-Token", controlPlaneToken());
  if (init.body) headers.set("content-type", "application/json");
  let response: Response;
  try {
    response = await fetch(`${apiBaseUrl()}${path}`, {
      ...init,
      cache: "no-store",
      headers,
    });
  } catch {
    throw new ConditionalIntegrationApiError("Conditional integration API unavailable", 503);
  }
  if (!response.ok) {
    throw new ConditionalIntegrationApiError(await responseMessage(response), response.status);
  }
  return (await response.json()) as T;
}

async function responseMessage(response: Response): Promise<string> {
  try {
    const payload = (await response.json()) as { detail?: string };
    return payload.detail ?? `Conditional integration API returned ${response.status}`;
  } catch {
    return `Conditional integration API returned ${response.status}`;
  }
}
