import Link from "next/link";

import type { SourcePortfolioEntry } from "@/features/sources/types";

import type { ConditionalProviderSummary } from "./types";

export function ConditionalProviderCatalog({
  candidates,
  approvals,
}: {
  candidates: readonly SourcePortfolioEntry[];
  approvals: ReadonlyMap<string, ConditionalProviderSummary>;
}) {
  return (
    <div className="conditional-catalog-grid">
      {candidates.map((candidate) => {
        const provider = approvals.get(candidate.source_id);
        return (
          <article className="conditional-provider-card" key={candidate.source_id}>
            <div className="conditional-card-heading">
              <div>
                <p className="eyebrow">{candidate.category.replaceAll("_", " ")}</p>
                <h3>{candidate.display_name}</h3>
                <code>{candidate.source_id}</code>
              </div>
              <span className={`conditional-state state-${provider?.approval.state ?? "missing"}`}>
                {provider?.approval.state ?? "no dossier"}
              </span>
            </div>

            <dl className="conditional-compact-grid">
              <Metric label="Portfolio" value={candidate.status} />
              <Metric label="Runtime adapter" value={candidate.adapter ? "present" : "absent"} />
              <Metric
                label="Pause"
                value={provider?.control?.paused ? "active" : "clear"}
              />
              <Metric
                label="Kill switch"
                value={provider?.control?.kill_switch_active ? "active" : "clear"}
              />
            </dl>

            <p className="conditional-boundary-note">
              Candidate visibility is not execution authorization. A positive provider dossier,
              shared governance gates and a real registered adapter are all required.
            </p>
            <Link
              className="conditional-link"
              href={`/conditional-integrations/${encodeURIComponent(candidate.source_id)}`}
            >
              Review provider
            </Link>
          </article>
        );
      })}
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt>{label}</dt>
      <dd>{value.replaceAll("_", " ")}</dd>
    </div>
  );
}
