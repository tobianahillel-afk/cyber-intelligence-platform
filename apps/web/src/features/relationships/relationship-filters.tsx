import {
  evidenceClasses,
  linkStatuses,
  relationshipRoles,
  relationshipStatuses,
  sourceKinds,
} from "./filter-state";
import type { RelationshipQuery } from "./api";

interface RelationshipFiltersProps {
  values: RelationshipQuery;
}

export function RelationshipFilters({ values }: RelationshipFiltersProps) {
  return (
    <form className="relationship-filters">
      <label>
        Search
        <input name="q" defaultValue={values.query ?? ""} placeholder="Organization or key" />
      </label>
      <SelectField name="status" label="Status" value={values.status} options={relationshipStatuses} />
      <SelectField name="role" label="Role" value={values.role} options={relationshipRoles} />
      <SelectField
        name="evidence_class"
        label="Evidence"
        value={values.evidenceClass}
        options={evidenceClasses}
      />
      <SelectField
        name="source_kind"
        label="Source"
        value={values.sourceKind}
        options={sourceKinds}
      />
      <SelectField
        name="source_link_status"
        label="Source identity"
        value={values.sourceLinkStatus}
        options={linkStatuses}
      />
      <SelectField
        name="target_link_status"
        label="Target identity"
        value={values.targetLinkStatus}
        options={linkStatuses}
      />
      <BooleanField
        name="contract_backed_current"
        label="Contract-backed current"
        value={values.contractBackedCurrent}
      />
      <BooleanField
        name="historical_only"
        label="Historical only"
        value={values.historicalOnly}
      />
      <button type="submit">Apply</button>
    </form>
  );
}

interface SelectFieldProps<T extends string> {
  name: string;
  label: string;
  value?: T;
  options: readonly T[];
}

function SelectField<T extends string>({
  name,
  label,
  value,
  options,
}: SelectFieldProps<T>) {
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

interface BooleanFieldProps {
  name: string;
  label: string;
  value?: boolean;
}

function BooleanField({ name, label, value }: BooleanFieldProps) {
  return (
    <label>
      {label}
      <select name={name} defaultValue={value === undefined ? "" : String(value)}>
        <option value="">Any</option>
        <option value="true">Yes</option>
        <option value="false">No</option>
      </select>
    </label>
  );
}

export function readable(value: string): string {
  return value
    .replaceAll("_", " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}
