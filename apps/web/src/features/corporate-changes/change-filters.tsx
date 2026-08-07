import {
  changeClaimTypes,
  changeEventTypes,
  changeSourceKinds,
  changeStatuses,
  organizationLinkStatuses,
  type ChangeFilterValues,
} from "./change-filter-state";
import { readable } from "./change-table";

interface ChangeFiltersFormProps {
  values: ChangeFilterValues;
}

export function ChangeFiltersForm({ values }: ChangeFiltersFormProps) {
  return (
    <form className="filter-form change-filters">
      <label>
        Search
        <input name="q" defaultValue={values.query} placeholder="Title, excerpt or key" />
      </label>
      <SelectFilter
        name="status"
        label="Status"
        value={values.status}
        options={changeStatuses}
      />
      <SelectFilter
        name="event_type"
        label="Event type"
        value={values.eventType}
        options={changeEventTypes}
      />
      <SelectFilter
        name="claim_type"
        label="Claim type"
        value={values.claimType}
        options={changeClaimTypes}
      />
      <SelectFilter
        name="source_kind"
        label="Source kind"
        value={values.sourceKind}
        options={changeSourceKinds}
      />
      <SelectFilter
        name="organization_link_status"
        label="Organization link"
        value={values.organizationLinkStatus}
        options={organizationLinkStatuses}
      />
      <BooleanFilter
        name="officially_confirmed"
        label="Official confirmation"
        value={values.officiallyConfirmed}
        trueLabel="Confirmed"
        falseLabel="Not confirmed"
      />
      <BooleanFilter
        name="historical_only"
        label="Historical backfill"
        value={values.historicalOnly}
        trueLabel="Historical only"
        falseLabel="Current-capable"
      />
      <button type="submit">Apply</button>
    </form>
  );
}

interface SelectFilterProps<T extends string> {
  name: string;
  label: string;
  value?: T;
  options: readonly T[];
}

function SelectFilter<T extends string>({
  name,
  label,
  value,
  options,
}: SelectFilterProps<T>) {
  return (
    <label>
      {label}
      <select name={name} defaultValue={value ?? ""}>
        <option value="">Any</option>
        {options.map((option) => (
          <option key={option} value={option}>
            {readable(option)}
          </option>
        ))}
      </select>
    </label>
  );
}

interface BooleanFilterProps {
  name: string;
  label: string;
  value?: boolean;
  trueLabel: string;
  falseLabel: string;
}

function BooleanFilter({
  name,
  label,
  value,
  trueLabel,
  falseLabel,
}: BooleanFilterProps) {
  return (
    <label>
      {label}
      <select name={name} defaultValue={value === undefined ? "" : String(value)}>
        <option value="">Any</option>
        <option value="true">{trueLabel}</option>
        <option value="false">{falseLabel}</option>
      </select>
    </label>
  );
}
