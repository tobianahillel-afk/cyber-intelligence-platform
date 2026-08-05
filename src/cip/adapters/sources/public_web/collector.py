from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from cip.adapters.sources.public_web.client import PublicWebClient
from cip.adapters.sources.public_web.mapper import (
    PreviousPageState,
    map_public_page,
)
from cip.adapters.sources.public_web.parsing import parse_sitemap
from cip.adapters.sources.public_web.registry import PublicWebTarget
from cip.modules.public_footprint.domain import PublicFootprintProjection
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
    if entry.policy.id != target.id:
        raise ValueError("public web source policy and target id must match")
    if not target.executable_at(collected):
        raise PublicWebCollectionDeniedError("target_authorization_inactive")
    _authorize(entry, target.robots_url, now=collected)
    robots = client.fetch_robots(target)
    total_bytes = robots.bytes_fetched
    if total_bytes > target.max_total_bytes:
        raise PublicWebCollectionDeniedError("total_byte_budget_exceeded")
    discovered_urls: list[str] = []
    seen_urls: set[str] = set()
    for sitemap_url in target.sitemap_urls:
        _authorize(entry, sitemap_url, now=collected)
        sitemap = client.fetch_sitemap(target, sitemap_url, robots)
        total_bytes += len(sitemap.body)
        if total_bytes > target.max_total_bytes:
            raise PublicWebCollectionDeniedError("total_byte_budget_exceeded")
        remaining = target.max_pages - len(discovered_urls)
        if remaining <= 0:
            break
        for sitemap_entry in parse_sitemap(
            sitemap.body,
            target,
            max_entries=remaining,
        ):
            if sitemap_entry.url in seen_urls:
                continue
            seen_urls.add(sitemap_entry.url)
            discovered_urls.append(sitemap_entry.url)
    usage = CrawlUsage(bytes_fetched=total_bytes)
    previous_pages = checkpoint.pages if checkpoint is not None else {}
    next_pages = dict(previous_pages)
    observations: list[RawObservation] = []
    projections: list[PublicFootprintProjection] = []
    for url in discovered_urls:
        _authorize(entry, url, now=collected)
        fetched = client.fetch_page(target, url, robots, usage=usage)
        previous = previous_pages.get(url)
        mapped = map_public_page(
            target,
            fetched,
            collection_job_id=collection_job_id,
            collected_at=collected,
            retention_until=retention_until,
            previous=(
                PreviousPageState(
                    content_hash_sha256=previous.content_hash_sha256,
                    version_id=previous.version_id,
                    canonical_url=previous.canonical_url,
                )
                if previous is not None
                else None
            ),
        )
        if mapped.observation is not None:
            observations.append(mapped.observation)
        projections.append(mapped.projection)
        unchanged = bool(
            previous is not None
            and previous.content_hash_sha256 == mapped.content_hash_sha256
            and previous.canonical_url == fetched.fetched_url
        )
        if unchanged and previous is not None:
            checkpoint_version_id = previous.version_id
        else:
            checkpoint_version_id = mapped.projection.version.id
        next_pages[url] = PageCheckpoint(
            content_hash_sha256=mapped.content_hash_sha256,
            version_id=checkpoint_version_id,
            canonical_url=fetched.fetched_url,
        )
        usage = CrawlUsage(
            pages_fetched=usage.pages_fetched + 1,
            bytes_fetched=usage.bytes_fetched + len(fetched.body),
        )
    return PublicWebCollectionBatch(
        observations=tuple(observations),
        projections=tuple(projections),
        checkpoint=PublicWebCheckpoint(next_pages),
        not_modified=not observations,
    )


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
