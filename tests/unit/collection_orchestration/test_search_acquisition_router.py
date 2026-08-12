from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest

from cip.adapters.sources.public_web.registry import PublicWebTarget
from cip.modules.collection_orchestration.application.search_acquisition_router import (
    SearchAcquisitionRouteKind,
    route_search_discovery_candidates,
)
from cip.modules.public_footprint.domain.scope import CrawlUsage
from cip.modules.public_footprint.domain.search_core import (
    SearchAcquisitionState,
    SearchDiscoveryCandidate,
    SearchProviderHit,
)

NOW = datetime(2026, 8, 12, 0, 45, tzinfo=UTC)
ORGANIZATION_ID = UUID("00000000-0000-0000-0000-000000001509")


def test_same_origin_candidate_routes_to_executable_governed_public_web_target() -> None:
    routes = route_search_discovery_candidates(
        (_candidate("https://example.com/security/report"),),
        (_target(),),
        routed_at=NOW,
    )

    route = routes[0]
    assert route.route_kind is SearchAcquisitionRouteKind.PUBLIC_WEB
    assert route.public_web_target_id == "example-company"
    assert route.automatic is True
    assert route.requested_url == "https://example.com/security/report"
    assert route.candidate.acquisition_state is SearchAcquisitionState.ROUTED_PUBLIC_WEB


def test_off_origin_candidate_requires_source_review_instead_of_generic_fetch() -> None:
    route = route_search_discovery_candidates(
        (_candidate("https://third-party.example/research"),),
        (_target(),),
        routed_at=NOW,
    )[0]

    assert route.route_kind is SearchAcquisitionRouteKind.SOURCE_REVIEW
    assert route.public_web_target_id is None
    assert route.automatic is False
    assert route.candidate.acquisition_state is SearchAcquisitionState.REQUIRES_SOURCE_REVIEW


def test_same_origin_candidate_outside_allowed_path_requires_source_review() -> None:
    target = _target(allowed_path_prefixes=("/security",))
    route = route_search_discovery_candidates(
        (_candidate("https://example.com/careers"),),
        (target,),
        routed_at=NOW,
    )[0]

    assert route.route_kind is SearchAcquisitionRouteKind.SOURCE_REVIEW
    assert route.candidate.acquisition_state is SearchAcquisitionState.REQUIRES_SOURCE_REVIEW


def test_expired_target_cannot_receive_automatic_search_acquisition() -> None:
    target = _target(authorization_expires_at=NOW - timedelta(seconds=1))
    route = route_search_discovery_candidates(
        (_candidate("https://example.com/security"),),
        (target,),
        routed_at=NOW,
    )[0]

    assert route.route_kind is SearchAcquisitionRouteKind.SOURCE_REVIEW


def test_router_fails_closed_when_candidate_matches_multiple_governed_targets() -> None:
    first = _target(target_id="one")
    second = _target(target_id="two")

    with pytest.raises(ValueError, match="multiple governed"):
        route_search_discovery_candidates(
            (_candidate("https://example.com/security"),),
            (first, second),
            routed_at=NOW,
        )


def test_automatic_routes_sort_before_source_review_routes() -> None:
    routes = route_search_discovery_candidates(
        (
            _candidate("https://third-party.example/research"),
            _candidate("https://example.com/security"),
        ),
        (_target(),),
        routed_at=NOW,
    )

    assert [route.route_kind for route in routes] == [
        SearchAcquisitionRouteKind.PUBLIC_WEB,
        SearchAcquisitionRouteKind.SOURCE_REVIEW,
    ]


def test_router_consumes_page_budget_across_candidates_and_existing_usage() -> None:
    target = _target(max_pages=2)
    routes = route_search_discovery_candidates(
        (
            _candidate("https://example.com/security/one"),
            _candidate("https://example.com/security/two"),
        ),
        (target,),
        routed_at=NOW,
        target_usage={target.id: CrawlUsage(pages_fetched=1)},
    )

    assert [route.route_kind for route in routes] == [
        SearchAcquisitionRouteKind.PUBLIC_WEB,
        SearchAcquisitionRouteKind.SOURCE_REVIEW,
    ]
    assert routes[0].requested_url == "https://example.com/security/one"
    assert routes[1].requested_url == "https://example.com/security/two"


def _candidate(url: str) -> SearchDiscoveryCandidate:
    return SearchDiscoveryCandidate(
        organization_id=ORGANIZATION_ID,
        target_url=url,
        title="Search discovery",
        snippet="Provider metadata only",
        purpose="corporate-public-footprint",
        provider_hits=(
            SearchProviderHit(
                provider_id="brave-search-api",
                source_record_key=f"record:{url}",
                rank=1,
                observed_at=NOW,
                executed_at=NOW,
                title="Search discovery",
                snippet="Provider metadata only",
                rendered_query='"Example Corp" cybersecurity',
                query_template_id="security",
                query_template_version=1,
            ),
        ),
    )


def _target(
    *,
    target_id: str = "example-company",
    allowed_path_prefixes: tuple[str, ...] = ("/",),
    authorization_expires_at: datetime | None = None,
    max_pages: int = 100,
) -> PublicWebTarget:
    return PublicWebTarget(
        id=target_id,
        organization_id=ORGANIZATION_ID,
        canonical_name="Example Corp",
        base_url="https://example.com/",
        sitemap_urls=("https://example.com/sitemap.xml",),
        allowed_path_prefixes=allowed_path_prefixes,
        enabled=True,
        authorization_reference="sa15-router-test",
        authorization_reviewed_at=NOW - timedelta(days=1),
        authorization_expires_at=authorization_expires_at,
        max_pages=max_pages,
    )
