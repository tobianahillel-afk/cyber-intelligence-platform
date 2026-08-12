from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from cip.adapters.sources.public_web.client import (
    PublicWebClient,
    PublicWebFetchResult,
    RobotsRules,
)
from cip.adapters.sources.public_web.feed_parsing import parse_public_feed
from cip.adapters.sources.public_web.mapper import (
    MappedPublicPage,
    PreviousPageState,
    map_public_page,
)
from cip.adapters.sources.public_web.parsing import parse_sitemap
from cip.adapters.sources.public_web.registry import PublicWebTarget
from cip.adapters.sources.public_web.security_txt import parse_security_txt
from cip.adapters.sources.public_web.security_txt_mapper import map_security_txt
from cip.modules.public_footprint.domain import (
    DiscoveryMethod,
    PublicFootprintProjection,
    PublicResourceKind,
)
from cip.modules.public_footprint.domain.scope import CrawlUsage
from cip.modules.raw_observations.domain.entities import RawObservation
from cip.modules.source_governance.domain.models import (
    CollectionRequest,
    DataCategory,
    SourceRuntimeState,
)
from cip.modules.source_governance.infrastructure.registry import SourceRegistryEntry
from cip.shared.kernel.time import require_aware_utc


class PublicWebCollectionDeniedError(RuntimeError):
    """Source or target governance denied public-web collection."""


@dataclass(frozen=True, slots=True)
class PageCheckpoint:
    content_hash_sha256: str
    version_id: UUID
    canonical_url: str
    resource_kind: PublicResourceKind = PublicResourceKind.WEB_PAGE


@dataclass(frozen=True, slots=True)
class PublicWebCheckpoint:
    pages: dict[str, PageCheckpoint]


@dataclass(frozen=True, slots=True)
class PublicWebCollectionBatch:
    observations: tuple[RawObservation, ...]
    projections: tuple[PublicFootprintProjection, ...]
    checkpoint: PublicWebCheckpoint
    not_modified: bool


@dataclass(frozen=True, slots=True)
class PublicWebDiscoveryCandidate:
    url: str
    discovery_method: DiscoveryMethod
    source_locator: str | None = None
    security_txt: bool = False


def collect_public_web_target(
    client: PublicWebClient,
    entry: SourceRegistryEntry,
    target: PublicWebTarget,
    *,
    collection_job_id: UUID,
    collected_at: datetime,
    retention_until: datetime,
    checkpoint: PublicWebCheckpoint | None = None,
) -> PublicWebCollectionBatch:
    collected = require_aware_utc(collected_at, field_name="collected_at")
    if entry.policy.id != target.source_id:
        raise ValueError("public web source policy and target source_id must match")
    if not target.executable_at(collected):
        raise PublicWebCollectionDeniedError("target_authorization_inactive")
    _authorize(entry, target.robots_url, now=collected)
    robots = client.fetch_robots(target)
    candidates, discovery_bytes = _discover_candidates(
        client,
        entry,
        target,
        robots,
        now=collected,
        initial_bytes=robots.bytes_fetched,
    )
    usage = CrawlUsage(bytes_fetched=discovery_bytes)
    previous_pages = checkpoint.pages if checkpoint is not None else {}
    next_pages = dict(previous_pages)
    observations: list[RawObservation] = []
    projections: list[PublicFootprintProjection] = []
    for candidate in candidates:
        _authorize(entry, candidate.url, now=collected)
        fetched = client.fetch_page(target, candidate.url, robots, usage=usage)
        usage = CrawlUsage(
            pages_fetched=usage.pages_fetched + 1,
            bytes_fetched=usage.bytes_fetched + len(fetched.body),
        )
        if candidate.security_txt and fetched.status_code in {404, 410}:
            continue
        previous = previous_pages.get(candidate.url)
        mapped = _map_candidate(
            target,
            candidate,
            fetched,
            collection_job_id=collection_job_id,
            collected_at=collected,
            retention_until=retention_until,
            previous=previous,
        )
        if mapped.observation is not None:
            observations.append(mapped.observation)
        projections.append(mapped.projection)
        checkpoint_version_id = _checkpoint_version_id(previous, mapped, fetched)
        next_pages[candidate.url] = PageCheckpoint(
            content_hash_sha256=mapped.content_hash_sha256,
            version_id=checkpoint_version_id,
            canonical_url=fetched.fetched_url,
            resource_kind=mapped.projection.resource.kind,
        )
    return PublicWebCollectionBatch(
        observations=tuple(observations),
        projections=tuple(projections),
        checkpoint=PublicWebCheckpoint(next_pages),
        not_modified=not observations,
    )


