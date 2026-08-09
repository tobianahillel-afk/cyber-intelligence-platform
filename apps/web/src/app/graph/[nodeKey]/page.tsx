import Link from "next/link";

import { loadGraphNodeDetail } from "@/features/corporate-graph/api";
import { GraphDetail } from "@/features/corporate-graph/graph-detail";

interface GraphNodePageProps {
  params: Promise<{ nodeKey: string }>;
  searchParams: Promise<{ as_of?: string | string[] }>;
}

export default async function GraphNodePage({ params, searchParams }: GraphNodePageProps) {
  const { nodeKey } = await params;
  const rawSearch = await searchParams;
  const asOf = Array.isArray(rawSearch.as_of) ? rawSearch.as_of[0] : rawSearch.as_of;
  const detail = await loadGraphNodeDetail(decodeURIComponent(nodeKey), asOf);

  return (
    <section className="page-stack">
      <div className="page-heading">
        <div>
          <p className="eyebrow">Corporate graph node</p>
          <h1>{detail.node.display_name}</h1>
          <p>
            Inspect source history and temporal edges without changing their original
            evidence strength.
          </p>
        </div>
        <Link className="graph-review-link" href="/graph">Back to graph</Link>
      </div>
      {detail.as_of ? (
        <div className="graph-as-of">Historical view as of {detail.as_of}</div>
      ) : null}
      <GraphDetail detail={detail} />
    </section>
  );
}
