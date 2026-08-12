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
from cip.modules.public_footprint.domain import PublicFootprintProjection, PublicResourceKind
from cip.modules.public_footprint.domain.scope import CrawlUsage
from cip.modules.raw_observations.domain.entities import RawObservation
from cip.modules.source_governance.infrastructure.registry import SourceRegistryEntry
from cip.shared.kernel.time import require_aware_utc


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
    initial_candidates, discovery_bytes, seen_feeds = discover_initial_candidates(
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
        authorize_public_web_url(entry, candidate.url, now=collected)
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
        next_pages[candidate.url] = PageCheckpoint(
            content_hash_sha256=mapped.content_hash_sha256,
            version_id=_checkpoint_version_id(previous, mapped, fetched),
            canonical_url=fetched.fetched_url,
            resource_kind=mapped.projection.resource.kind,
        )
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
        checkpoint=PublicWebCheckpoint(next_pages),
        not_modified=not observations,
    )


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
