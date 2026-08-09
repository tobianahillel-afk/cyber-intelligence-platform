import Link from "next/link";

import { loadProfessionalPerson } from "@/features/professional-context/api";
import { ProfessionalDetail } from "@/features/professional-context/detail";

interface ProfessionalPersonPageProps {
  params: Promise<{ personKey: string }>;
}

export default async function ProfessionalPersonPage({ params }: ProfessionalPersonPageProps) {
  const { personKey } = await params;
  const detail = await loadProfessionalPerson(decodeURIComponent(personKey));

  return (
    <section className="page-stack">
      <div className="page-heading">
        <div>
          <p className="eyebrow">Professional evidence review</p>
          <h1>{detail.person.display_name ?? "[deleted professional reference]"}</h1>
          <p>
            Inspect role chronology, explicit reporting claims, business contact evidence,
            community context and processing state.
          </p>
        </div>
        <Link className="professional-back-link" href="/professional-context">
          Back to professional context
        </Link>
      </div>
      {detail.person.organization_id ? (
        <Link
          className="professional-map-link"
          href={`/professional-context/organizations/${detail.person.organization_id}`}
        >
          Open organization map
        </Link>
      ) : null}
      <ProfessionalDetail detail={detail} />
    </section>
  );
}
