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
from cip.adapters.sources.public_web.link_discovery import (
    extract_public_feed_links,
    extract_public_html_links,
)
from cip.adapters.sources.public_web.mapper import (
    MappedPublicPage,
    PreviousPageState,
    map_public_page,
)
from cip.adapters.sources.public_web.parsing import parse_sitemap_document
from cip.adapters.sources.public_web.registry import PublicWebTarget
from cip.adapters.sources.public_web.security_txt import parse_security_txt
from cip.adapters.sources.public_web.security_txt_mapper import map_security_txt
from cip.modules.public_footprint.domain import (
    DiscoveryMethod,
    PublicFootprintProjection,
    PublicResourceKind,
)
from cip.modules.public_footprint.domain.scope import CrawlUsage
from cip.modules.public_footprint.domain.url_identity import same_origin
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
    depth: int = 0


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
    initial_candidates, discovery_bytes, seen_feeds = _discover_candidates(
        client,
        entry,
        target,
        robots,
        now=collected,
        initial_bytes=robots.bytes_fetched,
    )
    candidates = list(initial_candidates)
    seen = {candidate.url for candidate in candidates}
    usage = CrawlUsage(bytes_fetched=discovery_bytes)
    previous_pages = checkpoint.pages if checkpoint is not None else {}
    next_pages = dict(previous_pages)
    observations: list[RawObservation] = []
    projections: list[PublicFootprintProjection] = []
    index = 0
    while index < len(candidates):
        candidate = candidates[index]
        index += 1
        if usage.pages_fetched >= target.max_pages:
            break
        _authorize(entry, candidate.url, now=collected)
        fetched = client.fetch_page(
            target,
            candidate.url,
            robots,
            usage=usage,
            depth=candidate.depth,
        )
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
        usage = _discover_html_feeds(
            client,
            entry,
            target,
            robots,
            fetched,
            candidates,
            seen,
            seen_feeds,
            usage=usage,
            now=collected,
        )
        _discover_recursive_links(
            target,
            candidate,
            fetched,
            candidates,
            seen,
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
) -> tuple[tuple[PublicWebDiscoveryCandidate, ...], int, set[str]]:
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
    total_bytes = _discover_sitemap_candidates(
        client,
        entry,
        target,
        robots,
        candidates,
        seen,
        now=now,
        total_bytes=total_bytes,
    )
    seen_feeds = set(target.feed_urls)
    for feed_url in target.feed_urls:
        if len(candidates) >= target.max_pages:
            break
        total_bytes = _consume_feed(
            client,
            entry,
            target,
            robots,
            feed_url,
            candidates,
            seen,
            now=now,
            total_bytes=total_bytes,
            discovered=False,
        )
    return tuple(candidates), total_bytes, seen_feeds


def _discover_sitemap_candidates(
    client: PublicWebClient,
    entry: SourceRegistryEntry,
    target: PublicWebTarget,
    robots: RobotsRules,
    candidates: list[PublicWebDiscoveryCandidate],
    seen: set[str],
    *,
    now: datetime,
    total_bytes: int,
) -> int:
    queue: list[tuple[str, int, bool]] = [
        (url, 0, False) for url in target.sitemap_urls
    ]
    if target.discover_sitemaps:
        queue.extend((url, 0, True) for url in robots.sitemap_urls)
    seen_sitemaps: set[str] = set()
    index = 0
    while index < len(queue) and len(seen_sitemaps) < target.max_sitemaps:
        sitemap_url, depth, discovered = queue[index]
        index += 1
        if sitemap_url in seen_sitemaps:
            continue
        seen_sitemaps.add(sitemap_url)
        _authorize(entry, sitemap_url, now=now)
        sitemap = client.fetch_sitemap(
            target,
            sitemap_url,
            robots,
            discovered=discovered,
        )
        total_bytes = _checked_total_bytes(target, total_bytes + len(sitemap.body))
        remaining_pages = max(1, target.max_pages - len(candidates))
        remaining_sitemaps = max(1, target.max_sitemaps - len(seen_sitemaps))
        document = parse_sitemap_document(
            sitemap.body,
            target,
            max_entries=remaining_pages,
            max_child_sitemaps=remaining_sitemaps,
        )
        for sitemap_entry in document.entries:
            _append_candidate(
                candidates,
                seen,
                PublicWebDiscoveryCandidate(
                    url=sitemap_entry.url,
                    discovery_method=DiscoveryMethod.SITEMAP,
                    source_locator=sitemap_url,
                ),
                max_pages=target.max_pages,
            )
        if depth >= target.max_sitemap_depth:
            continue
        for child_url in document.child_sitemaps:
            if child_url in seen_sitemaps or len(queue) >= target.max_sitemaps:
                continue
            queue.append((child_url, depth + 1, True))
    return total_bytes


