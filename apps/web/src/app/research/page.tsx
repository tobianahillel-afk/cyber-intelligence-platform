import { loadPublicResourcePage } from "@/features/public-footprint/api";
import type {
  PublicClaimType,
  PublicResourceKind,
  ResourceRetrievalState,
} from "@/features/public-footprint/types";
import { loadResearchPlans } from "@/features/research-plans/api";
import { ResearchEvidenceLibrary } from "@/features/research-plans/research-evidence-library";
import { ResearchPlanTable } from "@/features/research-plans/research-plan-table";

const allowedKinds = new Set<PublicResourceKind>([
  "sitemap",
  "feed",
  "structured_data",
  "web_page",
  "document",
  "repository",
  "archive_snapshot",
  "search_result",
]);
const allowedRetrievalStates = new Set<ResourceRetrievalState>([
  "discovered",
  "fetched",
  "not_modified",
  "changed",
  "tombstoned",
  "quarantined",
]);
const allowedClaimTypes = new Set<PublicClaimType>([
  "contract_or_project",
  "technology_or_architecture",
  "provider_partner_customer",
  "security_or_compliance_objective",
  "professional_contact_path",
  "corporate_change",
]);

interface ResearchPageProps {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}

export default async function ResearchPage({ searchParams }: ResearchPageProps) {
  const parameters = await searchParams;
  const query = first(parameters.q);
  const sourceId = first(parameters.source_id);
  const kind = parseKind(first(parameters.kind));
  const retrievalState = parseRetrievalState(first(parameters.retrieval_state));
  const claimType = parseClaimType(first(parameters.claim_type));
  const [plans, evidence] = await Promise.all([
    loadResearchPlans(),
    loadPublicResourcePage({ query, sourceId, kind, retrievalState, claimType }),
  ]);
  const summary = [
    { label: "Research plans", value: plans.total },
    {
      label: "Approved / active",
      value: plans.items.filter((plan) =>
        ["approved", "in_progress"].includes(plan.state),
      ).length,
    },
    {
      label: "Paused plans",
      value: plans.items.filter((plan) => plan.state === "paused").length,
    },
    { label: "Persisted evidence", value: evidence.total },
  ] as const;

  return (
    <section className="page-stack research-workspace">
      <div className="page-heading">
        <div>
          <p className="eyebrow">Governed analyst research</p>
          <h1>Research</h1>
          <p>
            Plan bounded research, inspect persisted eligibility and evidence, and hand off manual
            actions without turning an analyst question into unrestricted provider execution.
          </p>
        </div>
        <span className="live-label">Database-first control plane</span>
      </div>

      <div className="summary-grid" aria-label="Research workspace summary">
        {summary.map((item) => (
          <article className="summary-card" key={item.label}>
            <span>{item.label}</span>
            <strong>{item.value}</strong>
          </article>
        ))}
      </div>

      <section className="panel research-safety-banner">
        Research question ≠ permission to use every source. Eligible research ≠ captured evidence
        ≠ commercial signal or opportunity ≠ outreach authorization. Manual search link ≠
        automated provider execution.
      </section>

      <section className="panel" aria-labelledby="research-plans-title">
        <div className="panel-heading">
          <div>
            <h2 id="research-plans-title">Governed research plans</h2>
            <p>
              {plans.total} persisted plan(s). Runtime, quota, provider authorization and budget are
              re-evaluated before a new attempt is created.
            </p>
          </div>
        </div>
        {plans.items.length > 0 ? (
          <ResearchPlanTable plans={plans.items} />
        ) : (
          <div className="empty-state">
            <h3>No research plans yet</h3>
            <p>
              The workspace is ready for bounded plans; it does not auto-create research or launch
              a source from the page render.
            </p>
          </div>
        )}
      </section>

      <ResearchEvidenceLibrary
        page={evidence}
        query={query}
        sourceId={sourceId}
        kind={kind}
        retrievalState={retrievalState}
        claimType={claimType}
      />
    </section>
  );
}

function first(value: string | string[] | undefined): string {
  return (Array.isArray(value) ? value[0] : value) ?? "";
}

function parseKind(value: string): PublicResourceKind | undefined {
  return allowedKinds.has(value as PublicResourceKind) ? (value as PublicResourceKind) : undefined;
}

function parseRetrievalState(value: string): ResourceRetrievalState | undefined {
  return allowedRetrievalStates.has(value as ResourceRetrievalState)
    ? (value as ResourceRetrievalState)
    : undefined;
}

function parseClaimType(value: string): PublicClaimType | undefined {
  return allowedClaimTypes.has(value as PublicClaimType) ? (value as PublicClaimType) : undefined;
}
