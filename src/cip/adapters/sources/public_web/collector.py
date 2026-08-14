from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from cip.adapters.sources.public_web.client import (
    PublicWebClient,
    PublicWebDeadlineExceededError,
    PublicWebFetchResult,
    PublicWebPolicyDeniedError,
    RobotsRules,
)
from cip.adapters.sources.public_web.collection_policy import (
    PublicWebCollectionDeniedError,
    authorize_public_web_url,
)
from cip.adapters.sources.public_web.crawl_runtime import (
    CrawlBudgetCoordinator,
    CrawlDeadline,
    CrawlReservation,
    CrawlTelemetry,
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
_TOMBSTONE_STATUSES = {404, 410}
_TOMBSTONE_MIME_TYPE = "application/x-public-resource-tombstone"
_MAX_VALIDATOR_LENGTH = 2_000
_CURRENT_EXTRACTION_PROFILE = 2
_LEGACY_EXTRACTION_PROFILE = 1
_DEFAULT_ADAPTER_ID = "public-web-sitemap"


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
    telemetry: CrawlTelemetry = field(default_factory=CrawlTelemetry)


@dataclass(frozen=True, slots=True)
class _PageWork:
    candidate: PublicWebDiscoveryCandidate
    previous: PageCheckpoint | None
    reservation: CrawlReservation
    usage: CrawlUsage
    etag: str | None
    last_modified: str | None


@dataclass(frozen=True, slots=True)
class _PageOutcome:
    work: _PageWork
    fetched: PublicWebFetchResult | None = None
    error: Exception | None = None


@dataclass(slots=True)
class _TelemetryState:
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
        if fetched.status_code == _NOT_MODIFIED_STATUS:
            self.not_modified_pages += 1
        if fetched.status_code in _TOMBSTONE_STATUSES:
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
class _CollectionContext:
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
    metrics: _TelemetryState


def collect_public_web_target(
    client: PublicWebClient,
    entry: SourceRegistryEntry,
    target: PublicWebTarget,
    *,
    collection_job_id: UUID,
    collected_at: datetime,
    retention_until: datetime,
    checkpoint: PublicWebCheckpoint | None = None,
    adapter_id: str = _DEFAULT_ADAPTER_ID,
) -> PublicWebCollectionBatch:
    context, discovery_bytes = _prepare_context(
        client,
        entry,
        target,
        collection_job_id=collection_job_id,
        collected_at=collected_at,
        retention_until=retention_until,
        checkpoint=checkpoint,
        adapter_id=adapter_id,
    )
    effective = target.max_crawl_concurrency if client.supports_concurrent_fetches else 1
    if effective == 1:
        _collect_serial_pages(context, discovery_bytes)
    else:
        _collect_concurrent_pages(context, discovery_bytes, effective)
    return PublicWebCollectionBatch(
        observations=tuple(context.observations),
        projections=tuple(context.projections),
        checkpoint=PublicWebCheckpoint(
            pages=context.next_pages,
            feed_urls=tuple(sorted(context.seen_feeds)),
        ),
        not_modified=not context.observations,
        telemetry=context.metrics.freeze(
            client=client,
            deadline=context.deadline,
            configured_concurrency=target.max_crawl_concurrency,
            effective_concurrency=effective,
        ),
    )


def _prepare_context(
    client: PublicWebClient,
    entry: SourceRegistryEntry,
    target: PublicWebTarget,
    *,
    collection_job_id: UUID,
    collected_at: datetime,
    retention_until: datetime,
    checkpoint: PublicWebCheckpoint | None,
    adapter_id: str,
) -> tuple[_CollectionContext, int]:
    collected = require_aware_utc(collected_at, field_name="collected_at")
    if entry.policy.id != target.source_id:
        raise ValueError("public web source policy and target source_id must match")
    if not target.executable_at(collected):
        raise PublicWebCollectionDeniedError("target_authorization_inactive")
    deadline = client.deadline or CrawlDeadline(target.crawl_deadline_seconds)
    client.bind_deadline(deadline)
    authorize_public_web_url(entry, target.robots_url, now=collected)
    robots = client.fetch_robots(target)
    previous_pages = checkpoint.pages if checkpoint is not None else {}
    known_feeds = checkpoint.feed_urls if checkpoint is not None else ()
    initial, discovery_bytes, seen_feeds = discover_initial_candidates(
        client,
        entry,
        target,
        robots,
        now=collected,
        initial_bytes=robots.bytes_fetched,
        known_feed_urls=known_feeds,
    )
    candidates = list(initial)
    seen = {candidate.url for candidate in candidates}
    _restore_checkpoint_candidates(target, previous_pages, candidates, seen)
    context = _CollectionContext(
        client=client,
        entry=entry,
        target=target,
        robots=robots,
        collection_job_id=collection_job_id,
        collected_at=collected,
        retention_until=retention_until,
        deadline=deadline,
        adapter_id=adapter_id,
        candidates=candidates,
        seen=seen,
        seen_feeds=seen_feeds,
        previous_pages=previous_pages,
        next_pages=dict(previous_pages),
        observations=[],
        projections=[],
        metrics=_TelemetryState(
            bytes_received=discovery_bytes,
            bytes_accepted=discovery_bytes,
        ),
    )
    return context, discovery_bytes


def _collect_serial_pages(context: _CollectionContext, discovery_bytes: int) -> None:
    usage = CrawlUsage(bytes_fetched=discovery_bytes)
    index = 0
    while index < len(context.candidates):
        if context.deadline.exceeded:
            _mark_deadline(context)
            break
        if usage.pages_fetched >= context.target.max_pages:
            break
        candidate = context.candidates[index]
        index += 1
        authorize_public_web_url(context.entry, candidate.url, now=context.collected_at)
        previous = context.previous_pages.get(candidate.url)
        etag, last_modified = _conditional_validators(previous, candidate)
        context.metrics.attempted_pages += 1
        try:
            fetched = context.client.fetch_page(
                context.target,
                candidate.url,
                context.robots,
                usage=usage,
                depth=candidate.depth,
                etag=etag,
                last_modified=last_modified,
            )
        except PublicWebDeadlineExceededError:
            context.metrics.failed_pages += 1
            _mark_deadline(context)
            break
        except PublicWebPolicyDeniedError:
            context.metrics.failed_pages += 1
            context.metrics.policy_denials += 1
            continue
        usage = CrawlUsage(
            pages_fetched=usage.pages_fetched + 1,
            bytes_fetched=usage.bytes_fetched + fetched.bytes_received,
        )
        context.metrics.max_concurrency_used = 1
        context.metrics.record_fetch(fetched)
        _apply_fetched(context, candidate, previous, fetched)
        if fetched.status_code != _NOT_MODIFIED_STATUS:
            usage = _discover_after_fetch(context, candidate, fetched, usage)


def _collect_concurrent_pages(
    context: _CollectionContext,
    discovery_bytes: int,
    effective_concurrency: int,
) -> None:
    budget = CrawlBudgetCoordinator(
        max_pages=context.target.max_pages,
        max_total_bytes=context.target.max_total_bytes,
        max_resource_bytes=context.target.max_resource_bytes,
        initial_bytes=discovery_bytes,
    )
    index = 0
    with ThreadPoolExecutor(
        max_workers=effective_concurrency,
        thread_name_prefix="cip-public-web",
    ) as executor:
        while index < len(context.candidates) and not context.metrics.deadline_exceeded:
            wave, index = _admit_wave(context, budget, index, effective_concurrency)
            if not wave:
                break
            outcomes = _execute_wave(context, executor, wave)
            _settle_reservations(budget, outcomes)
            _apply_wave(context, budget, outcomes)


def _admit_wave(
    context: _CollectionContext,
    budget: CrawlBudgetCoordinator,
    index: int,
    effective_concurrency: int,
) -> tuple[list[_PageWork], int]:
    wave: list[_PageWork] = []
    while index < len(context.candidates) and len(wave) < effective_concurrency:
        if context.deadline.exceeded:
            _mark_deadline(context)
            break
        candidate = context.candidates[index]
        authorize_public_web_url(context.entry, candidate.url, now=context.collected_at)
        reservation = budget.reserve()
        if reservation is None:
            break
        previous = context.previous_pages.get(candidate.url)
        etag, last_modified = _conditional_validators(previous, candidate)
        wave.append(
            _PageWork(
                candidate=candidate,
                previous=previous,
                reservation=reservation,
                usage=_reserved_usage(context.target, reservation),
                etag=etag,
                last_modified=last_modified,
            )
        )
        index += 1
    context.metrics.attempted_pages += len(wave)
    context.metrics.max_concurrency_used = max(
        context.metrics.max_concurrency_used,
        len(wave),
    )
    return wave, index


def _execute_wave(
    context: _CollectionContext,
    executor: ThreadPoolExecutor,
    wave: list[_PageWork],
) -> list[_PageOutcome]:
    futures = [
        executor.submit(
            _fetch_page_work,
            context.client,
            context.target,
            context.robots,
            work,
        )
        for work in wave
    ]
    return [future.result() for future in futures]


def _settle_reservations(
    budget: CrawlBudgetCoordinator,
    outcomes: list[_PageOutcome],
) -> None:
    for outcome in outcomes:
        received = (
            outcome.fetched.bytes_received
            if outcome.fetched is not None
            else outcome.work.reservation.byte_allowance
        )
        budget.commit(outcome.work.reservation, accepted_bytes=received)


def _apply_wave(
    context: _CollectionContext,
    budget: CrawlBudgetCoordinator,
    outcomes: list[_PageOutcome],
) -> None:
    for outcome in outcomes:
        if outcome.error is not None:
            _apply_page_error(context, outcome.error)
            continue
        fetched = outcome.fetched
        if fetched is None:
            raise RuntimeError("public web page outcome omitted result")
        context.metrics.record_fetch(fetched)
        candidate = outcome.work.candidate
        _apply_fetched(context, candidate, outcome.work.previous, fetched)
        if fetched.status_code == _NOT_MODIFIED_STATUS:
            continue
        usage = CrawlUsage(
            pages_fetched=budget.pages_used,
            bytes_fetched=budget.bytes_used,
        )
        try:
            feed_usage = _discover_after_fetch(context, candidate, fetched, usage)
        except PublicWebDeadlineExceededError:
            _mark_deadline(context)
            continue
        feed_bytes = feed_usage.bytes_fetched - budget.bytes_used
        budget.consume_bytes(feed_bytes)


def _apply_page_error(context: _CollectionContext, error: Exception) -> None:
    context.metrics.failed_pages += 1
    if isinstance(error, PublicWebDeadlineExceededError):
        _mark_deadline(context)
        return
    if isinstance(error, PublicWebPolicyDeniedError):
        context.metrics.policy_denials += 1
        return
    raise error


def _fetch_page_work(
    client: PublicWebClient,
    target: PublicWebTarget,
    robots: RobotsRules,
    work: _PageWork,
) -> _PageOutcome:
    try:
        fetched = client.fetch_page(
            target,
            work.candidate.url,
            robots,
            usage=work.usage,
            depth=work.candidate.depth,
            etag=work.etag,
            last_modified=work.last_modified,
        )
    except Exception as exc:
        return _PageOutcome(work=work, error=exc)
    return _PageOutcome(work=work, fetched=fetched)


def _reserved_usage(target: PublicWebTarget, reservation: CrawlReservation) -> CrawlUsage:
    return CrawlUsage(
        pages_fetched=target.max_pages - 1,
        bytes_fetched=target.max_total_bytes - reservation.byte_allowance,
    )


def _apply_fetched(
    context: _CollectionContext,
    candidate: PublicWebDiscoveryCandidate,
    previous: PageCheckpoint | None,
    fetched: PublicWebFetchResult,
) -> None:
    if candidate.security_txt and fetched.status_code in _TOMBSTONE_STATUSES:
        return
    mapped = _map_candidate(
        context.target,
        candidate,
        fetched,
        collection_job_id=context.collection_job_id,
        collected_at=context.collected_at,
        retention_until=context.retention_until,
        previous=previous,
        adapter_id=context.adapter_id,
    )
    if mapped.observation is not None:
        context.observations.append(mapped.observation)
    context.projections.append(mapped.projection)
    context.next_pages[candidate.url] = _next_page_checkpoint(
        candidate,
        previous,
        mapped,
        fetched,
    )


def _discover_after_fetch(
    context: _CollectionContext,
    candidate: PublicWebDiscoveryCandidate,
    fetched: PublicWebFetchResult,
    usage: CrawlUsage,
) -> CrawlUsage:
    before_bytes = usage.bytes_fetched
    usage = discover_html_feeds(
        context.client,
        context.entry,
        context.target,
        context.robots,
        fetched,
        context.candidates,
        context.seen,
        context.seen_feeds,
        usage=usage,
        now=context.collected_at,
    )
    feed_bytes = usage.bytes_fetched - before_bytes
    context.metrics.bytes_received += feed_bytes
    context.metrics.bytes_accepted += feed_bytes
    _discover_links_with_metrics(context, candidate, fetched)
    return usage


def _discover_links_with_metrics(
    context: _CollectionContext,
    candidate: PublicWebDiscoveryCandidate,
    fetched: PublicWebFetchResult,
) -> None:
    before = len(context.candidates)
    discover_recursive_links(
        context.target,
        candidate,
        fetched,
        context.candidates,
        context.seen,
    )
    admitted = len(context.candidates) - before
    context.metrics.links_discovered += admitted
    context.metrics.links_admitted += admitted


def _mark_deadline(context: _CollectionContext) -> None:
    context.metrics.deadline_exceeded = True
    context.metrics.cancelled = True


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
    adapter_id: str,
) -> MappedPublicPage:
    previous_state = _previous_state(previous)
    if candidate.security_txt:
        if fetched.mime_type != "text/plain":
            raise PublicWebCollectionDeniedError("security.txt must be served as text/plain")
        return map_security_txt(
            target,
            fetched,
            parse_security_txt(fetched.body, target),
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
        adapter_id=adapter_id,
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
