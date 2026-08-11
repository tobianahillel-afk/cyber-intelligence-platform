from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

from cip.adapters.sources.public_web.registry import PublicWebTarget
from cip.modules.collection_orchestration.application.common_crawl_adapter import (
    CommonCrawlIndexAdapter,
)
from cip.modules.source_governance.infrastructure.registry import load_source_registry

POLICY_PATH = Path("policies/sources.search_archives.yml")
ORG_ID = UUID("7a0b182e-353e-5a61-8be4-703e935e227d")


def main() -> None:
    entry = next(
        item
        for item in load_source_registry(POLICY_PATH)
        if item.policy.id == "common-crawl-index"
    )
    now = datetime.now(UTC)
    target = PublicWebTarget(
        id="common-crawl-provider-live",
        organization_id=ORG_ID,
        canonical_name="Common Crawl Foundation",
        base_url="https://commoncrawl.org",
        sitemap_urls=("https://commoncrawl.org/sitemap.xml",),
        feed_urls=(),
        discover_security_txt=False,
        allowed_path_prefixes=("/",),
        enabled=True,
        authorization_reference="sa14-controlled-common-crawl-provider-target",
        authorization_reviewed_at=now,
        terms_url="https://commoncrawl.org/terms-of-use",
        max_pages=50,
        max_total_bytes=2_000_000,
        max_resource_bytes=1_000_000,
        max_redirects=0,
    )
    batch = CommonCrawlIndexAdapter(entry, (target,), timeout_seconds=30).collect(
        collection_job_id=uuid4(),
        checkpoint_payload=None,
        collected_at=now,
        retention_until=now + timedelta(days=365),
    )
    observations = len(batch.observations)
    projections = len(batch.public_footprint_projections)
    if observations < 1 or projections != observations:
        raise RuntimeError("Common Crawl live validation did not preserve index captures")
    if any(projection.claims for projection in batch.public_footprint_projections):
        raise RuntimeError("Common Crawl index metadata unexpectedly produced claims")
    if any(
        projection.resource.retrieval_state.value != "quarantined"
        for projection in batch.public_footprint_projections
    ):
        raise RuntimeError("Common Crawl captures escaped quarantine")
    if any(
        "WARC body not retrieved" not in (projection.version.excerpt or "")
        for projection in batch.public_footprint_projections
    ):
        raise RuntimeError("Common Crawl capture lost metadata-only boundary")
    crawl_ids = batch.checkpoint_payload.get("crawl_ids", {})
    print(
        "SA-14 live validation passed: "
        f"common_crawl_observations={observations} "
        f"common_crawl_projections={projections} "
        f"crawl_ids={crawl_ids}"
    )


if __name__ == "__main__":
    main()
