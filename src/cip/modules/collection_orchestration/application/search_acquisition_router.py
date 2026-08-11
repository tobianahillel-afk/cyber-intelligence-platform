from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from enum import StrEnum

from cip.adapters.sources.public_web.registry import PublicWebTarget
from cip.modules.public_footprint.domain.scope import CrawlUsage
from cip.modules.public_footprint.domain.search_core import (
    SearchAcquisitionState,
    SearchDiscoveryCandidate,
)
from cip.modules.public_footprint.domain.url_identity import same_origin
from cip.shared.kernel.time import require_aware_utc


class SearchAcquisitionRouteKind(StrEnum):
    PUBLIC_WEB = "public_web"
    SOURCE_REVIEW = "source_review"


@dataclass(frozen=True, slots=True)
class SearchAcquisitionRoute:
    candidate: SearchDiscoveryCandidate
    route_kind: SearchAcquisitionRouteKind
    requested_url: str
    public_web_target_id: str | None
    reason: str

    def __post_init__(self) -> None:
        reason = self.reason.strip()
        if not reason:
            raise ValueError("search acquisition route requires a reason")
        if self.route_kind is SearchAcquisitionRouteKind.PUBLIC_WEB:
            if not self.public_web_target_id:
                raise ValueError("public-web route requires a governed target id")
            if self.candidate.acquisition_state is not SearchAcquisitionState.ROUTED_PUBLIC_WEB:
                raise ValueError("public-web route requires routed candidate state")
        elif self.public_web_target_id is not None:
            raise ValueError("source-review route cannot carry a public-web target id")
        object.__setattr__(self, "reason", reason)

    @property
    def automatic(self) -> bool:
        return self.route_kind is SearchAcquisitionRouteKind.PUBLIC_WEB


def route_search_discovery_candidates(
    candidates: tuple[SearchDiscoveryCandidate, ...],
    targets: tuple[PublicWebTarget, ...],
    *,
    routed_at: datetime,
) -> tuple[SearchAcquisitionRoute, ...]:
    now = require_aware_utc(routed_at, field_name="routed_at")
    routes = tuple(_route_candidate(candidate, targets, now=now) for candidate in candidates)
    return tuple(sorted(routes, key=_route_sort_key))


def _route_candidate(
    candidate: SearchDiscoveryCandidate,
    targets: tuple[PublicWebTarget, ...],
    *,
    now: datetime,
) -> SearchAcquisitionRoute:
    matching = tuple(
        target
        for target in targets
        if target.organization_id == candidate.organization_id
        and target.executable_at(now)
        and same_origin(candidate.target_url, target.base_url)
        and target.crawl_scope.evaluate_target(
            candidate.target_url,
            depth=0,
            redirects=0,
            usage=CrawlUsage(),
        ).allowed
    )
    if len(matching) > 1:
        raise ValueError("search candidate matches multiple governed public-web targets")
    if matching:
        target = matching[0]
        routed = replace(
            candidate,
            acquisition_state=SearchAcquisitionState.ROUTED_PUBLIC_WEB,
        )
        return SearchAcquisitionRoute(
            candidate=routed,
            route_kind=SearchAcquisitionRouteKind.PUBLIC_WEB,
            requested_url=routed.target_url,
            public_web_target_id=target.id,
            reason="candidate URL is inside an executable governed public-web target",
        )
    review_candidate = replace(
        candidate,
        acquisition_state=SearchAcquisitionState.REQUIRES_SOURCE_REVIEW,
    )
    return SearchAcquisitionRoute(
        candidate=review_candidate,
        route_kind=SearchAcquisitionRouteKind.SOURCE_REVIEW,
        requested_url=review_candidate.target_url,
        public_web_target_id=None,
        reason=(
            "candidate URL is not inside an executable governed public-web target; "
            "provider/source review is required before retrieval"
        ),
    )


def _route_sort_key(route: SearchAcquisitionRoute) -> tuple[int, str]:
    priority = 0 if route.route_kind is SearchAcquisitionRouteKind.PUBLIC_WEB else 1
    return (priority, route.requested_url)
