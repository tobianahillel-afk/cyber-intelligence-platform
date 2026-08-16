from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from cip.adapters.sources.public_web.client import (
    PublicWebClient,
    PublicWebFetchResult,
    RobotsRules,
)
from cip.adapters.sources.public_web.crawl_runtime import (
    CrawlDeadline,
    CrawlReservation,
    CrawlTelemetry,
)
from cip.adapters.sources.public_web.discovery import (
    PublicWebDiscoveryCandidate,
    append_candidate,
)
from cip.adapters.sources.public_web.registry import PublicWebTarget
from cip.modules.public_footprint.domain import (
    DiscoveryMethod,
    PublicFootprintProjection,
    PublicResourceKind,
)
from cip.modules.public_footprint.domain.scope import CrawlUsage
from cip.modules.raw_observations.domain.entities import RawObservation
from cip.modules.source_governance.infrastructure.registry import SourceRegistryEntry

TOMBSTONE_MIME_TYPE = "application/x-public-resource-tombstone"
CURRENT_EXTRACTION_PROFILE = 2
LEGACY_EXTRACTION_PROFILE = 1
MAX_VALIDATOR_LENGTH = 2_000


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
    extraction_profile: int = LEGACY_EXTRACTION_PROFILE


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
    telemetry: CrawlTelemetry = field(default_factory=CrawlTelemetry)


@dataclass(frozen=True, slots=True)
class PageWork:
    candidate: PublicWebDiscoveryCandidate
    previous: PageCheckpoint | None
    reservation: CrawlReservation
    usage: CrawlUsage
    etag: str | None
    last_modified: str | None


@dataclass(frozen=True, slots=True)
class PageOutcome:
    work: PageWork
    fetched: PublicWebFetchResult | None = None
    error: Exception | None = None


@dataclass(slots=True)
class TelemetryState:
    attempted_pages: int = 0
    fetched_pages: int = 0
    not_modified_pages: int = 0
    tombstoned_pages: int = 0
    failed_pages: int = 0
    bytes_received: int = 0
    bytes_accepted: int = 0
    links_discovered: int = 0
    links_admitted: int = 0
    links_denied: int = 0
    policy_denials: int = 0
    redirects: int = 0
    deadline_exceeded: bool = False
    cancelled: bool = False
    max_concurrency_used: int = 0

    def record_fetch(self, fetched: PublicWebFetchResult) -> None:
        self.fetched_pages += 1
        self.bytes_received += fetched.bytes_received
        self.bytes_accepted += len(fetched.body)
        self.redirects += fetched.redirects
        if fetched.status_code == 304:
            self.not_modified_pages += 1
        if fetched.status_code in {404, 410}:
            self.tombstoned_pages += 1

    def freeze(
        self,
        *,
        client: PublicWebClient,
        deadline: CrawlDeadline,
        configured_concurrency: int,
        effective_concurrency: int,
    ) -> CrawlTelemetry:
        fallback_urls = getattr(client, "fallback_urls", ())
        fallback_count = len(fallback_urls) if isinstance(fallback_urls, tuple) else 0
        return CrawlTelemetry(
            attempted_pages=self.attempted_pages,
            fetched_pages=self.fetched_pages,
            not_modified_pages=self.not_modified_pages,
            tombstoned_pages=self.tombstoned_pages,
            failed_pages=self.failed_pages,
            bytes_received=self.bytes_received,
            bytes_accepted=self.bytes_accepted,
            links_discovered=self.links_discovered,
            links_admitted=self.links_admitted,
            links_denied=self.links_denied,
            browser_fallback_count=fallback_count,
            policy_denials=self.policy_denials,
            redirects=self.redirects,
            elapsed_seconds=deadline.elapsed_seconds,
            deadline_exceeded=self.deadline_exceeded,
            cancelled=self.cancelled,
            configured_concurrency=configured_concurrency,
            effective_concurrency=effective_concurrency,
            max_concurrency_used=self.max_concurrency_used,
        )


@dataclass(slots=True)
class CollectionContext:
    client: PublicWebClient
    entry: SourceRegistryEntry
    target: PublicWebTarget
    robots: RobotsRules
    collection_job_id: UUID
    collected_at: datetime
    retention_until: datetime
    deadline: CrawlDeadline
    adapter_id: str
    candidates: list[PublicWebDiscoveryCandidate]
    seen: set[str]
    seen_feeds: set[str]
    previous_pages: dict[str, PageCheckpoint]
    next_pages: dict[str, PageCheckpoint]
    observations: list[RawObservation]
    projections: list[PublicFootprintProjection]
    metrics: TelemetryState


def restore_checkpoint_candidates(
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


def conditional_validators(
    previous: PageCheckpoint | None,
    candidate: PublicWebDiscoveryCandidate,
) -> tuple[str | None, str | None]:
    if (
        previous is None
        or candidate.security_txt
        or previous.canonical_url != candidate.url
        or previous.mime_type in {None, TOMBSTONE_MIME_TYPE}
        or previous.byte_size is None
        or requires_html_reprocessing(previous)
    ):
        return None, None
    return previous.etag, previous.last_modified


def requires_html_reprocessing(previous: PageCheckpoint) -> bool:
    return bool(
        previous.mime_type == "text/html"
        and previous.extraction_profile != CURRENT_EXTRACTION_PROFILE
    )


def safe_validator(value: str | None) -> str | None:
    if value is None or len(value) > MAX_VALIDATOR_LENGTH or "\r" in value or "\n" in value:
        return None
    return value


def reserved_usage(target: PublicWebTarget, reservation: CrawlReservation) -> CrawlUsage:
    return CrawlUsage(
        pages_fetched=target.max_pages - 1,
        bytes_fetched=target.max_total_bytes - reservation.byte_allowance,
    )


def mark_deadline(context: CollectionContext) -> None:
    context.metrics.deadline_exceeded = True
    context.metrics.cancelled = True