def _discover_candidates(
    client: PublicWebClient,
    entry: SourceRegistryEntry,
    target: PublicWebTarget,
    robots: RobotsRules,
    *,
    now: datetime,
    initial_bytes: int,
) -> tuple[tuple[PublicWebDiscoveryCandidate, ...], int]:
    candidates: list[PublicWebDiscoveryCandidate] = []
    seen: set[str] = set()
    total_bytes = _checked_total_bytes(target, initial_bytes)
    for seed_url in target.seed_urls:
        _append_candidate(
            candidates,
            seen,
            PublicWebDiscoveryCandidate(
                url=seed_url,
                discovery_method=DiscoveryMethod.DIRECT,
            ),
            max_pages=target.max_pages,
        )
    if target.discover_security_txt:
        _append_candidate(
            candidates,
            seen,
            PublicWebDiscoveryCandidate(
                url=target.security_txt_url,
                discovery_method=DiscoveryMethod.DIRECT,
                security_txt=True,
            ),
            max_pages=target.max_pages,
        )
    for sitemap_url in target.sitemap_urls:
        if len(candidates) >= target.max_pages:
            break
        _authorize(entry, sitemap_url, now=now)
        sitemap = client.fetch_sitemap(target, sitemap_url, robots)
        total_bytes = _checked_total_bytes(target, total_bytes + len(sitemap.body))
        remaining = target.max_pages - len(candidates)
        for sitemap_entry in parse_sitemap(sitemap.body, target, max_entries=remaining):
            _append_candidate(
                candidates,
                seen,
                PublicWebDiscoveryCandidate(
                    url=sitemap_entry.url,
                    discovery_method=DiscoveryMethod.SITEMAP,
                ),
                max_pages=target.max_pages,
            )
    for feed_url in target.feed_urls:
        if len(candidates) >= target.max_pages:
            break
        _authorize(entry, feed_url, now=now)
        feed = client.fetch_feed(target, feed_url, robots)
        total_bytes = _checked_total_bytes(target, total_bytes + len(feed.body))
        remaining = target.max_pages - len(candidates)
        for feed_entry in parse_public_feed(feed.body, target, max_entries=remaining):
            _append_candidate(
                candidates,
                seen,
                PublicWebDiscoveryCandidate(
                    url=feed_entry.url,
                    discovery_method=DiscoveryMethod.FEED,
                    source_locator=feed_url,
                ),
                max_pages=target.max_pages,
            )
    return tuple(candidates), total_bytes


def _append_candidate(
    candidates: list[PublicWebDiscoveryCandidate],
    seen: set[str],
    candidate: PublicWebDiscoveryCandidate,
    *,
    max_pages: int,
) -> None:
    if len(candidates) >= max_pages or candidate.url in seen:
        return
    seen.add(candidate.url)
    candidates.append(candidate)


def _map_candidate(
    target: PublicWebTarget,
    candidate: PublicWebDiscoveryCandidate,
    fetched: PublicWebFetchResult,
    *,
    collection_job_id: UUID,
    collected_at: datetime,
    retention_until: datetime,
    previous: PageCheckpoint | None,
) -> MappedPublicPage:
    previous_state = _previous_state(previous)
    if candidate.security_txt:
        if fetched.mime_type != "text/plain":
            raise PublicWebCollectionDeniedError(
                "security.txt must be served as text/plain"
            )
        document = parse_security_txt(fetched.body, target)
        return map_security_txt(
            target,
            fetched,
            document,
            collection_job_id=collection_job_id,
            collected_at=collected_at,
            retention_until=retention_until,
            previous=previous_state,
        )
    return map_public_page(
        target,
        fetched,
        collection_job_id=collection_job_id,
        collected_at=collected_at,
        retention_until=retention_until,
        previous=previous_state,
        discovery_method=candidate.discovery_method,
        discovery_source_url=candidate.source_locator,
        allow_claims=True,
    )


def _previous_state(previous: PageCheckpoint | None) -> PreviousPageState | None:
    if previous is None:
        return None
    return PreviousPageState(
        content_hash_sha256=previous.content_hash_sha256,
        version_id=previous.version_id,
        canonical_url=previous.canonical_url,
        resource_kind=previous.resource_kind,
    )


def _checkpoint_version_id(
    previous: PageCheckpoint | None,
    mapped: MappedPublicPage,
    fetched: PublicWebFetchResult,
) -> UUID:
    unchanged = bool(
        previous is not None
        and previous.content_hash_sha256 == mapped.content_hash_sha256
        and previous.canonical_url == fetched.fetched_url
    )
    if unchanged and previous is not None:
        return previous.version_id
    return mapped.projection.version.id


def _checked_total_bytes(target: PublicWebTarget, value: int) -> int:
    if value > target.max_total_bytes:
        raise PublicWebCollectionDeniedError("total_byte_budget_exceeded")
    return value


def _authorize(entry: SourceRegistryEntry, target_url: str, *, now: datetime) -> None:
    decision = entry.policy.evaluate(
        CollectionRequest(
            data_category=DataCategory.OFFICIAL_DOCUMENT_DISCOVERY,
            target_url=target_url,
            purpose="corporate-public-footprint",
            automated=True,
            store_raw_content=False,
            human_review_completed=False,
        ),
        entry.authorization,
        SourceRuntimeState(remaining_requests=1),
        now=now,
    )
    if not decision.allowed:
        raise PublicWebCollectionDeniedError(decision.reason.value)
