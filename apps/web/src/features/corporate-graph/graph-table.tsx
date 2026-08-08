import Link from "next/link";

import type { GraphNodeSummary } from "./types";

interface GraphTableProps {
  nodes: GraphNodeSummary[];
}

export function GraphTable({ nodes }: GraphTableProps) {
  return (
    <div className="table-wrap">
      <table className="graph-table">
        <thead>
          <tr>
            <th>Node</th>
            <th>Resolution</th>
            <th>Evidence</th>
            <th>Temporal state</th>
          </tr>
        </thead>
        <tbody>
          {nodes.map((node) => (
            <tr key={node.node_key}>
              <td>
                <Link href={`/graph/${encodeURIComponent(node.node_key)}`}>
                  <strong>{node.display_name}</strong>
                </Link>
                <span className="graph-subline">{node.node_type}</span>
                <code>{node.node_key}</code>
              </td>
              <td>
                {node.organization_id ? (
                  <span className="graph-badge graph-badge-confirmed">Resolved</span>
                ) : (
                  <span className="graph-badge graph-badge-review">Unresolved</span>
                )}
                {node.organization_id ? <code>{node.organization_id}</code> : null}
              </td>
              <td>
                <strong>{node.source_count} source(s)</strong>
                <span className="graph-subline">
                  confidence {Math.round(node.confidence * 100)}%
                </span>
              </td>
              <td>
                <span className={`graph-badge ${stateClass(node)}`}>
                  {node.suppressed ? "suppressed" : node.current ? "current" : "historical"}
                </span>
                <span className="graph-subline">
                  seen {formatDate(node.last_observed_at)}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function stateClass(node: GraphNodeSummary): string {
  if (node.suppressed) return "graph-badge-rejected";
  if (node.current) return "graph-badge-current";
  return "graph-badge-history";
}

function formatDate(value: string): string {
  return new Intl.DateTimeFormat("en-GB", {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone: "UTC",
  }).format(new Date(value));
}
