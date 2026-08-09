import "server-only";

import type {
  GraphNodeDetail,
  GraphNodePage,
  GraphNodeType,
  ResolutionCandidateDetail,
  ResolutionCandidatePage,
} from "./types";

const DEFAULT_API_BASE_URL = "http://127.0.0.1:8000";
const DEVELOPMENT_CONTROL_TOKEN = "development-control-token";

export interface GraphNodeQuery {
  nodeType?: GraphNodeType;
  organizationId?: string;
  current?: boolean;
  suppressed?: boolean;
  query?: string;
  limit?: number;
  offset?: number;
}

export interface ResolutionQuery {
  state?: string;
  requiresReview?: boolean;
  limit?: number;
  offset?: number;
}

export interface ResolutionDecisionInput {
  decisionType: "merge" | "reject" | "split" | "override" | "restore";
  actor: string;
  reason: string;
  organizationId?: string;
  reversesDecisionId?: string;
  blastRadiusFingerprint: string;
}

export async function loadGraphNodes(
  query: GraphNodeQuery = {},
): Promise<GraphNodePage> {
  const parameters = new URLSearchParams();
  setOptional(parameters, "node_type", query.nodeType);
  setOptional(parameters, "organization_id", query.organizationId);
  setBoolean(parameters, "current", query.current);
  setBoolean(parameters, "suppressed", query.suppressed);
  setOptional(parameters, "q", query.query);
  parameters.set("limit", String(query.limit ?? 100));
  parameters.set("offset", String(query.offset ?? 0));
  return controlRequestJson<GraphNodePage>(`/v1/graph/nodes?${parameters.toString()}`);
}

export async function loadGraphNodeDetail(
  nodeKey: string,
  asOf?: string,
): Promise<GraphNodeDetail> {
  const parameters = new URLSearchParams();
  setOptional(parameters, "as_of", asOf);
  const suffix = parameters.size ? `?${parameters.toString()}` : "";
  return controlRequestJson<GraphNodeDetail>(
    `/v1/graph/nodes/${encodeURIComponent(nodeKey)}${suffix}`,
  );
}

export async function loadResolutionCandidates(
  query: ResolutionQuery = {},
): Promise<ResolutionCandidatePage> {
  const parameters = new URLSearchParams();
  setOptional(parameters, "state", query.state);
  setBoolean(parameters, "requires_review", query.requiresReview);
  parameters.set("limit", String(query.limit ?? 100));
  parameters.set("offset", String(query.offset ?? 0));
  return controlRequestJson<ResolutionCandidatePage>(
    `/v1/graph/resolution-candidates?${parameters.toString()}`,
  );
}

export async function loadResolutionCandidate(
  candidateId: string,
): Promise<ResolutionCandidateDetail> {
  return controlRequestJson<ResolutionCandidateDetail>(
    `/v1/graph/resolution-candidates/${encodeURIComponent(candidateId)}`,
  );
}

export async function submitResolutionDecision(
  candidateId: string,
  input: ResolutionDecisionInput,
): Promise<ResolutionCandidateDetail> {
  return controlPostJson<ResolutionCandidateDetail>(
    `/v1/graph/resolution-candidates/${encodeURIComponent(candidateId)}/decisions`,
    {
      decision_type: input.decisionType,
      actor: input.actor,
      reason: input.reason,
      organization_id: input.organizationId,
      reverses_decision_id: input.reversesDecisionId,
      blast_radius_fingerprint: input.blastRadiusFingerprint,
    },
  );
}

function setOptional(
  parameters: URLSearchParams,
  key: string,
  value: string | undefined,
) {
  if (value) parameters.set(key, value);
}

function setBoolean(
  parameters: URLSearchParams,
  key: string,
  value: boolean | undefined,
) {
  if (value !== undefined) parameters.set(key, String(value));
}

function apiBaseUrl(): string {
  return (process.env.CIP_API_BASE_URL ?? DEFAULT_API_BASE_URL).replace(/\/$/, "");
}

function controlPlaneToken(): string {
  const token = process.env.CIP_CONTROL_PLANE_TOKEN;
  if (token) return token;
  if (process.env.NODE_ENV === "production") {
    throw new Error("Production graph access requires CIP_CONTROL_PLANE_TOKEN");
  }
  return DEVELOPMENT_CONTROL_TOKEN;
}

async function controlRequestJson<T>(path: string): Promise<T> {
  const response = await fetch(`${apiBaseUrl()}${path}`, {
    cache: "no-store",
    headers: controlHeaders(),
  });
  return parseResponse<T>(response);
}

async function controlPostJson<T>(path: string, body: object): Promise<T> {
  const response = await fetch(`${apiBaseUrl()}${path}`, {
    method: "POST",
    cache: "no-store",
    headers: { ...controlHeaders(), "content-type": "application/json" },
    body: JSON.stringify(body),
  });
  return parseResponse<T>(response);
}

function controlHeaders(): Record<string, string> {
  return {
    accept: "application/json",
    "X-CIP-Control-Token": controlPlaneToken(),
  };
}

async function parseResponse<T>(response: Response): Promise<T> {
  if (!response.ok) throw new Error(await responseMessage(response));
  return (await response.json()) as T;
}

async function responseMessage(response: Response): Promise<string> {
  try {
    const payload = (await response.json()) as { detail?: string };
    return payload.detail ?? `Corporate graph API returned ${response.status}`;
  } catch {
    return `Corporate graph API returned ${response.status}`;
  }
}
