from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from time import monotonic


@dataclass(frozen=True, slots=True)
class CrawlTelemetry:
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
    browser_fallback_count: int = 0
    policy_denials: int = 0
    redirects: int = 0
    elapsed_seconds: float = 0.0
    deadline_exceeded: bool = False
    cancelled: bool = False
    configured_concurrency: int = 1
    max_concurrency_used: int = 0

    def __post_init__(self) -> None:
        integer_fields = (
            "attempted_pages",
            "fetched_pages",
            "not_modified_pages",
            "tombstoned_pages",
            "failed_pages",
            "bytes_received",
            "bytes_accepted",
            "links_discovered",
            "links_admitted",
            "links_denied",
            "browser_fallback_count",
            "policy_denials",
            "redirects",
            "max_concurrency_used",
        )
        for field_name in integer_fields:
            if getattr(self, field_name) < 0:
                raise ValueError(f"{field_name} cannot be negative")
        if self.elapsed_seconds < 0:
            raise ValueError("elapsed_seconds cannot be negative")
        if self.configured_concurrency < 1:
            raise ValueError("configured_concurrency must be positive")
        if self.max_concurrency_used > self.configured_concurrency:
            raise ValueError("max_concurrency_used cannot exceed configured_concurrency")


@dataclass(frozen=True, slots=True)
class CrawlReservation:
    sequence: int
    byte_allowance: int

    def __post_init__(self) -> None:
        if self.sequence < 0:
            raise ValueError("reservation sequence cannot be negative")
        if self.byte_allowance < 1:
            raise ValueError("reservation byte_allowance must be positive")


class CrawlDeadline:
    def __init__(
        self,
        duration_seconds: float,
        *,
        clock: Callable[[], float] = monotonic,
    ) -> None:
        if duration_seconds <= 0:
            raise ValueError("crawl deadline duration must be positive")
        self._clock = clock
        self._started_at = clock()
        self._expires_at = self._started_at + duration_seconds

    @property
    def exceeded(self) -> bool:
        return self.remaining_seconds <= 0.0

    @property
    def remaining_seconds(self) -> float:
        return max(0.0, self._expires_at - self._clock())

    @property
    def elapsed_seconds(self) -> float:
        return max(0.0, self._clock() - self._started_at)


class CrawlBudgetCoordinator:
    """Own synchronized crawl admission allowances in deterministic sequence order."""

    def __init__(
        self,
        *,
        max_pages: int,
        max_total_bytes: int,
        max_resource_bytes: int,
        initial_bytes: int = 0,
    ) -> None:
        if max_pages < 1:
            raise ValueError("max_pages must be positive")
        if max_total_bytes < 1 or max_resource_bytes < 1:
            raise ValueError("crawl byte budgets must be positive")
        if max_resource_bytes > max_total_bytes:
            raise ValueError("max_resource_bytes cannot exceed max_total_bytes")
        if not 0 <= initial_bytes <= max_total_bytes:
            raise ValueError("initial_bytes must fit the total byte budget")
        self._max_pages = max_pages
        self._max_total_bytes = max_total_bytes
        self._max_resource_bytes = max_resource_bytes
        self._used_pages = 0
        self._used_bytes = initial_bytes
        self._reserved_pages = 0
        self._reserved_bytes = 0
        self._next_sequence = 0
        self._active: dict[int, CrawlReservation] = {}

    @property
    def pages_used(self) -> int:
        return self._used_pages

    @property
    def bytes_used(self) -> int:
        return self._used_bytes

    @property
    def active_reservations(self) -> int:
        return len(self._active)

    def reserve(self) -> CrawlReservation | None:
        if self._used_pages + self._reserved_pages >= self._max_pages:
            return None
        remaining_bytes = self._max_total_bytes - self._used_bytes - self._reserved_bytes
        if remaining_bytes <= 0:
            return None
        reservation = CrawlReservation(
            sequence=self._next_sequence,
            byte_allowance=min(self._max_resource_bytes, remaining_bytes),
        )
        self._next_sequence += 1
        self._reserved_pages += 1
        self._reserved_bytes += reservation.byte_allowance
        self._active[reservation.sequence] = reservation
        return reservation

    def commit(self, reservation: CrawlReservation, *, accepted_bytes: int) -> None:
        current = self._pop_active(reservation)
        if not 0 <= accepted_bytes <= current.byte_allowance:
            raise ValueError("accepted_bytes exceeds the reserved crawl allowance")
        self._reserved_pages -= 1
        self._reserved_bytes -= current.byte_allowance
        self._used_pages += 1
        self._used_bytes += accepted_bytes

    def release(self, reservation: CrawlReservation) -> None:
        current = self._pop_active(reservation)
        self._reserved_pages -= 1
        self._reserved_bytes -= current.byte_allowance

    def _pop_active(self, reservation: CrawlReservation) -> CrawlReservation:
        current = self._active.pop(reservation.sequence, None)
        if current != reservation:
            raise ValueError("crawl reservation is not active")
        return current
