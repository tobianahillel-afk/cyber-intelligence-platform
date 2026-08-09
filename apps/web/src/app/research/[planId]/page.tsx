import { notFound } from "next/navigation";

import { loadResearchPlan } from "@/features/research-plans/api";
import { ResearchPlanDetail } from "@/features/research-plans/research-plan-detail";

interface ResearchPlanPageProps {
  params: Promise<{ planId: string }>;
}

export default async function ResearchPlanPage({ params }: ResearchPlanPageProps) {
  const { planId } = await params;
  const detail = await loadResearchPlan(planId);
  if (detail === null) {
    notFound();
  }
  return <ResearchPlanDetail detail={detail} />;
}
