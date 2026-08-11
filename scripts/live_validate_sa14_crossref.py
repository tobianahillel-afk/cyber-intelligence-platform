from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

from cip.adapters.sources.crossref_publications.registry import CrossrefPublicationTarget
from cip.modules.collection_orchestration.application.crossref_publication_adapter import (
    CrossrefPublicationAdapter,
)
from cip.modules.source_governance.infrastructure.registry import load_source_registry

POLICY_PATH = Path("policies/sources.search_archives.yml")
ORG_ID = UUID("74b2a087-10ce-5d99-a90c-5aa1c0fabf6f")


def main() -> None:
    entry = next(
        item
        for item in load_source_registry(POLICY_PATH)
        if item.policy.id == "crossref-publication-metadata"
    )
    now = datetime.now(UTC)
    target = CrossrefPublicationTarget(
        target_id="goethe-university-live",
        organization_id=ORG_ID,
        canonical_name="Goethe University Frankfurt",
        ror_id="04cvxnb49",
        enabled=True,
    )
    batch = CrossrefPublicationAdapter(
        entry,
        (target,),
        timeout_seconds=30,
    ).collect(
        collection_job_id=uuid4(),
        checkpoint_payload=None,
        collected_at=now,
        retention_until=now + timedelta(days=180),
    )
    observations = len(batch.observations)
    projections = len(batch.public_footprint_projections)
    if observations < 1 or projections != observations:
        raise RuntimeError("Crossref live proof did not preserve ROR-associated metadata")
    if observations > 20:
        raise RuntimeError("Crossref live proof exceeded bounded page size")
    if any(projection.claims for projection in batch.public_footprint_projections):
        raise RuntimeError("Crossref publication discovery unexpectedly produced claims")
    if any(
        projection.resource.retrieval_state.value != "quarantined"
        for projection in batch.public_footprint_projections
    ):
        raise RuntimeError("Crossref results escaped quarantine")
    if any(
        not projection.resource.canonical_url.startswith("https://doi.org/")
        for projection in batch.public_footprint_projections
    ):
        raise RuntimeError("Crossref live result escaped DOI metadata boundary")
    if any(
        "Authors, abstract and full text not retrieved" not in (projection.version.excerpt or "")
        for projection in batch.public_footprint_projections
    ):
        raise RuntimeError("Crossref live result lost metadata-only boundary")
    print(
        "SA-14 Crossref live validation passed: "
        f"observations={observations} projections={projections} claims=0 full_text_fetches=0"
    )


if __name__ == "__main__":
    main()
