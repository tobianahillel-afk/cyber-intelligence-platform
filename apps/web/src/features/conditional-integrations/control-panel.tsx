import {
  eligibilityPreviewAction,
  providerControlAction,
} from "@/app/conditional-integrations/actions";

import type { ConditionalApproval, ConditionalRuntimeControl } from "./types";

export function ConditionalControlPanel({
  sourceId,
  approval,
  control,
}: {
  sourceId: string;
  approval: ConditionalApproval;
  control: ConditionalRuntimeControl | null;
}) {
  return (
    <div className="conditional-control-stack">
      <section className="conditional-subpanel">
        <h3>Runtime controls</h3>
        <p>
          Pause and kill switch are local control-plane states. They immediately block new
          eligibility decisions but never delete historical provenance.
        </p>
        <div className="conditional-control-actions">
          <ControlForm sourceId={sourceId} action="pause" label="Pause" />
          <ControlForm sourceId={sourceId} action="resume" label="Resume" />
          <ControlForm
            sourceId={sourceId}
            action="activate_kill_switch"
            label="Activate kill switch"
            destructive
          />
          <ControlForm sourceId={sourceId} action="clear_kill_switch" label="Clear kill switch" />
        </div>
        <dl className="conditional-compact-grid">
          <Metric label="Paused" value={control?.paused ? "yes" : "no"} />
          <Metric label="Kill switch" value={control?.kill_switch_active ? "active" : "clear"} />
        </dl>
      </section>

      <section className="conditional-subpanel">
        <h3>Persisted-state eligibility preview</h3>
        <p>
          This submits only the intended access. Onboarding, source policy, portfolio state,
          capability, quota, cost, pause and kill switch are resolved from the database.
        </p>
        <form
          className="conditional-form"
          action={eligibilityPreviewAction.bind(null, sourceId)}
        >
          <div className="conditional-form-grid">
            <label>
              Access method
              <select defaultValue={approval.access_method} name="access_method">
                <option value="official_api">Official API</option>
                <option value="licensed_api">Licensed API</option>
                <option value="admin_installed_connector">Admin-installed connector</option>
                <option value="authorized_export">Authorized export</option>
                <option value="customer_provided_access">Customer-provided access</option>
                <option value="manual_import">Manual import</option>
              </select>
            </label>
            <Field
              label="Purpose"
              name="purpose"
              value={approval.approved_purposes[0] ?? "professional-context"}
            />
            <Field
              label="Data category"
              name="data_category"
              value={approval.approved_data_categories[0] ?? "organization_metadata"}
            />
            <Field label="Target URL" name="target_url" value="https://example.invalid/" />
            <Field
              label="Requested scopes"
              name="requested_scopes"
              value={approval.approved_scopes.join(", ")}
            />
            <Field
              label="Requested fields"
              name="requested_fields"
              value={approval.approved_fields.join(", ")}
            />
            <Field
              label="Retention days"
              name="retention_days"
              value={String(approval.retention_days ?? 1)}
            />
            <Field
              label="Account reference"
              name="account_reference"
              value={approval.account_reference ?? ""}
            />
          </div>
          <div className="conditional-checkbox-row">
            <label className="conditional-checkbox">
              <input defaultChecked name="automated" type="checkbox" /> Automated request
            </label>
            <label className="conditional-checkbox">
              <input name="store_raw_content" type="checkbox" /> Store raw content
            </label>
          </div>
          <p className="conditional-boundary-note">
            Preview writes an audit decision only. It performs no provider login, HTTP request,
            browser action, collection, outreach or opportunity creation.
          </p>
          <button type="submit">Evaluate and audit</button>
        </form>
      </section>
    </div>
  );
}

function ControlForm({
  sourceId,
  action,
  label,
  destructive = false,
}: {
  sourceId: string;
  action: string;
  label: string;
  destructive?: boolean;
}) {
  return (
    <form action={providerControlAction.bind(null, sourceId, action)}>
      <input name="actor" type="hidden" value="provider-operator" />
      <input name="reason" type="hidden" value={`operator action: ${label}`} />
      <button className={destructive ? "destructive" : undefined} type="submit">
        {label}
      </button>
    </form>
  );
}

function Field({ label, name, value }: { label: string; name: string; value: string }) {
  return (
    <label>
      {label}
      <input defaultValue={value} name={name} />
    </label>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt>{label}</dt>
      <dd>{value}</dd>
    </div>
  );
}
