from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

from cip.adapters.sources.public_web.registry import PublicWebTarget
from cip.modules.collection_orchestration.application.common_crawl_adapter import (
    CommonCrawlIndexAdapter,
)
from cip.modules.collection_orchestration.application.common_crawl_search_bridge import (
    COMMON_CRAWL_PROVIDER_ID,
)
from cip.modules.collection_orchestration.application.ports import AdapterCollectionBatch
from cip.modules.source_governance.infrastructure.registry import load_source_registry

POLICY_PATH = Path("policies/sources.search_archives.yml")
ORG_ID = UUID("7a0b182e-353e-5a61-8be4-703e935e227d")
_TARGET_ID = "sa15-common-crawl-normalized-live"


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
    routing = _assert_live_truth(batch)
    print(
        "SA-15 C1 production-integrated live validation passed: "
        f"observations={len(batch.observations)} "
        f"normalized_candidates={routing['candidate_count']} "
        f"automatic_routes={routing['public_web_route_count']} "
        f"provider={COMMON_CRAWL_PROVIDER_ID}"
    )


def _target(now: datetime) -> PublicWebTarget:
    return PublicWebTarget(
        id=_TARGET_ID,
        organization_id=ORG_ID,
        canonical_name="Common Crawl Foundation",
        base_url="https://commoncrawl.org",
        sitemap_urls=(),
        feed_urls=(),
        seed_urls=("https://commoncrawl.org/",),
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


def _assert_live_truth(batch: AdapterCollectionBatch) -> Mapping[str, object]:
    observations = len(batch.observations)
    if observations < 1 or observations > 50:
        raise RuntimeError("Common Crawl live adapter returned an invalid observation count")
    if len(batch.public_footprint_projections) != observations:
        raise RuntimeError("Common Crawl live adapter lost archive projections")
    if any(projection.claims for projection in batch.public_footprint_projections):
        raise RuntimeError("Common Crawl archive metadata unexpectedly produced claims")

    checkpoint = batch.checkpoint_payload
    if not isinstance(checkpoint, Mapping):
        raise RuntimeError("Common Crawl live adapter did not persist a checkpoint")
    routing = checkpoint.get("normalized_discovery")
    if not isinstance(routing, Mapping):
        raise RuntimeError(
            "Common Crawl production adapter did not execute normalized discovery routing"
        )
    if routing.get("provider_id") != COMMON_CRAWL_PROVIDER_ID:
        raise RuntimeError("Common Crawl normalized provider id drifted")

    candidate_count = routing.get("candidate_count")
    public_web_count = routing.get("public_web_route_count")
    source_review_count = routing.get("source_review_route_count")
    routes = routing.get("routes")
    if not isinstance(candidate_count, int) or not 1 <= candidate_count <= observations:
        raise RuntimeError("Common Crawl production adapter produced invalid normalized candidates")
    if public_web_count != candidate_count or source_review_count != 0:
        raise RuntimeError("Common Crawl normalized candidates did not all route to PUBLIC_WEB")
    if not isinstance(routes, list) or len(routes) != candidate_count:
        raise RuntimeError("Common Crawl production routing checkpoint lost routes")
    if any(not isinstance(route, Mapping) for route in routes):
        raise RuntimeError("Common Crawl production routing checkpoint contains invalid routes")
    if any(route.get("route_kind") != "public_web" for route in routes):
        raise RuntimeError("Common Crawl normalized candidate failed governed PUBLIC_WEB routing")
    if any(route.get("public_web_target_id") != _TARGET_ID for route in routes):
        raise RuntimeError("Common Crawl normalized route lost governed target provenance")
    return routing


if __name__ == "__main__":
    main()
