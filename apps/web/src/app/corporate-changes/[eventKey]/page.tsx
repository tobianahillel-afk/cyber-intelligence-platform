import { loadChangeDetail } from "@/features/corporate-changes/api";
import { ChangeDetailPanel } from "@/features/corporate-changes/change-detail";

interface CorporateChangeDetailPageProps {
  params: Promise<{ eventKey: string }>;
}

export default async function CorporateChangeDetailPage({
  params,
}: CorporateChangeDetailPageProps) {
  const { eventKey } = await params;
  const detail = await loadChangeDetail(decodeURIComponent(eventKey));

  return (
    <section className="page-stack">
      <div className="page-heading">
        <div>
          <p className="eyebrow">Corporate and regulatory change intelligence</p>
          <h1>{detail.event.title}</h1>
          <p>{detail.event.excerpt}</p>
        </div>
        <span className="live-label">Persisted evidence only</span>
      </div>
      <ChangeDetailPanel detail={detail} />
    </section>
  );
}
