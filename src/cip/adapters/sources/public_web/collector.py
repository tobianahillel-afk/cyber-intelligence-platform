from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from uuid import UUID

from cip.adapters.sources.public_web.client import (
    PublicWebClient,
    PublicWebDeadlineExceededError,
    PublicWebFetchResult,
    PublicWebPolicyDeniedError,
)
from cip.adapters.sources.public_web.collection_policy import (
    PublicWebCollectionDeniedError,
    authorize_public_web_url,
)
from cip.adapters.sources.public_web.collector_mapping import apply_fetched
from cip.adapters.sources.public_web.collector_state import (
    CollectionContext,
    PageCheckpoint,
    PageOutcome,
    PageWork,
    PublicWebCheckpoint,
    PublicWebCollectionBatch,
    TelemetryState,
    conditional_validators,
    mark_deadline,
    reserved_usage,
    restore_checkpoint_candidates,
)
from cip.adapters.sources.public_web.crawl_runtime import CrawlBudgetCoordinator, CrawlDeadline
from cip.adapters.sources.public_web.discovery import (
    PublicWebDiscoveryCandidate,
    discover_html_feeds,
    discover_initial_candidates,
    discover_recursive_links,
)
from cip.adapters.sources.public_web.registry import PublicWebTarget
from cip.modules.public_footprint.domain.scope import CrawlUsage
from cip.modules.source_governance.infrastructure.registry import SourceRegistryEntry
from cip.shared.kernel.time import require_aware_utc

_NOT_MODIFIED_STATUS = 304
_DEFAULT_ADAPTER_ID = "public-web-sitemap"


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
    return _build_batch(context, effective)


def _build_batch(
    context: CollectionContext,
    effective_concurrency: int,
) -> PublicWebCollectionBatch:
    return PublicWebCollectionBatch(
        observations=tuple(context.observations),
        projections=tuple(context.projections),
        checkpoint=PublicWebCheckpoint(
            pages=context.next_pages,
            feed_urls=tuple(sorted(context.seen_feeds)),
        ),
        not_modified=not context.observations,
        telemetry=context.metrics.freeze(
            client=context.client,
            deadline=context.deadline,
            configured_concurrency=context.target.max_crawl_concurrency,
            effective_concurrency=effective_concurrency,
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
) -> tuple[CollectionContext, int]:
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
    restore_checkpoint_candidates(target, previous_pages, candidates, seen)
    context = CollectionContext(
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
        metrics=TelemetryState(
            bytes_received=discovery_bytes,
            bytes_accepted=discovery_bytes,
        ),
    )
    return context, discovery_bytes


def _collect_serial_pages(context: CollectionContext, discovery_bytes: int) -> None:
    usage = CrawlUsage(bytes_fetched=discovery_bytes)
    index = 0
    while index < len(context.candidates):
        if context.deadline.exceeded:
            mark_deadline(context)
            break
        if usage.pages_fetched >= context.target.max_pages:
            break
        candidate = context.candidates[index]
        index += 1
        authorize_public_web_url(context.entry, candidate.url, now=context.collected_at)
        previous = context.previous_pages.get(candidate.url)
        etag, last_modified = conditional_validators(previous, candidate)
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
            mark_deadline(context)
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
        apply_fetched(context, candidate, previous, fetched)
        if fetched.status_code != _NOT_MODIFIED_STATUS:
            usage = _discover_after_fetch(context, candidate, fetched, usage)


def _collect_concurrent_pages(
    context: CollectionContext,
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
    context: CollectionContext,
    budget: CrawlBudgetCoordinator,
    index: int,
    effective_concurrency: int,
) -> tuple[list[PageWork], int]:
    wave: list[PageWork] = []
    while index < len(context.candidates) and len(wave) < effective_concurrency:
        if context.deadline.exceeded:
            mark_deadline(context)
            break
        candidate = context.candidates[index]
        authorize_public_web_url(context.entry, candidate.url, now=context.collected_at)
        reservation = budget.reserve()
        if reservation is None:
            break
        previous = context.previous_pages.get(candidate.url)
        etag, last_modified = conditional_validators(previous, candidate)
        wave.append(
            PageWork(
                candidate=candidate,
                previous=previous,
                reservation=reservation,
                usage=reserved_usage(context.target, reservation),
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
    context: CollectionContext,
    executor: ThreadPoolExecutor,
    wave: list[PageWork],
) -> list[PageOutcome]:
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
    outcomes: list[PageOutcome],
) -> None:
    for outcome in outcomes:
        received = (
            outcome.fetched.bytes_received
            if outcome.fetched is not None
            else outcome.work.reservation.byte_allowance
        )
        budget.commit(outcome.work.reservation, accepted_bytes=received)


def _apply_wave(
    context: CollectionContext,
    budget: CrawlBudgetCoordinator,
    outcomes: list[PageOutcome],
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
        apply_fetched(context, candidate, outcome.work.previous, fetched)
        if fetched.status_code == _NOT_MODIFIED_STATUS:
            continue
        usage = CrawlUsage(
            pages_fetched=budget.pages_used,
            bytes_fetched=budget.bytes_used,
        )
        try:
            feed_usage = _discover_after_fetch(context, candidate, fetched, usage)
        except PublicWebDeadlineExceededError:
            mark_deadline(context)
            continue
        budget.consume_bytes(feed_usage.bytes_fetched - budget.bytes_used)


def _apply_page_error(context: CollectionContext, error: Exception) -> None:
    context.metrics.failed_pages += 1
    if isinstance(error, PublicWebDeadlineExceededError):
        mark_deadline(context)
        return
    if isinstance(error, PublicWebPolicyDeniedError):
        context.metrics.policy_denials += 1
        return
    raise error


def _fetch_page_work(
    client: PublicWebClient,
    target: PublicWebTarget,
    robots: object,
    work: PageWork,
) -> PageOutcome:
    try:
        fetched = client.fetch_page(
            target,
            work.candidate.url,
            robots,  # type: ignore[arg-type]
            usage=work.usage,
            depth=work.candidate.depth,
            etag=work.etag,
            last_modified=work.last_modified,
        )
    except Exception as exc:
        return PageOutcome(work=work, error=exc)
    return PageOutcome(work=work, fetched=fetched)


def _discover_after_fetch(
    context: CollectionContext,
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
    return usage


__all__ = [
    "PageCheckpoint",
    "PublicWebCheckpoint",
    "PublicWebCollectionBatch",
    "collect_public_web_target",
]
