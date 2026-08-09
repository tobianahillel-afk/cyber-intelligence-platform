import Link from "next/link";

import { loadOrganizationProfessionalMap } from "@/features/professional-context/api";
import { OrganizationMap } from "@/features/professional-context/organization-map";

interface OrganizationProfessionalMapPageProps {
  params: Promise<{ organizationId: string }>;
}

export default async function OrganizationProfessionalMapPage({
  params,
}: OrganizationProfessionalMapPageProps) {
  const { organizationId } = await params;
  const data = await loadOrganizationProfessionalMap(organizationId);

  return (
    <section className="page-stack">
      <div className="page-heading">
        <div>
          <p className="eyebrow">Organization professional map</p>
          <h1>Explicit professional relationships</h1>
          <p>
            Review roles, public business contact channels and reporting-line claims for
            one organization without inferring missing hierarchy.
          </p>
        </div>
        <Link className="professional-back-link" href="/professional-context">
          Back to professional context
        </Link>
      </div>
      <OrganizationMap data={data} />
    </section>
  );
}
