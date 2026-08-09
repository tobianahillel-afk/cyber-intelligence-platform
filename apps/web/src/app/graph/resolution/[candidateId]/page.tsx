import Link from "next/link";

import { loadResolutionCandidate } from "@/features/corporate-graph/api";
import { ResolutionDetail } from "@/features/corporate-graph/resolution-detail";

interface ResolutionPageProps {
  params: Promise<{ candidateId: string }>;
}

export default async function ResolutionPage({ params }: ResolutionPageProps) {
  const { candidateId } = await params;
  const detail = await loadResolutionCandidate(candidateId);

  return (
    <section className="page-stack">
      <div className="page-heading">
        <div>
          <p className="eyebrow">Entity-resolution review</p>
          <h1>Review identity binding</h1>
          <p>
            Inspect evidence conflicts and downstream impact before applying a reversible
            human decision.
          </p>
        </div>
        <Link className="graph-review-link" href="/graph">Back to graph</Link>
      </div>
      <ResolutionDetail detail={detail} />
    </section>
  );
}
