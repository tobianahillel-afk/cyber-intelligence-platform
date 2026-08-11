from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest

from cip.modules.public_footprint.domain import (
    SearchAcquisitionState,
    SearchProviderExecution,
    SearchQueryPlan,
    SearchQueryTemplate,
    SearchResultLead,
    normalize_search_executions,
)

NOW = datetime(2026, 8, 11, 20, 0, tzinfo=UTC)
ORGANIZATION_ID = UUID("00000000-0000-0000-0000-000000001501")


def test_query_plan_requires_an_enabled_template_and_unique_providers() -> None:
    disabled = _template(enabled=False)

    with pytest.raises(ValueError, match="enabled"):
        SearchQueryPlan.from_template(
            organization_id=ORGANIZATION_ID,
            organization_name="Example Corp",
            template=disabled,
            provider_ids=("brave-web-search",),
            created_at=NOW,
        )

    with pytest.raises(ValueError, match="unique"):
        SearchQueryPlan.from_template(
            organization_id=ORGANIZATION_ID,
            organization_name="Example Corp",
            template=_template(),
            provider_ids=("brave-web-search", "BRAVE-WEB-SEARCH"),
            created_at=NOW,
        )


def test_normalization_deduplicates_canonical_url_and_preserves_each_provider_hit() -> None:
    plan = _plan()
    brave = SearchProviderExecution(
        provider_id="brave-web-search",
        organization_id=ORGANIZATION_ID,
        rendered_query=plan.rendered_query,
        query_template_id=plan.template_id,
        query_template_version=plan.template_version,
        executed_at=NOW,
        results=(
            _lead(
                provider="brave-web-search",
                key="brave-1",
                url="https://Example.com:443/security?a=1&b=2#section",
                rank=2,
                title="Example security page from Brave",
            ),
        ),
    )
    mojeek = SearchProviderExecution(
        provider_id="mojeek-web-search-metadata",
        organization_id=ORGANIZATION_ID,
        rendered_query=plan.rendered_query,
        query_template_id=plan.template_id,
        query_template_version=plan.template_version,
        executed_at=NOW + timedelta(seconds=1),
        results=(
            _lead(
                provider="mojeek-web-search-metadata",
                key="mojeek-7",
                url="https://example.com/security?b=2&a=1",
                rank=1,
                title="Example security page from Mojeek",
            ),
            _lead(
                provider="mojeek-web-search-metadata",
                key="mojeek-8",
                url="https://example.com/architecture",
                rank=4,
                title="Example architecture",
            ),
        ),
    )

    candidates = normalize_search_executions(plan, (brave, mojeek))

    assert len(candidates) == 2
    shared = candidates[0]
    assert shared.target_url == "https://example.com/security?a=1&b=2"
    assert shared.title == "Example security page from Mojeek"
    assert shared.best_rank == 1
    assert shared.provider_count == 2
    assert [hit.provider_id for hit in shared.provider_hits] == [
        "mojeek-web-search-metadata",
        "brave-web-search",
    ]
    assert {hit.source_record_key for hit in shared.provider_hits} == {
        "brave-1",
        "mojeek-7",
    }
    assert shared.acquisition_state is SearchAcquisitionState.UNROUTED
    assert candidates[1].target_url == "https://example.com/architecture"


def test_normalization_rejects_execution_outside_plan_or_with_wrong_query() -> None:
    plan = _plan()
    outside_provider = SearchProviderExecution(
        provider_id="unplanned-search",
        organization_id=ORGANIZATION_ID,
        rendered_query=plan.rendered_query,
        query_template_id=plan.template_id,
        query_template_version=plan.template_version,
        executed_at=NOW,
        results=(),
    )
    wrong_query = SearchProviderExecution(
        provider_id="brave-web-search",
        organization_id=ORGANIZATION_ID,
        rendered_query="different query",
        query_template_id=plan.template_id,
        query_template_version=plan.template_version,
        executed_at=NOW,
        results=(),
    )

    with pytest.raises(ValueError, match="not part"):
        normalize_search_executions(plan, (outside_provider,))
    with pytest.raises(ValueError, match="query does not match"):
        normalize_search_executions(plan, (wrong_query,))


def test_execution_rejects_provider_or_template_mismatch_in_results() -> None:
    plan = _plan()

    with pytest.raises(ValueError, match="provider source id"):
        SearchProviderExecution(
            provider_id="brave-web-search",
            organization_id=ORGANIZATION_ID,
            rendered_query=plan.rendered_query,
            query_template_id=plan.template_id,
            query_template_version=plan.template_version,
            executed_at=NOW,
            results=(
                _lead(
                    provider="mojeek-web-search-metadata",
                    key="wrong-provider",
                    url="https://example.com/security",
                    rank=1,
                    title="Wrong provider",
                ),
            ),
        )


def test_duplicate_execution_for_same_provider_is_rejected() -> None:
    plan = _plan()
    execution = SearchProviderExecution(
        provider_id="brave-web-search",
        organization_id=ORGANIZATION_ID,
        rendered_query=plan.rendered_query,
        query_template_id=plan.template_id,
        query_template_version=plan.template_version,
        executed_at=NOW,
        results=(),
    )

    with pytest.raises(ValueError, match="at most one execution"):
        normalize_search_executions(plan, (execution, execution))


def _plan() -> SearchQueryPlan:
    return SearchQueryPlan.from_template(
        organization_id=ORGANIZATION_ID,
        organization_name="Example Corp",
        template=_template(),
        provider_ids=("brave-web-search", "mojeek-web-search-metadata"),
        created_at=NOW,
    )


def _template(*, enabled: bool = True) -> SearchQueryTemplate:
    return SearchQueryTemplate(
        id="organization-security-footprint",
        version=3,
        query_pattern='"{organization}" security architecture',
        purpose="corporate-public-footprint",
        enabled=enabled,
    )


def _lead(
    *,
    provider: str,
    key: str,
    url: str,
    rank: int,
    title: str,
) -> SearchResultLead:
    return SearchResultLead(
        organization_id=ORGANIZATION_ID,
        source_id=provider,
        source_record_key=key,
        target_url=url,
        title=title,
        snippet="Search metadata only; original content has not been retrieved.",
        rank=rank,
        observed_at=NOW,
        query_template_id="organization-security-footprint",
        query_template_version=3,
    )
