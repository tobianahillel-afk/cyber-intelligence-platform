import type { ResearchSourceOptions } from "./source-types";

const API_BASE_URL = process.env.CIP_API_BASE_URL ?? "http://127.0.0.1:8000";
const CONTROL_TOKEN =
  process.env.CIP_CONTROL_PLANE_TOKEN ?? "development-control-token";

const EMPTY_OPTIONS: ResearchSourceOptions = {
  purpose: "organization-research",
  data_category: "organization_metadata",
  items: [],
};

export async function loadResearchSourceOptions(): Promise<ResearchSourceOptions> {
  const query = new URLSearchParams({
    purpose: "organization-research",
    data_category: "organization_metadata",
  });
  try {
    const response = await fetch(`${API_BASE_URL}/v1/research/source-options?${query}`, {
      cache: "no-store",
      headers: { "X-CIP-Control-Token": CONTROL_TOKEN },
    });
    if (!response.ok) {
      return EMPTY_OPTIONS;
    }
    return (await response.json()) as ResearchSourceOptions;
  } catch {
    return EMPTY_OPTIONS;
  }
}
