"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";

import {
  OpportunityApiError,
  submitComponentOverride,
  submitOpportunityReview,
} from "./api";
import type { OpportunityReviewAction } from "./types";

const reviewActions = new Set<OpportunityReviewAction>([
  "qualify",
  "reject",
  "snooze",
  "request_enrichment",
  "reopen",
]);

export async function reviewOpportunityAction(
  opportunityId: string,
  formData: FormData,
): Promise<void> {
  const action = formValue(formData, "action") as OpportunityReviewAction;
  if (!reviewActions.has(action)) {
    redirectWithError(opportunityId, "Unsupported review action");
  }
  try {
    await submitOpportunityReview(opportunityId, {
      action,
      actor: requiredFormValue(formData, "actor"),
      note: formValue(formData, "note"),
      snoozedUntil: localDateTimeToIso(formValue(formData, "snoozed_until")),
    });
  } catch (error) {
    redirectWithError(opportunityId, messageFromError(error));
  }
  revalidateOpportunity(opportunityId);
  redirect(`/opportunities/${opportunityId}?updated=${encodeURIComponent(action)}`);
}

export async function overrideScoreComponentAction(
  opportunityId: string,
  componentId: string,
  formData: FormData,
): Promise<void> {
  try {
    await submitComponentOverride(opportunityId, componentId, {
      actor: requiredFormValue(formData, "actor"),
      value: optionalNumber(formData, "value"),
      weight: optionalNumber(formData, "weight"),
      reason: formValue(formData, "reason"),
    });
  } catch (error) {
    redirectWithError(opportunityId, messageFromError(error));
  }
  revalidateOpportunity(opportunityId);
  redirect(`/opportunities/${opportunityId}?updated=score`);
}

function revalidateOpportunity(opportunityId: string): void {
  revalidatePath("/");
  revalidatePath(`/opportunities/${opportunityId}`);
}

function formValue(formData: FormData, key: string): string | undefined {
  const value = formData.get(key);
  return typeof value === "string" && value.trim() ? value.trim() : undefined;
}

function requiredFormValue(formData: FormData, key: string): string {
  const value = formValue(formData, key);
  if (!value) {
    throw new Error(`${key} is required`);
  }
  return value;
}

function optionalNumber(formData: FormData, key: string): number | undefined {
  const value = formValue(formData, key);
  if (value === undefined) {
    return undefined;
  }
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) {
    throw new Error(`${key} must be a number`);
  }
  return parsed;
}

function localDateTimeToIso(value: string | undefined): string | undefined {
  if (!value) {
    return undefined;
  }
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    throw new Error("snoozed_until is invalid");
  }
  return parsed.toISOString();
}

function messageFromError(error: unknown): string {
  if (error instanceof OpportunityApiError || error instanceof Error) {
    return error.message;
  }
  return "Unexpected opportunity update failure";
}

function redirectWithError(opportunityId: string, message: string): never {
  redirect(`/opportunities/${opportunityId}?error=${encodeURIComponent(message)}`);
}
