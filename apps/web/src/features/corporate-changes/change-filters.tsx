import { readable } from "./change-table";
import type {
  ChangeClaimType,
  ChangeEventStatus,
  ChangeEventType,
  ChangeSourceKind,
  OrganizationLinkStatus,
} from "./types";

const statuses = [
  "under_review",
  "speculative",
  "reported",
  "confirmed",
  "disputed",
  "corrected",
  "retracted",
  "stale",
] as const satisfies readonly ChangeEventStatus[];
const eventTypes = [
  "acquisition",
  "leadership",
  "funding",
  "restructuring",
  "geographic_expansion",
  "cloud_digital_program",
  "regulatory_action",
  "breach",
  "audit",
  "certification",
  "security_commitment",
  "other",
] as const satisfies readonly ChangeEventType[];
const claimTypes = [
  "confirmation",
  "report",
  "speculation",
  "dispute",
  "correction",
  "retraction",
] as const satisfies readonly ChangeClaimType[];
const sourceKinds = [
  "official_filing",
  "regulator",
  "company",
  "media",
  "analyst",
  "other",
] as const satisfies readonly ChangeSourceKind[];
const linkStatuses = [
  "unresolved",
  "exact",
  "candidate",
  "review_required",
  "rejected",
] as const satisfies readonly OrganizationLinkStatus[];

export interface ChangeFilterValues {
  query: string;
  status?: ChangeEventStatus;
  eventType?: ChangeEventType;
  claimType?: ChangeClaimType;
  sourceKind?: ChangeSourceKind;
  organizationLinkStatus?: OrganizationLinkStatus;
  officiallyConfirmed?: boolean;
  historicalOnly?: boolean;
}

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
      <SelectFilter name="status" label="Status" value={values.status} options={statuses} />
      <SelectFilter
        name="event_type"
        label="Event type"
        value={values.eventType}
        options={eventTypes}
      />
      <SelectFilter
        name="claim_type"
        label="Claim type"
        value={values.claimType}
        options={claimTypes}
      />
      <SelectFilter
        name="source_kind"
        label="Source kind"
        value={values.sourceKind}
        options={sourceKinds}
      />
      <SelectFilter
        name="organization_link_status"
        label="Organization link"
        value={values.organizationLinkStatus}
        options={linkStatuses}
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

export function parseChangeFilters(
  parameters: Record<string, string | string[] | undefined>,
): ChangeFilterValues {
  return {
    query: first(parameters.q),
    status: parseOption(first(parameters.status), statuses),
    eventType: parseOption(first(parameters.event_type), eventTypes),
    claimType: parseOption(first(parameters.claim_type), claimTypes),
    sourceKind: parseOption(first(parameters.source_kind), sourceKinds),
    organizationLinkStatus: parseOption(
      first(parameters.organization_link_status),
      linkStatuses,
    ),
    officiallyConfirmed: parseBoolean(first(parameters.officially_confirmed)),
    historicalOnly: parseBoolean(first(parameters.historical_only)),
  };
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

function first(value: string | string[] | undefined): string {
  return (Array.isArray(value) ? value[0] : value) ?? "";
}

function parseOption<T extends string>(
  value: string,
  options: readonly T[],
): T | undefined {
  return options.find((option) => option === value);
}

function parseBoolean(value: string): boolean | undefined {
  if (value === "true") return true;
  if (value === "false") return false;
  return undefined;
}
