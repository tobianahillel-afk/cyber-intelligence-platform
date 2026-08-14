from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from cip.adapters.sources.public_web.client import (
    PublicWebClient,
    PublicWebDeadlineExceededError,
    PublicWebFetchResult,
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
        browser_fallback_count = len(fallback_urls) if isinstance(fallback_urls, tuple) else 0
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
            browser_fallback_count=browser_fallback_count,
            policy_denials=self.policy_denials,
            redirects=self.redirects,
            elapsed_seconds=deadline.elapsed_seconds,
            deadline_exceeded=self.deadline_exceeded,
            cancelled=self.cancelled,
            configured_concurrency=configured_concurrency,
            effective_concurrency=effective_concurrency,
            max_concurrency_used=self.max_concurrency_used,
        )


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
    next_pages = dict(previous_pages)
    observations: list[RawObservation] = []
    projections: list[PublicFootprintProjection] = []
    metrics = _TelemetryState(
        bytes_received=discovery_bytes,
        bytes_accepted=discovery_bytes,
    )
    effective_concurrency = (
        target.max_crawl_concurrency if client.supports_concurrent_fetches else 1
    )
    if effective_concurrency == 1:
        _collect_serial_pages(
            client,
            entry,
            target,
            robots,
            candidates,
            seen,
            seen_feeds,
            previous_pages,
            next_pages,
            observations,
            projections,
            metrics,
            collection_job_id=collection_job_id,
            collected_at=collected,
            retention_until=retention_until,
            discovery_bytes=discovery_bytes,
            adapter_id=adapter_id,
        )
    else:
        _collect_concurrent_pages(
            client,
            entry,
            target,
            robots,
            candidates,
            seen,
            seen_feeds,
            previous_pages,
            next_pages,
            observations,
            projections,
            metrics,
            deadline=deadline,
            collection_job_id=collection_job_id,
            collected_at=collected,
            retention_until=retention_until,
            discovery_bytes=discovery_bytes,
            effective_concurrency=effective_concurrency,
            adapter_id=adapter_id,
        )
    return PublicWebCollectionBatch(
        observations=tuple(observations),
        projections=tuple(projections),
        checkpoint=PublicWebCheckpoint(
            pages=next_pages,
            feed_urls=tuple(sorted(seen_feeds)),
        ),
        not_modified=not observations,
        telemetry=metrics.freeze(
            client=client,
            deadline=deadline,
            configured_concurrency=target.max_crawl_concurrency,
            effective_concurrency=effective_concurrency,
        ),
    )


def _collect_serial_pages(
    client: PublicWebClient,
    entry: SourceRegistryEntry,
    target: PublicWebTarget,
    robots: object,
    candidates: list[PublicWebDiscoveryCandidate],
    seen: set[str],
    seen_feeds: set[str],
    previous_pages: dict[str, PageCheckpoint],
    next_pages: dict[str, PageCheckpoint],
    observations: list[RawObservation],
    projections: list[PublicFootprintProjection],
    metrics: _TelemetryState,
    *,
    collection_job_id: UUID,
    collected_at: datetime,
    retention_until: datetime,
    discovery_bytes: int,
    adapter_id: str,
) -> None:
    from cip.adapters.sources.public_web.client import RobotsRules

    if not isinstance(robots, RobotsRules):
        raise TypeError("robots must be RobotsRules")
    usage = CrawlUsage(bytes_fetched=discovery_bytes)
    index = 0
    while index < len(candidates):
        candidate = candidates[index]
        index += 1
        if usage.pages_fetched >= target.max_pages:
            break
        authorize_public_web_url(entry, candidate.url, now=collected_at)
        previous = previous_pages.get(candidate.url)
        etag, last_modified = _conditional_validators(previous, candidate)
        metrics.attempted_pages += 1
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
            bytes_fetched=usage.bytes_fetched + fetched.bytes_received,
        )
        metrics.max_concurrency_used = max(metrics.max_concurrency_used, 1)
        metrics.record_fetch(fetched)
        if candidate.security_txt and fetched.status_code in _TOMBSTONE_STATUSES:
            continue
        _process_fetched_candidate(
            client,
            entry,
            target,
            robots,
            candidate,
            previous,
            fetched,
            candidates,
            seen,
            seen_feeds,
            next_pages,
            observations,
            projections,
            metrics,
            collection_job_id=collection_job_id,
            collected_at=collected_at,
            retention_until=retention_until,
            usage=usage,
            adapter_id=adapter_id,
        )
        if fetched.status_code == _NOT_MODIFIED_STATUS:
            continue
        before_bytes = usage.bytes_fetched
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
            now=collected_at,
        )
        feed_bytes = usage.bytes_fetched - before_bytes
        metrics.bytes_received += feed_bytes
        metrics.bytes_accepted += feed_bytes
        _discover_links_with_metrics(target, candidate, fetched, candidates, seen, metrics)


