from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

from cip.adapters.sources.public_web.registry import PublicWebTarget
from cip.modules.collection_orchestration.application.archive_cdx_adapter import (
    InternetArchiveCdxAdapter,
)
from cip.modules.public_footprint.domain.models import (
    PublicResourceKind,
    ResourceRetrievalState,
)
from cip.modules.source_governance.infrastructure.registry import load_source_registry

POLICY_PATH = Path("policies/sources.search_archives.yml")
ORG_ID = UUID("15712d0d-9054-50b4-8a26-e25d9ea1f509")
_TARGET_URL = "https://archive.org/about/terms.php"


def main() -> None:
    entry = next(
        item
        for item in load_source_registry(POLICY_PATH)
        if item.policy.id == "internet-archive-cdx"
    )
    now = datetime.now(UTC)
    target = PublicWebTarget(
        id="sa15-internet-archive-first-party",
        organization_id=ORG_ID,
        canonical_name="Internet Archive",
        base_url=_TARGET_URL,
        sitemap_urls=("https://archive.org/sitemap.xml",),
        feed_urls=(),
        discover_security_txt=False,
        allowed_path_prefixes=("/about",),
        enabled=True,
        authorization_reference="sa15-controlled-internet-archive-first-party-target",
        authorization_reviewed_at=now,
        terms_url=_TARGET_URL,
        max_pages=50,
        max_total_bytes=2_000_000,
        max_resource_bytes=1_000_000,
        max_redirects=0,
    )
    batch = InternetArchiveCdxAdapter(entry, (target,), timeout_seconds=90).collect(
        collection_job_id=uuid4(),
        checkpoint_payload=None,
        collected_at=now,
        retention_until=now + timedelta(days=365),
    )
    observations = len(batch.observations)
    projections = len(batch.public_footprint_projections)
    if not 1 <= observations <= 50 or projections != observations:
        raise RuntimeError("Internet Archive CDX live validation returned invalid capture counts")
    if any(projection.claims for projection in batch.public_footprint_projections):
        raise RuntimeError("Internet Archive CDX metadata unexpectedly produced claims")
    if any(
        projection.resource.kind is not PublicResourceKind.ARCHIVE_SNAPSHOT
        or projection.resource.retrieval_state is not ResourceRetrievalState.QUARANTINED
        for projection in batch.public_footprint_projections
    ):
        raise RuntimeError("Internet Archive CDX captures escaped archive quarantine")
    if any(
        projection.resource.source_id != "internet-archive-cdx"
        or not projection.resource.source_url.startswith("https://web.archive.org/web/")
        for projection in batch.public_footprint_projections
    ):
        raise RuntimeError("Internet Archive CDX provenance was not preserved")
    if any(
        "Historical archive index metadata" not in (projection.version.excerpt or "")
        for projection in batch.public_footprint_projections
    ):
        raise RuntimeError("Internet Archive CDX lost the metadata-only evidence boundary")
    if batch.checkpoint_payload != {"target_index": 0}:
        raise RuntimeError("Internet Archive CDX checkpoint did not converge for one target")
    print(
        "SA-15 L05 live validation passed: "
        f"target={_TARGET_URL} "
        f"internet_archive_cdx_observations={observations} "
        f"internet_archive_cdx_projections={projections} claims=0 bodies=0"
    )


if __name__ == "__main__":
    main()
