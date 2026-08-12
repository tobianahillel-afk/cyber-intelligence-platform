from __future__ import annotations

from datetime import datetime
from uuid import UUID

from cip.modules.collection_orchestration.application.ports import AdapterCollectionBatch
from cip.modules.public_footprint.domain.search import SearchResultLead
from cip.modules.public_footprint.domain.search_core import (
    SearchDiscoveryCandidate,
    SearchProviderExecution,
    SearchQueryPlan,
    normalize_search_executions,
)
from cip.modules.public_footprint.domain.url_identity import CanonicalUrl
from cip.shared.kernel.time import require_aware_utc

COMMON_CRAWL_PROVIDER_ID = "common-crawl-index"
COMMON_CRAWL_TEMPLATE_ID = "common-crawl-archive-discovery"
COMMON_CRAWL_TEMPLATE_VERSION = 1
COMMON_CRAWL_PURPOSE = "archive-discovery"
_MAX_COMMON_CRAWL_RESULTS = 50


def build_common_crawl_search_plan(
    *,
    organization_id: UUID,
    organization_name: str,
    target_base_url: str,
    created_at: datetime,
) -> SearchQueryPlan:
    origin = CanonicalUrl(target_base_url).origin
    return SearchQueryPlan(
        organization_id=organization_id,
        organization_name=organization_name,
        template_id=COMMON_CRAWL_TEMPLATE_ID,
        template_version=COMMON_CRAWL_TEMPLATE_VERSION,
        purpose=COMMON_CRAWL_PURPOSE,
        rendered_query=f"common-crawl:{origin}/*",
        provider_ids=(COMMON_CRAWL_PROVIDER_ID,),
        created_at=created_at,
    )


def common_crawl_batch_to_search_execution(
    plan: SearchQueryPlan,
    batch: AdapterCollectionBatch,
    *,
    executed_at: datetime,
) -> SearchProviderExecution:
    executed_at = require_aware_utc(executed_at, field_name="executed_at")
    _validate_plan(plan)
    projections = batch.public_footprint_projections
    if len(projections) > _MAX_COMMON_CRAWL_RESULTS:
        raise ValueError("Common Crawl normalized discovery exceeds the provider result bound")
    results = tuple(
        _search_result(plan, projection, rank=index + 1)
        for index, projection in enumerate(projections)
    )
    return SearchProviderExecution(
        provider_id=COMMON_CRAWL_PROVIDER_ID,
        organization_id=plan.organization_id,
        rendered_query=plan.rendered_query,
        query_template_id=plan.template_id,
        query_template_version=plan.template_version,
        executed_at=executed_at,
        results=results,
    )


def normalize_common_crawl_batch(
    plan: SearchQueryPlan,
    batch: AdapterCollectionBatch,
    *,
    executed_at: datetime,
) -> tuple[SearchDiscoveryCandidate, ...]:
    execution = common_crawl_batch_to_search_execution(
        plan,
        batch,
        executed_at=executed_at,
    )
    return normalize_search_executions(plan, (execution,))


def _validate_plan(plan: SearchQueryPlan) -> None:
    if plan.template_id != COMMON_CRAWL_TEMPLATE_ID:
        raise ValueError("Common Crawl bridge requires the archive-discovery template")
    if plan.template_version != COMMON_CRAWL_TEMPLATE_VERSION:
        raise ValueError("Common Crawl bridge requires the current template version")
    if plan.purpose != COMMON_CRAWL_PURPOSE:
        raise ValueError("Common Crawl bridge requires the archive-discovery purpose")
    if plan.provider_ids != (COMMON_CRAWL_PROVIDER_ID,):
        raise ValueError("Common Crawl bridge requires the Common Crawl provider only")


def _search_result(plan: SearchQueryPlan, projection, *, rank: int) -> SearchResultLead:
    resource = projection.resource
    version = projection.version
    if resource.organization_id != plan.organization_id:
        raise ValueError("Common Crawl projection organization does not match the query plan")
    if resource.source_id != COMMON_CRAWL_PROVIDER_ID:
        raise ValueError("Common Crawl bridge rejects projections from another source")
    if projection.claims:
        raise ValueError("Common Crawl archive discovery must not contain claims")
    if resource.retrieval_state.value != "quarantined":
        raise ValueError("Common Crawl archive discovery must remain quarantined")
    title = resource.title or f"Common Crawl capture of {resource.canonical_url}"
    snippet = version.excerpt or "Common Crawl archive index metadata; WARC body not retrieved."
    return SearchResultLead(
        organization_id=plan.organization_id,
        source_id=COMMON_CRAWL_PROVIDER_ID,
        source_record_key=resource.source_record_key,
        target_url=resource.canonical_url,
        title=title,
        snippet=snippet,
        rank=rank,
        observed_at=version.fetched_at,
        query_template_id=plan.template_id,
        query_template_version=plan.template_version,
    )
