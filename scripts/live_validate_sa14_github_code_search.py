from __future__ import annotations

from datetime import UTC, datetime, timedelta
from os import environ
from pathlib import Path
from uuid import UUID, uuid4

from cip.adapters.sources.developer_ecosystem.registry import (
    DeveloperEcosystemTarget,
    DeveloperTargetKind,
)
from cip.modules.collection_orchestration.application.github_code_search_adapter import (
    GitHubCodeSearchAdapter,
)
from cip.modules.public_footprint.domain.search import SearchQueryTemplate
from cip.modules.source_governance.infrastructure.registry import load_source_registry

POLICY_PATH = Path("policies/sources.search_archives.yml")
ORG_ID = UUID("7c043f8d-aa93-5c10-94f4-d0ce92fcd5a4")


def main() -> None:
    token = environ.get("GITHUB_TOKEN", "").strip()
    if not token:
        raise RuntimeError("GITHUB_TOKEN is required for controlled GitHub code-search live proof")
    entry = next(
        item
        for item in load_source_registry(POLICY_PATH)
        if item.policy.id == "github-code-search-metadata"
    )
    now = datetime.now(UTC)
    target = DeveloperEcosystemTarget(
        target_id="github-provider-live",
        organization_id=ORG_ID,
        kind=DeveloperTargetKind.GITHUB_ORG,
        namespace="github",
        enabled=True,
    )
    template = SearchQueryTemplate(
        id="security-policy-metadata-live",
        version=1,
        query_pattern="security org:{organization} filename:SECURITY.md",
        purpose="public-security-policy-discovery",
        enabled=True,
    )
    batch = GitHubCodeSearchAdapter(
        entry,
        (target,),
        (template,),
        token_provider=lambda: token,
        timeout_seconds=30,
    ).collect(
        collection_job_id=uuid4(),
        checkpoint_payload=None,
        collected_at=now,
        retention_until=now + timedelta(days=90),
    )
    observations = len(batch.observations)
    projections = len(batch.public_footprint_projections)
    if observations < 1 or projections != observations:
        raise RuntimeError("GitHub code-search live proof did not preserve metadata hits")
    if observations > 20:
        raise RuntimeError("GitHub code-search live proof exceeded bounded page size")
    if any(projection.claims for projection in batch.public_footprint_projections):
        raise RuntimeError("GitHub code-search metadata unexpectedly produced claims")
    if any(
        projection.resource.retrieval_state.value != "quarantined"
        for projection in batch.public_footprint_projections
    ):
        raise RuntimeError("GitHub code-search results escaped quarantine")
    if any(
        "file content not retrieved" not in (projection.version.excerpt or "")
        for projection in batch.public_footprint_projections
    ):
        raise RuntimeError("GitHub code-search result lost metadata-only boundary")
    if any(
        not projection.resource.canonical_url.startswith("https://github.com/github/")
        for projection in batch.public_footprint_projections
    ):
        raise RuntimeError("GitHub code-search live result escaped controlled organization")
    print(
        "SA-14 GitHub code-search live validation passed: "
        f"observations={observations} projections={projections} claims=0 content_fetches=0"
    )


if __name__ == "__main__":
    main()
