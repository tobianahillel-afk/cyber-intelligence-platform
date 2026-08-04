"use server";

import { revalidatePath } from "next/cache";

import {
  recordHumanCheckpoint,
  registerSecretReference,
  revokeProvider,
  startProvider,
  verifyProvider,
} from "@/features/sources/api";
import type { ProviderOnboardingState } from "@/features/sources/types";

const checkpointStates = new Set<ProviderOnboardingState>([
  "awaiting_user_action",
  "awaiting_email_verification",
  "awaiting_mfa",
  "awaiting_provider_approval",
]);

export async function startProviderAction(
  sourceId: string,
  formData: FormData,
): Promise<void> {
  await startProvider(sourceId, { actor: actor(formData) });
  revalidatePath("/sources");
}

export async function verifyProviderAction(
  sourceId: string,
  formData: FormData,
): Promise<void> {
  await verifyProvider(sourceId, { actor: actor(formData) });
  revalidatePath("/sources");
}

export async function revokeProviderAction(
  sourceId: string,
  formData: FormData,
): Promise<void> {
  await revokeProvider(sourceId, { actor: actor(formData) });
  revalidatePath("/sources");
}

export async function humanCheckpointAction(
  sourceId: string,
  formData: FormData,
): Promise<void> {
  const state = text(formData, "state") as ProviderOnboardingState;
  if (!checkpointStates.has(state)) {
    throw new Error("Unsupported provider checkpoint state");
  }
  await recordHumanCheckpoint(sourceId, {
    actor: actor(formData),
    state,
    note: optionalText(formData, "note"),
  });
  revalidatePath("/sources");
}

export async function registerSecretReferenceAction(
  sourceId: string,
  formData: FormData,
): Promise<void> {
  await registerSecretReference(sourceId, {
    actor: actor(formData),
    name: text(formData, "name"),
    reference: text(formData, "reference"),
  });
  revalidatePath("/sources");
}

function actor(formData: FormData): string {
  return text(formData, "actor");
}

function text(formData: FormData, name: string): string {
  const value = formData.get(name);
  if (typeof value !== "string" || !value.trim()) {
    throw new Error(`${name} is required`);
  }
  return value.trim();
}

function optionalText(formData: FormData, name: string): string | undefined {
  const value = formData.get(name);
  return typeof value === "string" && value.trim() ? value.trim() : undefined;
}
