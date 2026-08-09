import type { GraphNodeQuery, ResolutionQuery } from "./api";
import type { GraphNodeType } from "./types";

const NODE_TYPES = new Set<GraphNodeType>([
  "organization",
  "establishment",
  "group",
  "brand",
  "alias",
  "identifier",
  "domain",
  "asset",
  "technology",
  "product",
  "incident",
  "vulnerability",
  "provider",
  "material_change",
]);

export function parseGraphFilters(
  raw: Record<string, string | string[] | undefined>,
): GraphNodeQuery {
  const nodeType = first(raw.node_type);
  return {
    nodeType: nodeType && NODE_TYPES.has(nodeType as GraphNodeType)
      ? (nodeType as GraphNodeType)
      : undefined,
    organizationId: first(raw.organization_id),
    current: parseBoolean(first(raw.current)),
    suppressed: parseBoolean(first(raw.suppressed)),
    query: first(raw.q),
    limit: 100,
    offset: 0,
  };
}

export function parseResolutionFilters(
  raw: Record<string, string | string[] | undefined>,
): ResolutionQuery {
  return {
    state: first(raw.resolution_state),
    requiresReview: parseBoolean(first(raw.requires_review)),
    limit: 100,
    offset: 0,
  };
}

function first(value: string | string[] | undefined): string | undefined {
  return Array.isArray(value) ? value[0] : value;
}

function parseBoolean(value: string | undefined): boolean | undefined {
  if (value === "true") return true;
  if (value === "false") return false;
  return undefined;
}
