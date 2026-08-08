import type { GraphNodeQuery } from "./api";

const NODE_TYPES = [
  "organization",
  "establishment",
  "group",
  "brand",
  "domain",
  "asset",
  "technology",
  "product",
  "incident",
  "vulnerability",
  "provider",
  "material_change",
] as const;

interface GraphFiltersProps {
  values: GraphNodeQuery;
}

export function GraphFilters({ values }: GraphFiltersProps) {
  return (
    <form className="graph-filters" method="get">
      <label>
        Search
        <input
          defaultValue={values.query}
          maxLength={200}
          name="q"
          placeholder="name, domain, key…"
        />
      </label>
      <label>
        Type
        <select defaultValue={values.nodeType ?? ""} name="node_type">
          <option value="">All types</option>
          {NODE_TYPES.map((value) => (
            <option key={value} value={value}>
              {value.replaceAll("_", " ")}
            </option>
          ))}
        </select>
      </label>
      <label>
        Current state
        <select defaultValue={booleanValue(values.current)} name="current">
          <option value="">Any</option>
          <option value="true">Current</option>
          <option value="false">Historical / inactive</option>
        </select>
      </label>
      <label>
        Suppression
        <select defaultValue={booleanValue(values.suppressed)} name="suppressed">
          <option value="">Any</option>
          <option value="false">Visible</option>
          <option value="true">Suppressed</option>
        </select>
      </label>
      <button type="submit">Apply</button>
    </form>
  );
}

function booleanValue(value: boolean | undefined): string {
  if (value === true) return "true";
  if (value === false) return "false";
  return "";
}
