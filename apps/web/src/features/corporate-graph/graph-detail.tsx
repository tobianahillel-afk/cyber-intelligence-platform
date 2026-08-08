import type { GraphEdgeSummary, GraphNodeDetail } from "./types";

interface GraphDetailProps {
  detail: GraphNodeDetail;
}

export function GraphDetail({ detail }: GraphDetailProps) {
  return (
    <div className="graph-detail-stack">
      <div className="graph-warning">{detail.evidence_disclaimer}</div>

      <section className="panel graph-node-overview">
        <div>
          <span className={`graph-badge ${detail.node.current ? "graph-badge-current" : "graph-badge-history"}`}>
            {detail.node.current ? "current" : "historical"}
          </span>
          {detail.node.suppressed ? (
            <span className="graph-badge graph-badge-rejected">suppressed</span>
          ) : null}
          <h2>{detail.node.display_name}</h2>
          <code>{detail.node.node_key}</code>
        </div>
        <dl>
          <div><dt>Type</dt><dd>{detail.node.node_type}</dd></div>
          <div><dt>Sources</dt><dd>{detail.node.source_count}</dd></div>
          <div><dt>Confidence</dt><dd>{Math.round(detail.node.confidence * 100)}%</dd></div>
          <div>
            <dt>Organization</dt>
            <dd>{detail.node.organization_id ?? "Unresolved"}</dd>
          </div>
        </dl>
      </section>

      <section className="panel">
        <div className="panel-heading">
          <div>
            <h2>Outgoing edges</h2>
            <p>Evidence class and review state are shown before relationship meaning.</p>
          </div>
        </div>
        <EdgeList edges={detail.outgoing_edges} />
      </section>

      <section className="panel">
        <div className="panel-heading"><h2>Incoming edges</h2></div>
        <EdgeList edges={detail.incoming_edges} />
      </section>

      <section className="panel">
        <div className="panel-heading">
          <div>
            <h2>Immutable source history</h2>
            <p>{detail.snapshots.length} snapshot(s) visible for this time view.</p>
          </div>
        </div>
        <div className="graph-history-list">
          {detail.snapshots.map((snapshot) => (
            <article key={snapshot.id}>
              <div>
                <span className={`graph-badge ${snapshot.active ? "graph-badge-current" : "graph-badge-history"}`}>
                  {snapshot.active ? "active source revision" : "inactive revision"}
                </span>
                {snapshot.suppressed ? (
                  <span className="graph-badge graph-badge-rejected">suppressed</span>
                ) : null}
                <strong>{snapshot.source_module}</strong>
              </div>
              <code>{snapshot.source_record_key}</code>
              <p>
                observed {formatDate(snapshot.observed_at)} · confidence {Math.round(snapshot.confidence * 100)}%
              </p>
              {snapshot.source_url ? (
                <a href={snapshot.source_url} rel="noreferrer" target="_blank">Source evidence</a>
              ) : null}
            </article>
          ))}
        </div>
      </section>
    </div>
  );
}

function EdgeList({ edges }: { edges: GraphEdgeSummary[] }) {
  if (!edges.length) return <div className="empty-state"><p>No edge in this view.</p></div>;
  return (
    <div className="graph-edge-list">
      {edges.map((edge) => (
        <article key={edge.edge_key}>
          <div className="graph-edge-state">
            <span className={`graph-badge ${reviewClass(edge.review_state)}`}>
              {edge.review_state.replaceAll("_", " ")}
            </span>
            <span className={`graph-badge ${edge.current ? "graph-badge-current" : "graph-badge-history"}`}>
              {edge.current ? "current" : "historical"}
            </span>
          </div>
          <strong>{edge.source_evidence_class.replaceAll("_", " ")}</strong>
          <p>{edge.edge_type.replaceAll("_", " ")}</p>
          <code>{edge.source_node_key} → {edge.target_node_key}</code>
          <span className="graph-subline">
            {edge.source_module} · {Math.round(edge.confidence * 100)}% confidence
          </span>
        </article>
      ))}
    </div>
  );
}

function reviewClass(state: string): string {
  if (state === "confirmed" || state === "auto_confirmed") return "graph-badge-confirmed";
  if (state === "rejected") return "graph-badge-rejected";
  return "graph-badge-review";
}

function formatDate(value: string): string {
  return new Intl.DateTimeFormat("en-GB", {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone: "UTC",
  }).format(new Date(value));
}
