from __future__ import annotations

from dataclasses import replace

import pytest

from cip.adapters.sources.public_web.crawl_runtime import (
    CrawlBudgetCoordinator,
    CrawlDeadline,
    CrawlTelemetry,
)


def test_deadline_uses_whole_crawl_monotonic_clock() -> None:
    now = 10.0

    def clock() -> float:
        return now

    deadline = CrawlDeadline(5.0, clock=clock)
    assert deadline.remaining_seconds == 5.0
    assert deadline.elapsed_seconds == 0.0
    assert deadline.exceeded is False

    now = 15.0
    assert deadline.remaining_seconds == 0.0
    assert deadline.elapsed_seconds == 5.0
    assert deadline.exceeded is True


def test_budget_prevents_duplicate_final_page_allowance() -> None:
    budget = CrawlBudgetCoordinator(
        max_pages=1,
        max_total_bytes=1_000,
        max_resource_bytes=1_000,
    )

    first = budget.reserve()
    assert first is not None
    assert budget.reserve() is None

    budget.commit(first, accepted_bytes=100)
    assert budget.pages_used == 1
    assert budget.bytes_used == 100
    assert budget.reserve() is None


def test_budget_reserves_shared_bytes_before_concurrent_work() -> None:
    budget = CrawlBudgetCoordinator(
        max_pages=4,
        max_total_bytes=1_500,
        max_resource_bytes=1_000,
    )

    first = budget.reserve()
    second = budget.reserve()
    assert first is not None
    assert second is not None
    assert first.byte_allowance == 1_000
    assert second.byte_allowance == 500
    assert budget.reserve() is None

    budget.commit(second, accepted_bytes=400)
    budget.commit(first, accepted_bytes=900)
    assert budget.bytes_used == 1_300

    third = budget.reserve()
    assert third is not None
    assert third.byte_allowance == 200


def test_failed_reservation_releases_page_and_byte_allowance() -> None:
    budget = CrawlBudgetCoordinator(
        max_pages=1,
        max_total_bytes=100,
        max_resource_bytes=100,
    )
    first = budget.reserve()
    assert first is not None
    budget.release(first)

    retry = budget.reserve()
    assert retry is not None
    assert retry.sequence != first.sequence
    assert retry.byte_allowance == 100


def test_budget_rejects_double_commit_and_oversized_acceptance() -> None:
    budget = CrawlBudgetCoordinator(
        max_pages=2,
        max_total_bytes=100,
        max_resource_bytes=50,
    )
    reservation = budget.reserve()
    assert reservation is not None

    with pytest.raises(ValueError, match="exceeds"):
        budget.commit(reservation, accepted_bytes=51)

    assert budget.pages_used == 0
    assert budget.bytes_used == 0
    assert budget.active_reservations == 1
    budget.release(reservation)
    assert budget.active_reservations == 0
    with pytest.raises(ValueError, match="not active"):
        budget.release(reservation)


def test_telemetry_is_bounded_by_configured_concurrency() -> None:
    telemetry = CrawlTelemetry(configured_concurrency=2, max_concurrency_used=2)
    assert replace(telemetry, fetched_pages=1).fetched_pages == 1

    with pytest.raises(ValueError, match="cannot exceed"):
        CrawlTelemetry(configured_concurrency=1, max_concurrency_used=2)
