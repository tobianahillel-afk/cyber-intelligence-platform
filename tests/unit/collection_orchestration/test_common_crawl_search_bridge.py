from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from cip.modules.collection_orchestration.application.common_crawl_search_bridge import (
    COMMON_CRAWL_PROVIDER_ID,
    COMMON_CRAWL_PURPOSE,
    COMMON_CRAWL_TEMPLATE_ID,
    build_common_crawl_search_plan,
)

NOW = datetime(2026, 8, 12, 11, 0, tzinfo=UTC)
ORG_ID = UUID("5b49c59a-cd47-5b9c-bdf0-dba39055cce5")


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
