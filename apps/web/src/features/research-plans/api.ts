import type { ResearchPlanDetail, ResearchPlanPage } from "./types";

const API_BASE_URL = process.env.CIP_API_BASE_URL ?? "http://127.0.0.1:8000";
const CONTROL_TOKEN =
  process.env.CIP_CONTROL_PLANE_TOKEN ?? "development-control-token";

const EMPTY_PAGE: ResearchPlanPage = { items: [], total: 0 };

export async function loadResearchPlans(): Promise<ResearchPlanPage> {
  const response = await request("/v1/research/plans");
  if (response === null) {
    return EMPTY_PAGE;
  }
  return (await response.json()) as ResearchPlanPage;
}

export async function loadResearchPlan(
  planId: string,
): Promise<ResearchPlanDetail | null> {
  const response = await request(`/v1/research/plans/${encodeURIComponent(planId)}`);
  if (response === null) {
    return null;
  }
  return (await response.json()) as ResearchPlanDetail;
}

async function request(path: string): Promise<Response | null> {
  try {
    const response = await fetch(`${API_BASE_URL}${path}`, {
      cache: "no-store",
      headers: { "X-CIP-Control-Token": CONTROL_TOKEN },
    });
    return response.ok ? response : null;
  } catch {
    return null;
  }
}
