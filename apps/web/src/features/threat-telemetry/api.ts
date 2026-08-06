import "server-only";

import type {
  IndicatorState,
  IndicatorType,
  SensorScope,
  TelemetrySourceKind,
  ThreatIndicatorDetail,
  ThreatIndicatorPage,
} from "./types";

const DEFAULT_API_BASE_URL = "http://127.0.0.1:8000";
const DEVELOPMENT_CONTROL_TOKEN = "development-control-token";

export class ThreatTelemetryApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
  ) {
    super(message);
  }
}

interface IndicatorQuery {
  indicatorType?: IndicatorType;
  state?: IndicatorState;
  sourceKind?: TelemetrySourceKind;
  sensorScope?: SensorScope;
  active?: boolean;
  sharedInfrastructure?: boolean;
  historicalOnly?: boolean;
  hasConflict?: boolean;
  query?: string;
  limit?: number;
  offset?: number;
}

export async function loadThreatIndicatorPage(
  query: IndicatorQuery = {},
): Promise<ThreatIndicatorPage> {
  const parameters = new URLSearchParams();
  setOptional(parameters, "indicator_type", query.indicatorType);
  setOptional(parameters, "state", query.state);
  setOptional(parameters, "source_kind", query.sourceKind);
  setOptional(parameters, "sensor_scope", query.sensorScope);
  setBoolean(parameters, "active", query.active);
  setBoolean(parameters, "shared_infrastructure", query.sharedInfrastructure);
  setBoolean(parameters, "historical_only", query.historicalOnly);
  setBoolean(parameters, "has_conflict", query.hasConflict);
  setOptional(parameters, "q", query.query);
  parameters.set("limit", String(query.limit ?? 100));
  parameters.set("offset", String(query.offset ?? 0));
  return controlRequestJson<ThreatIndicatorPage>(
    `/v1/threat-indicators?${parameters.toString()}`,
  );
}

export async function loadThreatIndicatorDetail(
  indicatorId: string,
): Promise<ThreatIndicatorDetail> {
  return controlRequestJson<ThreatIndicatorDetail>(
    `/v1/threat-indicators/${encodeURIComponent(indicatorId)}`,
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

function setBoolean(
  parameters: URLSearchParams,
  key: string,
  value: boolean | undefined,
) {
  if (value !== undefined) {
    parameters.set(key, String(value));
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
    throw new ThreatTelemetryApiError(
      "Production threat telemetry access requires CIP_CONTROL_PLANE_TOKEN",
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
    throw new ThreatTelemetryApiError("Threat telemetry API is unavailable", 503);
  }
  if (!response.ok) {
    throw new ThreatTelemetryApiError(
      await responseMessage(response),
      response.status,
    );
  }
  return (await response.json()) as T;
}

async function responseMessage(response: Response): Promise<string> {
  try {
    const payload = (await response.json()) as { detail?: string };
    return payload.detail ?? `Threat telemetry API returned ${response.status}`;
  } catch {
    return `Threat telemetry API returned ${response.status}`;
  }
}
