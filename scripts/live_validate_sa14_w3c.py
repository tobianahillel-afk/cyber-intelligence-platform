from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

from cip.adapters.sources.w3c_standards.registry import W3cAffiliationTarget
from cip.modules.collection_orchestration.application.w3c_standard_adapter import W3cStandardAdapter
from cip.modules.source_governance.infrastructure.registry import load_source_registry

POLICY_PATH = Path("policies/sources.search_archives.yml")
ORG_ID = UUID("74b2a087-10ce-5d99-a90c-5aa1c0fabf6f")


def main() -> None:
    entry = next(
        item
        for item in load_source_registry(POLICY_PATH)
        if item.policy.id == "w3c-affiliation-specification-metadata"
    )
    target = W3cAffiliationTarget(
        target_id="lbnl-controlled-live",
        organization_id=ORG_ID,
        canonical_name="Lawrence Berkeley National Laboratory",
        affiliation_id=1015,
        enabled=True,
    )
    now = datetime.now(UTC)
    batch = W3cStandardAdapter(entry, (target,), timeout_seconds=30).collect(
        collection_job_id=uuid4(),
        checkpoint_payload=None,
        collected_at=now,
        retention_until=now + timedelta(days=180),
    )
    observations = len(batch.observations)
    projections = len(batch.public_footprint_projections)
    if observations < 1 or projections != observations:
        raise RuntimeError("W3C live proof did not preserve specification metadata")
    if observations > 20:
        raise RuntimeError("W3C live proof exceeded bounded result count")
    if any(projection.claims for projection in batch.public_footprint_projections):
        raise RuntimeError("W3C standards discovery unexpectedly produced claims")
    if any(
        projection.resource.retrieval_state.value != "quarantined"
        for projection in batch.public_footprint_projections
    ):
        raise RuntimeError("W3C results escaped quarantine")
    if any(
        not (
            projection.resource.canonical_url.startswith("https://www.w3.org/")
            or projection.resource.canonical_url.startswith("https://w3.org/")
            or projection.resource.canonical_url.startswith("https://api.w3.org/specifications/")
        )
        for projection in batch.public_footprint_projections
    ):
        raise RuntimeError("W3C live result escaped approved metadata URL boundary")
    if any(
        "Participants, editors, versions and specification body were not retrieved"
        not in (projection.version.excerpt or "")
        for projection in batch.public_footprint_projections
    ):
        raise RuntimeError("W3C live result lost metadata-only boundary")
    print(
        "SA-14 W3C live validation passed: "
        f"observations={observations} projections={projections} claims=0 "
        "person_fetches=0 specification_body_fetches=0"
    )


if __name__ == "__main__":
    main()