def _discover_html_feeds(
    client: PublicWebClient,
    entry: SourceRegistryEntry,
    target: PublicWebTarget,
    robots: RobotsRules,
    fetched: PublicWebFetchResult,
    candidates: list[PublicWebDiscoveryCandidate],
    seen: set[str],
    seen_feeds: set[str],
    *,
    usage: CrawlUsage,
    now: datetime,
) -> CrawlUsage:
    remaining_feeds = target.max_feeds - len(seen_feeds)
    if (
        not target.discover_feeds
        or fetched.mime_type != "text/html"
        or remaining_feeds <= 0
        or len(candidates) >= target.max_pages
    ):
        return usage
    feed_urls = extract_public_feed_links(
        fetched.body,
        base_url=fetched.fetched_url,
        max_feeds=remaining_feeds,
    )
    total_bytes = usage.bytes_fetched
    for feed_url in feed_urls:
        if feed_url in seen_feeds or not same_origin(target.base_url, feed_url):
            continue
        seen_feeds.add(feed_url)
        total_bytes = _consume_feed(
            client,
            entry,
            target,
            robots,
            feed_url,
            candidates,
            seen,
            now=now,
            total_bytes=total_bytes,
            discovered=True,
        )
        if len(seen_feeds) >= target.max_feeds or len(candidates) >= target.max_pages:
            break
    return CrawlUsage(pages_fetched=usage.pages_fetched, bytes_fetched=total_bytes)


def _consume_feed(
    client: PublicWebClient,
    entry: SourceRegistryEntry,
    target: PublicWebTarget,
    robots: RobotsRules,
    feed_url: str,
    candidates: list[PublicWebDiscoveryCandidate],
    seen: set[str],
    *,
    now: datetime,
    total_bytes: int,
    discovered: bool,
) -> int:
    _authorize(entry, feed_url, now=now)
    feed = client.fetch_feed(target, feed_url, robots, discovered=discovered)
    total_bytes = _checked_total_bytes(target, total_bytes + len(feed.body))
    remaining = target.max_pages - len(candidates)
    if remaining <= 0:
        return total_bytes
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
    return total_bytes


def _discover_recursive_links(
    target: PublicWebTarget,
    candidate: PublicWebDiscoveryCandidate,
    fetched: PublicWebFetchResult,
    candidates: list[PublicWebDiscoveryCandidate],
    seen: set[str],
) -> None:
    child_depth = candidate.depth + 1
    remaining = target.max_pages - len(candidates)
    if (
        fetched.mime_type != "text/html"
        or child_depth > target.max_link_depth
        or remaining <= 0
    ):
        return
    links = extract_public_html_links(
        fetched.body,
        base_url=fetched.fetched_url,
        max_links=remaining,
    )
    for link in links:
        if not same_origin(target.base_url, link):
            continue
        decision = target.crawl_scope.evaluate_target(
            link,
            depth=child_depth,
            redirects=0,
            usage=CrawlUsage(),
        )
        if not decision.allowed:
            continue
        _append_candidate(
            candidates,
            seen,
            PublicWebDiscoveryCandidate(
                url=link,
                discovery_method=DiscoveryMethod.LINK,
                source_locator=fetched.fetched_url,
                depth=child_depth,
            ),
            max_pages=target.max_pages,
        )


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
            raise PublicWebCollectionDeniedError("security.txt must be served as text/plain")
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