def _collect_concurrent_pages(
    client: PublicWebClient,
    entry: SourceRegistryEntry,
    target: PublicWebTarget,
    robots: object,
    candidates: list[PublicWebDiscoveryCandidate],
    seen: set[str],
    seen_feeds: set[str],
    previous_pages: dict[str, PageCheckpoint],
    next_pages: dict[str, PageCheckpoint],
    observations: list[RawObservation],
    projections: list[PublicFootprintProjection],
    metrics: _TelemetryState,
    *,
    deadline: CrawlDeadline,
    collection_job_id: UUID,
    collected_at: datetime,
    retention_until: datetime,
    discovery_bytes: int,
    effective_concurrency: int,
    adapter_id: str,
) -> None:
    from cip.adapters.sources.public_web.client import RobotsRules

    if not isinstance(robots, RobotsRules):
        raise TypeError("robots must be RobotsRules")
    budget = CrawlBudgetCoordinator(
        max_pages=target.max_pages,
        max_total_bytes=target.max_total_bytes,
        max_resource_bytes=target.max_resource_bytes,
        initial_bytes=discovery_bytes,
    )
    index = 0
    with ThreadPoolExecutor(
        max_workers=effective_concurrency,
        thread_name_prefix="cip-public-web",
    ) as executor:
        while index < len(candidates):
            if deadline.exceeded:
                metrics.deadline_exceeded = True
                metrics.cancelled = True
                break
            wave: list[_PageWork] = []
            while index < len(candidates) and len(wave) < effective_concurrency:
                if deadline.exceeded:
                    metrics.deadline_exceeded = True
                    metrics.cancelled = True
                    break
                candidate = candidates[index]
                authorize_public_web_url(entry, candidate.url, now=collected_at)
                reservation = budget.reserve()
                if reservation is None:
                    break
                index += 1
                previous = previous_pages.get(candidate.url)
                etag, last_modified = _conditional_validators(previous, candidate)
                wave.append(
                    _PageWork(
                        candidate=candidate,
                        previous=previous,
                        reservation=reservation,
                        usage=CrawlUsage(
                            pages_fetched=target.max_pages - 1,
                            bytes_fetched=(
                                target.max_total_bytes - reservation.byte_allowance
                            ),
                        ),
                        etag=etag,
                        last_modified=last_modified,
                    )
                )
            if not wave:
                break
            metrics.attempted_pages += len(wave)
            metrics.max_concurrency_used = max(metrics.max_concurrency_used, len(wave))
            futures = [
                executor.submit(_fetch_page_work, client, target, robots, work)
                for work in wave
            ]
            outcomes = [future.result() for future in futures]
            for outcome in outcomes:
                if outcome.fetched is not None:
                    budget.commit(
                        outcome.work.reservation,
                        accepted_bytes=outcome.fetched.bytes_received,
                    )
                else:
                    budget.commit(
                        outcome.work.reservation,
                        accepted_bytes=outcome.work.reservation.byte_allowance,
                    )
            for outcome in outcomes:
                if outcome.error is not None:
                    metrics.failed_pages += 1
                    if isinstance(outcome.error, PublicWebDeadlineExceededError):
                        metrics.deadline_exceeded = True
                        metrics.cancelled = True
                        continue
                    raise outcome.error
                fetched = outcome.fetched
                if fetched is None:
                    raise RuntimeError("public web page outcome omitted result")
                metrics.record_fetch(fetched)
                candidate = outcome.work.candidate
                if candidate.security_txt and fetched.status_code in _TOMBSTONE_STATUSES:
                    continue
                _process_fetched_candidate(
                    client,
                    entry,
                    target,
                    robots,
                    candidate,
                    outcome.work.previous,
                    fetched,
                    candidates,
                    seen,
                    seen_feeds,
                    next_pages,
                    observations,
                    projections,
                    metrics,
                    collection_job_id=collection_job_id,
                    collected_at=collected_at,
                    retention_until=retention_until,
                    usage=CrawlUsage(
                        pages_fetched=budget.pages_used,
                        bytes_fetched=budget.bytes_used,
                    ),
                    adapter_id=adapter_id,
                )
                if fetched.status_code == _NOT_MODIFIED_STATUS:
                    continue
                before_bytes = budget.bytes_used
                try:
                    feed_usage = discover_html_feeds(
                        client,
                        entry,
                        target,
                        robots,
                        fetched,
                        candidates,
                        seen,
                        seen_feeds,
                        usage=CrawlUsage(
                            pages_fetched=budget.pages_used,
                            bytes_fetched=budget.bytes_used,
                        ),
                        now=collected_at,
                    )
                except PublicWebDeadlineExceededError:
                    metrics.deadline_exceeded = True
                    metrics.cancelled = True
                    break
                feed_bytes = feed_usage.bytes_fetched - before_bytes
                budget.consume_bytes(feed_bytes)
                metrics.bytes_received += feed_bytes
                metrics.bytes_accepted += feed_bytes
                _discover_links_with_metrics(
                    target,
                    candidate,
                    fetched,
                    candidates,
                    seen,
                    metrics,
                )
            if metrics.deadline_exceeded:
                break


