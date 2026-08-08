import {
  loadGraphNodes,
  loadResolutionCandidates,
} from "@/features/corporate-graph/api";
import {
  parseGraphFilters,
  parseResolutionFilters,
} from "@/features/corporate-graph/filter-state";
import { GraphFilters } from "@/features/corporate-graph/graph-filters";
import { GraphTable } from "@/features/corporate-graph/graph-table";
import { ResolutionQueue } from "@/features/corporate-graph/resolution-queue";

interface GraphPageProps {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}

export default async function GraphPage({ searchParams }: GraphPageProps) {
  const raw = await searchParams;
  const filters = parseGraphFilters(raw);
  const resolutionFilters = parseResolutionFilters(raw);
  if (resolutionFilters.requiresReview === undefined) {
    resolutionFilters.requiresReview = true;
  }
  const [nodes, candidates] = await Promise.all([
    loadGraphNodes(filters),
    loadResolutionCandidates(resolutionFilters),
  ]);
  const summary = [
    { label: "Graph nodes", value: nodes.total },
    {
      label: "Current on page",
      value: nodes.items.filter((item) => item.current && !item.suppressed).length,
    },
    {
      label: "Unresolved on page",
      value: nodes.items.filter((item) => !item.organization_id).length,
    },
    { label: "Resolution reviews", value: candidates.total },
  ] as const;

  return (
    <section className="page-stack">
      <div className="page-heading">
        <div>
          <p className="eyebrow">Temporal corporate knowledge graph</p>
          <h1>Identity, evidence and relationships over time</h1>
          <p>
            Explore persisted company context without upgrading weak evidence or hiding
            historical identity decisions.
          </p>
        </div>
        <span className="live-label">PostgreSQL source of truth</span>
      </div>

      <div className="graph-warning">
        Graph membership is not proof. Claimed, inferred, historical, disputed or retracted
        edges keep their original evidence class and review state.
      </div>

      <div className="summary-grid" aria-label="Corporate graph summary">
        {summary.map((item) => (
          <article className="summary-card" key={item.label}>
            <span>{item.label}</span>
            <strong>{item.value}</strong>
          </article>
        ))}
      </div>

      <section className="panel" aria-labelledby="graph-node-title">
        <div className="panel-heading graph-heading">
          <div>
            <h2 id="graph-node-title">Persisted graph nodes</h2>
            <p>Current and historical nodes ordered by latest observed evidence.</p>
          </div>
          <GraphFilters values={filters} />
        </div>
        {nodes.items.length ? (
          <GraphTable nodes={nodes.items} />
        ) : (
          <div className="empty-state"><h3>No matching graph node</h3></div>
        )}
      </section>

      <section className="panel" aria-labelledby="resolution-title">
        <div className="panel-heading">
          <div>
            <h2 id="resolution-title">Resolution review queue</h2>
            <p>Probabilistic and conflicting matches remain human-reviewed.</p>
          </div>
        </div>
        <ResolutionQueue candidates={candidates.items} />
      </section>
    </section>
  );
}
