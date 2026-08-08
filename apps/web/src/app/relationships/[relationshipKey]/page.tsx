import { loadRelationshipDetail } from "@/features/relationships/api";
import { RelationshipDetailPanel } from "@/features/relationships/relationship-detail";

interface RelationshipDetailPageProps {
  params: Promise<{ relationshipKey: string }>;
}

export default async function RelationshipDetailPage({
  params,
}: RelationshipDetailPageProps) {
  const { relationshipKey } = await params;
  const detail = await loadRelationshipDetail(decodeURIComponent(relationshipKey));
  const source = detail.relationship.source_name ?? "Unresolved source organization";
  const target = detail.relationship.target_name ?? "Unresolved target organization";

  return (
    <section className="page-stack">
      <div className="page-heading">
        <div>
          <p className="eyebrow">Temporal organization relationship intelligence</p>
          <h1>{source} → {target}</h1>
          <p>
            Directed relationship evidence with explicit chronology, provenance,
            evidence class, identity resolution and review state.
          </p>
        </div>
        <span className="live-label">Persisted evidence only</span>
      </div>
      <RelationshipDetailPanel detail={detail} />
    </section>
  );
}
