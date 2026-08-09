import { saveApprovalAction } from "@/app/conditional-integrations/actions";

import type { ConditionalApproval } from "./types";

export function ApprovalForm({
  sourceId,
  approval,
}: {
  sourceId: string;
  approval: ConditionalApproval | null;
}) {
  const defaults = dossierDefaults(sourceId, approval);
  return (
    <form className="conditional-form" action={saveApprovalAction.bind(null, sourceId)}>
      <div className="conditional-form-grid">
        <SelectField label="Provider family" name="provider_kind" value={defaults.providerKind}>
          <option value="linkedin">LinkedIn</option>
          <option value="discord">Discord</option>
          <option value="brixhub">BrixHub</option>
          <option value="premium_cti">Premium CTI</option>
          <option value="commercial_data">Commercial data</option>
          <option value="other">Other</option>
        </SelectField>
        <SelectField label="Access method" name="access_method" value={defaults.accessMethod}>
          <option value="official_api">Official API</option>
          <option value="licensed_api">Licensed API</option>
          <option value="admin_installed_connector">Admin-installed connector</option>
          <option value="authorized_export">Authorized export</option>
          <option value="customer_provided_access">Customer-provided access</option>
          <option value="manual_import">Manual import</option>
        </SelectField>
        <SelectField label="Approval state" name="state" value={approval?.state ?? "draft"}>
          <option value="draft">Draft</option>
          <option value="pending_review">Pending review</option>
          <option value="approved">Approved</option>
          <option value="paused">Paused</option>
          <option value="expired">Expired</option>
          <option value="revoked">Revoked</option>
        </SelectField>
        <SelectField
          label="Terms review"
          name="terms_state"
          value={approval?.terms_state ?? "review_required"}
        >
          <option value="review_required">Review required</option>
          <option value="current">Current</option>
          <option value="changed">Changed</option>
        </SelectField>
        <TextField
          label="Authorization document reference"
          name="authorization_document_reference"
          value={approval?.authorization_document_reference}
        />
        <TextField label="Licence / contract reference" name="licence_reference" value={approval?.licence_reference} />
        <TextField label="Terms reference" name="terms_reference" value={approval?.terms_reference} />
        <TextField label="Approved account reference" name="account_reference" value={approval?.account_reference} />
        <TextField label="Approved scopes (comma separated)" name="approved_scopes" value={approval?.approved_scopes.join(", ")} />
        <TextField label="Approved fields (comma separated)" name="approved_fields" value={approval?.approved_fields.join(", ")} />
        <TextField label="Approved purposes (comma separated)" name="approved_purposes" value={approval?.approved_purposes.join(", ")} />
        <TextField
          label="Approved data categories (comma separated)"
          name="approved_data_categories"
          value={approval?.approved_data_categories.join(", ")}
        />
        <TextField label="Retention days" name="retention_days" value={numberValue(approval?.retention_days)} inputMode="numeric" />
        <TextField label="Reviewed at (RFC3339 UTC)" name="reviewed_at" value={approval?.reviewed_at} />
        <TextField label="Review due at (RFC3339 UTC)" name="review_due_at" value={approval?.review_due_at} />
        <TextField label="Expires at (RFC3339 UTC)" name="expires_at" value={approval?.expires_at} />
        <TextField label="Revoked at (RFC3339 UTC)" name="revoked_at" value={approval?.revoked_at} />
        <TextField label="Paused reason" name="paused_reason" value={approval?.paused_reason} />
      </div>
      <label className="conditional-checkbox">
        <input
          defaultChecked={approval?.automated_collection_allowed ?? false}
          name="automated_collection_allowed"
          type="checkbox"
        />
        Automation explicitly approved
      </label>
      <div className="conditional-form-grid compact">
        <TextField label="Actor" name="actor" value="provider-governance" required />
        <TextField label="Change reason" name="change_reason" value="provider dossier review" required />
      </div>
      <p className="conditional-boundary-note">
        Approved dossiers require a reviewed authorization reference, current terms, explicit
        purpose/category scopes and a retention limit. Saving this form never connects to the provider.
      </p>
      <button type="submit">Save audited dossier revision</button>
    </form>
  );
}

function TextField({
  label,
  name,
  value,
  required = false,
  inputMode,
}: {
  label: string;
  name: string;
  value?: string | null;
  required?: boolean;
  inputMode?: "numeric";
}) {
  return (
    <label>
      {label}
      <input defaultValue={value ?? ""} inputMode={inputMode} name={name} required={required} />
    </label>
  );
}

function SelectField({
  label,
  name,
  value,
  children,
}: {
  label: string;
  name: string;
  value: string;
  children: React.ReactNode;
}) {
  return (
    <label>
      {label}
      <select defaultValue={value} name={name}>{children}</select>
    </label>
  );
}

function dossierDefaults(sourceId: string, approval: ConditionalApproval | null) {
  if (approval) return { providerKind: approval.provider_kind, accessMethod: approval.access_method };
  if (sourceId.startsWith("linkedin")) return { providerKind: "linkedin", accessMethod: "official_api" };
  if (sourceId.startsWith("discord")) return { providerKind: "discord", accessMethod: "authorized_export" };
  if (sourceId === "brixhub") return { providerKind: "brixhub", accessMethod: "manual_import" };
  if (sourceId.startsWith("premium-cti")) return { providerKind: "premium_cti", accessMethod: "licensed_api" };
  if (sourceId.startsWith("commercial-data")) return { providerKind: "commercial_data", accessMethod: "licensed_api" };
  return { providerKind: "other", accessMethod: "manual_import" };
}

function numberValue(value: number | null | undefined): string {
  return value === null || value === undefined ? "" : String(value);
}
