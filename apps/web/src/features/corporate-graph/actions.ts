"use server";

import { revalidatePath } from "next/cache";

import { submitResolutionDecision } from "./api";

export async function decideResolution(formData: FormData): Promise<void> {
  const candidateId = required(formData, "candidate_id", 100);
  const decisionType = decision(formData.get("decision_type"));
  const actor = required(formData, "actor", 200);
  const reason = required(formData, "reason", 1_000);
  const blastRadiusFingerprint = required(formData, "blast_radius_fingerprint", 64);
  const organizationId = optional(formData, "organization_id", 100);
  const reversesDecisionId = optional(formData, "reverses_decision_id", 100);

  await submitResolutionDecision(candidateId, {
    decisionType,
    actor,
    reason,
    organizationId: decisionType === "merge" ? organizationId : undefined,
    reversesDecisionId: decisionType === "split" ? reversesDecisionId : undefined,
    blastRadiusFingerprint,
  });
  revalidatePath("/graph");
  revalidatePath(`/graph/resolution/${candidateId}`);
}

function required(formData: FormData, key: string, maximum: number): string {
  const value = formData.get(key);
  if (typeof value !== "string") throw new Error(`${key} is required`);
  const normalized = value.trim();
  if (!normalized || normalized.length > maximum) throw new Error(`invalid ${key}`);
  return normalized;
}

function optional(formData: FormData, key: string, maximum: number): string | undefined {
  const value = formData.get(key);
  if (typeof value !== "string" || !value.trim()) return undefined;
  const normalized = value.trim();
  if (normalized.length > maximum) throw new Error(`invalid ${key}`);
  return normalized;
}

function decision(value: FormDataEntryValue | null): "merge" | "reject" | "split" {
  if (value === "merge" || value === "reject" || value === "split") return value;
  throw new Error("invalid decision_type");
}