def _fetch_page_work(
    client: PublicWebClient,
    target: PublicWebTarget,
    robots: object,
    work: _PageWork,
) -> _PageOutcome:
    from cip.adapters.sources.public_web.client import RobotsRules

    if not isinstance(robots, RobotsRules):
        return _PageOutcome(work=work, error=TypeError("robots must be RobotsRules"))
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


def _process_fetched_candidate(
    client: PublicWebClient,
    entry: SourceRegistryEntry,
    target: PublicWebTarget,
    robots: object,
    candidate: PublicWebDiscoveryCandidate,
    previous: PageCheckpoint | None,
    fetched: PublicWebFetchResult,
    candidates: list[PublicWebDiscoveryCandidate],
    seen: set[str],
    seen_feeds: set[str],
    next_pages: dict[str, PageCheckpoint],
    observations: list[RawObservation],
    projections: list[PublicFootprintProjection],
    metrics: _TelemetryState,
    *,
    collection_job_id: UUID,
    collected_at: datetime,
    retention_until: datetime,
    usage: CrawlUsage,
    adapter_id: str,
) -> None:
    del client, entry, robots, candidates, seen, seen_feeds, metrics, usage
    mapped = _map_candidate(
        target,
        candidate,
        fetched,
        collection_job_id=collection_job_id,
        collected_at=collected_at,
        retention_until=retention_until,
        previous=previous,
        adapter_id=adapter_id,
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


def _discover_links_with_metrics(
    target: PublicWebTarget,
    candidate: PublicWebDiscoveryCandidate,
    fetched: PublicWebFetchResult,
    candidates: list[PublicWebDiscoveryCandidate],
    seen: set[str],
    metrics: _TelemetryState,
) -> None:
    before = len(candidates)
    discover_recursive_links(target, candidate, fetched, candidates, seen)
    admitted = len(candidates) - before
    metrics.links_discovered += admitted
    metrics.links_admitted += admitted


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
