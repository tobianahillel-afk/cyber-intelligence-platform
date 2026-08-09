"use server";

import { revalidatePath } from "next/cache";

import {
  changeConditionalControl,
  evaluateConditionalEligibility,
  saveConditionalApproval,
} from "@/features/conditional-integrations/api";

export async function saveApprovalAction(
  sourceId: string,
  formData: FormData,
): Promise<void> {
  await saveConditionalApproval(sourceId, {
    provider_kind: text(formData, "provider_kind"),
    access_method: text(formData, "access_method"),
    state: text(formData, "state"),
    authorization_document_reference: optionalText(formData, "authorization_document_reference"),
    licence_reference: optionalText(formData, "licence_reference"),
    terms_reference: optionalText(formData, "terms_reference"),
    terms_state: text(formData, "terms_state"),
    approved_scopes: csv(formData, "approved_scopes"),
    approved_fields: csv(formData, "approved_fields"),
    approved_purposes: csv(formData, "approved_purposes"),
    approved_data_categories: csv(formData, "approved_data_categories"),
    retention_days: optionalInteger(formData, "retention_days"),
    automated_collection_allowed: checkbox(formData, "automated_collection_allowed"),
    account_reference: optionalText(formData, "account_reference"),
    reviewed_at: optionalText(formData, "reviewed_at"),
    review_due_at: optionalText(formData, "review_due_at"),
    expires_at: optionalText(formData, "expires_at"),
    revoked_at: optionalText(formData, "revoked_at"),
    paused_reason: optionalText(formData, "paused_reason"),
    actor: text(formData, "actor"),
    change_reason: text(formData, "change_reason"),
  });
  revalidate(sourceId);
}

export async function providerControlAction(
  sourceId: string,
  action: string,
  formData: FormData,
): Promise<void> {
  await changeConditionalControl(sourceId, {
    action,
    actor: text(formData, "actor"),
    reason: text(formData, "reason"),
  });
  revalidate(sourceId);
}

export async function eligibilityPreviewAction(
  sourceId: string,
  formData: FormData,
): Promise<void> {
  await evaluateConditionalEligibility(sourceId, {
    access_method: text(formData, "access_method"),
    purpose: text(formData, "purpose"),
    data_category: text(formData, "data_category"),
    target_url: text(formData, "target_url"),
    requested_scopes: csv(formData, "requested_scopes"),
    requested_fields: csv(formData, "requested_fields"),
    retention_days: integer(formData, "retention_days"),
    automated: checkbox(formData, "automated"),
    store_raw_content: checkbox(formData, "store_raw_content"),
    account_reference: optionalText(formData, "account_reference"),
  });
  revalidate(sourceId);
}

function revalidate(sourceId: string): void {
  revalidatePath("/conditional-integrations");
  revalidatePath(`/conditional-integrations/${encodeURIComponent(sourceId)}`);
}

function text(formData: FormData, name: string): string {
  const value = formData.get(name);
  if (typeof value !== "string" || !value.trim()) {
    throw new Error(`${name} is required`);
  }
  return value.trim();
}

function optionalText(formData: FormData, name: string): string | null {
  const value = formData.get(name);
  return typeof value === "string" && value.trim() ? value.trim() : null;
}

function csv(formData: FormData, name: string): string[] {
  const value = optionalText(formData, name);
  return value
    ? [...new Set(value.split(",").map((item) => item.trim()).filter(Boolean))]
    : [];
}

function integer(formData: FormData, name: string): number {
  const parsed = Number.parseInt(text(formData, name), 10);
  if (!Number.isInteger(parsed) || parsed < 1) {
    throw new Error(`${name} must be a positive integer`);
  }
  return parsed;
}

function optionalInteger(formData: FormData, name: string): number | null {
  const value = optionalText(formData, name);
  if (value === null) return null;
  const parsed = Number.parseInt(value, 10);
  if (!Number.isInteger(parsed) || parsed < 1) {
    throw new Error(`${name} must be a positive integer`);
  }
  return parsed;
}

function checkbox(formData: FormData, name: string): boolean {
  return formData.get(name) === "on";
}
