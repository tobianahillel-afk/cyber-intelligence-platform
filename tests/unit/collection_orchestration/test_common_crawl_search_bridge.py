from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

import httpx
import pytest

from cip.adapters.sources.public_web.registry import PublicWebTarget
from cip.modules.collection_orchestration.application.common_crawl_adapter import (
    CommonCrawlIndexAdapter,
)
from cip.modules.collection_orchestration.application.common_crawl_search_bridge import (
    COMMON_CRAWL_PROVIDER_ID,
    COMMON_CRAWL_PURPOSE,
    COMMON_CRAWL_TEMPLATE_ID,
    build_common_crawl_search_plan,
    common_crawl_batch_to_search_execution,
    normalize_common_crawl_batch,
)
from cip.modules.public_footprint.domain.search_core import (
    SearchAcquisitionState,
    SearchQueryPlan,
)
from cip.modules.source_governance.infrastructure.registry import load_source_registry

NOW = datetime(2026, 8, 12, 11, 0, tzinfo=UTC)
RETENTION = NOW + timedelta(days=365)
ORG_ID = UUID("5b49c59a-cd47-5b9c-bdf0-dba39055cce5")
POLICY_PATH = Path("policies/sources.search_archives.yml")


def test_common_crawl_search_plan_uses_explicit_archive_identity() -> None:
    plan = build_common_crawl_search_plan(
        organization_id=ORG_ID,
        organization_name="Controlled Example",
        target_base_url="https://example.com:443/path?b=2&a=1",
        created_at=NOW,
    )
    assert plan.template_id == COMMON_CRAWL_TEMPLATE_ID
    assert plan.purpose == COMMON_CRAWL_PURPOSE
    assert plan.provider_ids == (COMMON_CRAWL_PROVIDER_ID,)
    assert plan.rendered_query == "common-crawl:https://example.com/*"


def test_common_crawl_batch_enters_normalized_discovery_with_provenance() -> None:
    batch = _batch()
    plan = _plan()
    execution = common_crawl_batch_to_search_execution(plan, batch, executed_at=NOW)
    candidates = normalize_common_crawl_batch(plan, batch, executed_at=NOW)

    assert execution.provider_id == COMMON_CRAWL_PROVIDER_ID
    assert len(execution.results) == 2
    assert [result.rank for result in execution.results] == [1, 2]
    assert all(result.source_id == COMMON_CRAWL_PROVIDER_ID for result in execution.results)
    assert len(candidates) == 2
    assert {candidate.target_url for candidate in candidates} == {
        "https://example.com/public/alpha",
        "https://example.com/public/beta?a=1&b=2",
    }
    assert all(
        candidate.acquisition_state is SearchAcquisitionState.UNROUTED
        for candidate in candidates
    )
    assert all(candidate.provider_count == 1 for candidate in candidates)
    assert all(
        hit.provider_id == COMMON_CRAWL_PROVIDER_ID
        for candidate in candidates
        for hit in candidate.provider_hits
    )
    assert all("WARC body not retrieved" in candidate.snippet for candidate in candidates)
    assert all(not projection.claims for projection in batch.public_footprint_projections)


def test_common_crawl_normalization_is_deterministic() -> None:
    batch = _batch()
    first = normalize_common_crawl_batch(_plan(), batch, executed_at=NOW)
    second = normalize_common_crawl_batch(_plan(), batch, executed_at=NOW)
    assert first == second
    assert [candidate.best_rank for candidate in first] == [1, 2]


def test_common_crawl_bridge_rejects_non_archive_plan() -> None:
    invalid_plan = SearchQueryPlan(
        organization_id=ORG_ID,
        organization_name="Controlled Example",
        template_id="generic-search",
        template_version=1,
        purpose="company-research",
        rendered_query="Controlled Example",
        provider_ids=(COMMON_CRAWL_PROVIDER_ID,),
        created_at=NOW,
    )
    with pytest.raises(ValueError, match="archive-discovery template"):
        common_crawl_batch_to_search_execution(invalid_plan, _batch(), executed_at=NOW)


def test_common_crawl_bridge_rejects_cross_organization_projection() -> None:
    other_plan = build_common_crawl_search_plan(
        organization_id=UUID("d4d28967-bf52-553a-937e-719f6185c940"),
        organization_name="Other Organization",
        target_base_url="https://example.com",
        created_at=NOW,
    )
    with pytest.raises(ValueError, match="organization does not match"):
        common_crawl_batch_to_search_execution(other_plan, _batch(), executed_at=NOW)


def _batch():
    adapter = CommonCrawlIndexAdapter(
        _entry(),
        (_target(),),
        transport=httpx.MockTransport(_provider_handler),
    )
    return adapter.collect(
        collection_job_id=uuid4(),
        checkpoint_payload=None,
        collected_at=NOW,
        retention_until=RETENTION,
    )


def _plan() -> SearchQueryPlan:
    return build_common_crawl_search_plan(
        organization_id=ORG_ID,
        organization_name="Controlled Example",
        target_base_url="https://example.com",
        created_at=NOW,
    )


def _entry():
    return next(
        entry
        for entry in load_source_registry(POLICY_PATH)
        if entry.policy.id == COMMON_CRAWL_PROVIDER_ID
    )


def _target() -> PublicWebTarget:
    return PublicWebTarget(
        id="common-crawl-normalized-discovery-test",
        organization_id=ORG_ID,
        canonical_name="Controlled Example",
        base_url="https://example.com",
        sitemap_urls=(),
        feed_urls=(),
        discover_security_txt=False,
        allowed_path_prefixes=("/public",),
        enabled=True,
        authorization_reference="sa15-c1-test",
        authorization_reviewed_at=NOW,
        terms_url="https://example.com/",
    )


def _provider_handler(request: httpx.Request) -> httpx.Response:
    if request.url.path == "/collinfo.json":
        return httpx.Response(
            200,
            json=[
                {
                    "id": "CC-MAIN-2026-30",
                    "name": "July 2026 Index",
                    "timegate": "https://index.commoncrawl.org/CC-MAIN-2026-30/",
                    "cdx-api": "https://index.commoncrawl.org/CC-MAIN-2026-30-index",
                    "from": "2026-07-10T07:05:34",
                    "to": "2026-07-23T01:13:28",
                }
            ],
            request=request,
        )
    body = "\n".join(
        (
            json.dumps(_capture("https://example.com/public/alpha", "DIGEST-A")),
            json.dumps(_capture("https://example.com/public/beta?b=2&a=1", "DIGEST-B")),
        )
    )
    return httpx.Response(200, text=body, request=request)


def _capture(url: str, digest: str) -> dict[str, str]:
    return {
        "timestamp": "20260715120000",
        "url": url,
        "mime": "text/html",
        "status": "200",
        "digest": digest,
        "length": "1234",
        "offset": "5678",
        "filename": "crawl-data/CC-MAIN-2026-30/segments/example/warc/example.warc.gz",
    }
