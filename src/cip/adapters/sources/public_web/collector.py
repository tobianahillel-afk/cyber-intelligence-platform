from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from cip.adapters.sources.public_web.client import PublicWebClient, PublicWebFetchResult
from cip.adapters.sources.public_web.collection_policy import (
    PublicWebCollectionDeniedError,
    authorize_public_web_url,
)
from cip.adapters.sources.public_web.discovery import (
    PublicWebDiscoveryCandidate,
    append_candidate,
    discover_html_feeds,
    discover_initial_candidates,
    discover_recursive_links,
)
from cip.adapters.sources.public_web.mapper import (
    MappedPublicPage,
    PreviousPageState,
    map_public_page,
)
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
from cip.modules.source_governance.infrastructure.registry import SourceRegistryEntry
from cip.shared.kernel.time import require_aware_utc

_NOT_MODIFIED_STATUS = 304
_TOMBSTONE_MIME_TYPE = "application/x-public-resource-tombstone"
_MAX_VALIDATOR_LENGTH = 2_000
_CURRENT_EXTRACTION_PROFILE = 2
_LEGACY_EXTRACTION_PROFILE = 1


@dataclass(frozen=True, slots=True)
class PageCheckpoint:
    content_hash_sha256: str
    version_id: UUID
    canonical_url: str
    resource_kind: PublicResourceKind = PublicResourceKind.WEB_PAGE
    etag: str | None = None
    last_modified: str | None = None
    mime_type: str | None = None
    byte_size: int | None = None
    discovery_method: DiscoveryMethod | None = None
    source_locator: str | None = None
    depth: int | None = None
    security_txt: bool = False
    extraction_profile: int = _LEGACY_EXTRACTION_PROFILE


@dataclass(frozen=True, slots=True)
class PublicWebCheckpoint:
    pages: dict[str, PageCheckpoint]
    feed_urls: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class PublicWebCollectionBatch:
    observations: tuple[RawObservation, ...]
    projections: tuple[PublicFootprintProjection, ...]
    checkpoint: PublicWebCheckpoint
    not_modified: bool


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
    authorize_public_web_url(entry, target.robots_url, now=collected)
    robots = client.fetch_robots(target)
    previous_pages = checkpoint.pages if checkpoint is not None else {}
    known_feed_urls = checkpoint.feed_urls if checkpoint is not None else ()
    initial_candidates, discovery_bytes, seen_feeds = discover_initial_candidates(
        client,
        entry,
        target,
        robots,
        now=collected,
        initial_bytes=robots.bytes_fetched,
        known_feed_urls=known_feed_urls,
    )
    candidates = list(initial_candidates)
    seen = {candidate.url for candidate in candidates}
    _restore_checkpoint_candidates(target, previous_pages, candidates, seen)
    usage = CrawlUsage(bytes_fetched=discovery_bytes)
    next_pages = dict(previous_pages)
    observations: list[RawObservation] = []
    projections: list[PublicFootprintProjection] = []
    index = 0
    while index < len(candidates):
        candidate = candidates[index]
        index += 1
        if usage.pages_fetched >= target.max_pages:
            break
        authorize_public_web_url(entry, candidate.url, now=collected)
        previous = previous_pages.get(candidate.url)
        etag, last_modified = _conditional_validators(previous, candidate)
        fetched = client.fetch_page(
            target,
            candidate.url,
            robots,
            usage=usage,
            depth=candidate.depth,
            etag=etag,
            last_modified=last_modified,
        )
        usage = CrawlUsage(
            pages_fetched=usage.pages_fetched + 1,
            bytes_fetched=usage.bytes_fetched + len(fetched.body),
        )
        if candidate.security_txt and fetched.status_code in {404, 410}:
            continue
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
        next_pages[candidate.url] = _next_page_checkpoint(
            candidate,
            previous,
            mapped,
            fetched,
        )
        if fetched.status_code == _NOT_MODIFIED_STATUS:
            continue
        usage = discover_html_feeds(
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
        discover_recursive_links(target, candidate, fetched, candidates, seen)
    return PublicWebCollectionBatch(
        observations=tuple(observations),
        projections=tuple(projections),
        checkpoint=PublicWebCheckpoint(
            pages=next_pages,
            feed_urls=tuple(sorted(seen_feeds)),
        ),
        not_modified=not observations,
    )


def _restore_checkpoint_candidates(
    target: PublicWebTarget,
    previous_pages: dict[str, PageCheckpoint],
    candidates: list[PublicWebDiscoveryCandidate],
    seen: set[str],
) -> None:
    resumable = sorted(
        previous_pages.items(),
        key=lambda item: (
            item[1].depth if item[1].depth is not None else 21,
            item[0],
        ),
    )
    for url, state in resumable:
        if state.discovery_method is None or state.depth is None:
            continue
        if state.security_txt and not target.discover_security_txt:
            continue
        decision = target.crawl_scope.evaluate_target(
            url,
            depth=state.depth,
            redirects=0,
            usage=CrawlUsage(),
        )
        if not decision.allowed:
            continue
        append_candidate(
            candidates,
            seen,
            PublicWebDiscoveryCandidate(
                url=url,
                discovery_method=state.discovery_method,
                source_locator=state.source_locator,
                security_txt=state.security_txt,
                depth=state.depth,
            ),
            max_pages=target.max_pages,
        )


def _conditional_validators(
    previous: PageCheckpoint | None,
    candidate: PublicWebDiscoveryCandidate,
) -> tuple[str | None, str | None]:
    if (
        previous is None
        or candidate.security_txt
        or previous.canonical_url != candidate.url
        or previous.mime_type in {None, _TOMBSTONE_MIME_TYPE}
        or previous.byte_size is None
        or _requires_html_reprocessing(previous)
    ):
        return None, None
    return previous.etag, previous.last_modified


def _requires_html_reprocessing(previous: PageCheckpoint) -> bool:
    return bool(
        previous.mime_type == "text/html"
        and previous.extraction_profile != _CURRENT_EXTRACTION_PROFILE
    )


def _next_page_checkpoint(
    candidate: PublicWebDiscoveryCandidate,
    previous: PageCheckpoint | None,
    mapped: MappedPublicPage,
    fetched: PublicWebFetchResult,
) -> PageCheckpoint:
    not_modified = fetched.status_code == _NOT_MODIFIED_STATUS
    mime_type = previous.mime_type if not_modified and previous is not None else fetched.mime_type
    byte_size = previous.byte_size if not_modified and previous is not None else len(fetched.body)
    return PageCheckpoint(
        content_hash_sha256=mapped.content_hash_sha256,
        version_id=_checkpoint_version_id(previous, mapped, fetched),
        canonical_url=fetched.fetched_url,
        resource_kind=mapped.projection.resource.kind,
        etag=_safe_validator(fetched.etag),
        last_modified=_safe_validator(fetched.last_modified),
        mime_type=mime_type,
        byte_size=byte_size,
        discovery_method=candidate.discovery_method,
        source_locator=candidate.source_locator,
        depth=candidate.depth,
        security_txt=candidate.security_txt,
        extraction_profile=_CURRENT_EXTRACTION_PROFILE,
    )


def _safe_validator(value: str | None) -> str | None:
    if value is None or len(value) > _MAX_VALIDATOR_LENGTH or "\r" in value or "\n" in value:
        return None
    return value


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
        mime_type=previous.mime_type,
        byte_size=previous.byte_size,
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
