from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

from cip.adapters.sources.public_web.registry import PublicWebTarget
from cip.modules.collection_orchestration.application.common_crawl_adapter import (
    CommonCrawlIndexAdapter,
)
from cip.modules.collection_orchestration.application.common_crawl_search_bridge import (
    COMMON_CRAWL_PROVIDER_ID,
    build_common_crawl_search_plan,
    normalize_common_crawl_batch,
)
from cip.modules.collection_orchestration.application.search_acquisition_router import (
    SearchAcquisitionRouteKind,
    route_search_discovery_candidates,
)
from cip.modules.source_governance.infrastructure.registry import load_source_registry

POLICY_PATH = Path("policies/sources.search_archives.yml")
ORG_ID = UUID("7a0b182e-353e-5a61-8be4-703e935e227d")


def main() -> None:
    now = datetime.now(UTC)
    entry = next(
        item
        for item in load_source_registry(POLICY_PATH)
        if item.policy.id == COMMON_CRAWL_PROVIDER_ID
    )
    target = _target(now)
    batch = CommonCrawlIndexAdapter(entry, (target,), timeout_seconds=30).collect(
        collection_job_id=uuid4(),
        checkpoint_payload=None,
        collected_at=now,
        retention_until=now + timedelta(days=365),
    )
    plan = build_common_crawl_search_plan(
        organization_id=ORG_ID,
        organization_name="Common Crawl Foundation",
        target_base_url=target.base_url,
        created_at=now,
    )
    candidates = normalize_common_crawl_batch(plan, batch, executed_at=now)
    routes = route_search_discovery_candidates(candidates, (target,), routed_at=now)
    _assert_live_truth(batch, candidates, routes)
    print(
        "SA-15 C1 live validation passed: "
        f"observations={len(batch.observations)} "
        f"normalized_candidates={len(candidates)} "
        f"automatic_routes={len(routes)} "
        f"provider={COMMON_CRAWL_PROVIDER_ID}"
    )


def _target(now: datetime) -> PublicWebTarget:
    return PublicWebTarget(
        id="sa15-common-crawl-normalized-live",
        organization_id=ORG_ID,
        canonical_name="Common Crawl Foundation",
        base_url="https://commoncrawl.org",
        sitemap_urls=(),
        feed_urls=(),
        discover_security_txt=False,
        allowed_path_prefixes=("/",),
        enabled=True,
        authorization_reference="sa15-c1-controlled-common-crawl-live",
        authorization_reviewed_at=now,
        terms_url="https://commoncrawl.org/terms-of-use",
        max_pages=50,
        max_total_bytes=2_000_000,
        max_resource_bytes=1_000_000,
        max_redirects=0,
    )


def _assert_live_truth(batch, candidates, routes) -> None:
    observations = len(batch.observations)
    if observations < 1 or observations > 50:
        raise RuntimeError("Common Crawl live bridge returned an invalid observation count")
    if len(batch.public_footprint_projections) != observations:
        raise RuntimeError("Common Crawl live bridge lost archive projections")
    if len(candidates) < 1 or len(candidates) > observations:
        raise RuntimeError("Common Crawl live bridge produced invalid normalized candidates")
    if len(routes) != len(candidates):
        raise RuntimeError("Common Crawl normalized candidates did not all enter routing")
    if any(projection.claims for projection in batch.public_footprint_projections):
        raise RuntimeError("Common Crawl archive metadata unexpectedly produced claims")
    if any(candidate.provider_count != 1 for candidate in candidates):
        raise RuntimeError("Common Crawl provider provenance was not preserved")
    if any(
        hit.provider_id != COMMON_CRAWL_PROVIDER_ID
        for candidate in candidates
        for hit in candidate.provider_hits
    ):
        raise RuntimeError("Common Crawl normalized provider id drifted")
    if any(route.route_kind is not SearchAcquisitionRouteKind.PUBLIC_WEB for route in routes):
        raise RuntimeError("Common Crawl normalized candidate failed governed public-web routing")
    if any(not route.automatic for route in routes):
        raise RuntimeError("Common Crawl normalized route is not automatic")


if __name__ == "__main__":
    main()
