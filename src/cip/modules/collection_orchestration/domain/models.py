from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import StrEnum
from hashlib import sha256
from types import MappingProxyType
from uuid import UUID, uuid4

from cip.shared.kernel.time import require_aware_utc, utc_now


class JobStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    RETRY_SCHEDULED = "retry_scheduled"
    SUCCEEDED = "succeeded"
    NOT_MODIFIED = "not_modified"
    DEAD_LETTERED = "dead_lettered"
    CANCELLED = "cancelled"

    @property
    def is_terminal(self) -> bool:
        return self in {
            JobStatus.SUCCEEDED,
            JobStatus.NOT_MODIFIED,
            JobStatus.DEAD_LETTERED,
            JobStatus.CANCELLED,
        }


class CircuitState(StrEnum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass(frozen=True, slots=True)
class RetryPolicy:
    max_attempts: int = 4
    base_delay_seconds: int = 30
    max_delay_seconds: int = 900
    circuit_failure_threshold: int = 3
    circuit_reset_seconds: int = 900

    def __post_init__(self) -> None:
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be positive")
        if self.base_delay_seconds < 1:
            raise ValueError("base_delay_seconds must be positive")
        if self.max_delay_seconds < self.base_delay_seconds:
            raise ValueError("max_delay_seconds cannot be below base delay")
        if self.circuit_failure_threshold < 1:
            raise ValueError("circuit_failure_threshold must be positive")
        if self.circuit_reset_seconds < 1:
            raise ValueError("circuit_reset_seconds must be positive")

    def delay_for_attempt(self, attempt: int) -> timedelta:
        if attempt < 1:
            raise ValueError("attempt must be positive")
        seconds = min(
            self.base_delay_seconds * (2 ** (attempt - 1)),
            self.max_delay_seconds,
        )
        return timedelta(seconds=seconds)


@dataclass(frozen=True, slots=True)
class SourceSchedule:
    source_id: str
    adapter_id: str
    interval_seconds: int
    lease_seconds: int = 120
    enabled: bool = True
    retry_policy: RetryPolicy = field(default_factory=RetryPolicy)

    def __post_init__(self) -> None:
        if not self.source_id.strip():
            raise ValueError("source_id is required")
        if not self.adapter_id.strip():
            raise ValueError("adapter_id is required")
        if self.interval_seconds < 1:
            raise ValueError("interval_seconds must be positive")
        if self.lease_seconds < 1:
            raise ValueError("lease_seconds must be positive")

    def slot_for(self, now: datetime) -> datetime:
        current = require_aware_utc(now, field_name="now")
        slot_epoch = int(current.timestamp())
        slot_epoch -= slot_epoch % self.interval_seconds
        return datetime.fromtimestamp(slot_epoch, tz=current.tzinfo)


@dataclass(frozen=True, slots=True)
class CollectionJob:
    source_id: str
    adapter_id: str
    scheduled_for: datetime
    available_at: datetime
    lease_seconds: int
    max_attempts: int
    base_delay_seconds: int
    max_delay_seconds: int
    circuit_failure_threshold: int
    circuit_reset_seconds: int
    id: UUID = field(default_factory=uuid4)
    status: JobStatus = JobStatus.PENDING
    attempt: int = 0
    created_at: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        if not self.source_id.strip():
            raise ValueError("source_id is required")
        if not self.adapter_id.strip():
            raise ValueError("adapter_id is required")
        if self.lease_seconds < 1:
            raise ValueError("lease_seconds must be positive")
        for field_name in ("scheduled_for", "available_at", "created_at"):
            value = require_aware_utc(getattr(self, field_name), field_name=field_name)
            object.__setattr__(self, field_name, value)
        RetryPolicy(
            max_attempts=self.max_attempts,
            base_delay_seconds=self.base_delay_seconds,
            max_delay_seconds=self.max_delay_seconds,
            circuit_failure_threshold=self.circuit_failure_threshold,
            circuit_reset_seconds=self.circuit_reset_seconds,
        )
        if self.attempt < 0 or self.attempt > self.max_attempts:
            raise ValueError("attempt must be between zero and max_attempts")

    @classmethod
    def from_schedule(cls, schedule: SourceSchedule, *, scheduled_for: datetime) -> CollectionJob:
        slot = require_aware_utc(scheduled_for, field_name="scheduled_for")
        retry = schedule.retry_policy
        return cls(
            source_id=schedule.source_id,
            adapter_id=schedule.adapter_id,
            scheduled_for=slot,
            available_at=slot,
            lease_seconds=schedule.lease_seconds,
            max_attempts=retry.max_attempts,
            base_delay_seconds=retry.base_delay_seconds,
            max_delay_seconds=retry.max_delay_seconds,
            circuit_failure_threshold=retry.circuit_failure_threshold,
            circuit_reset_seconds=retry.circuit_reset_seconds,
        )

    @property
    def idempotency_key(self) -> str:
        material = f"{self.source_id}\0{self.adapter_id}\0{self.scheduled_for.isoformat()}"
        return sha256(material.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class CollectionCheckpoint:
    source_id: str
    adapter_id: str
    payload: Mapping[str, object]
    version: int
    updated_at: datetime
    last_success_at: datetime | None = None
    last_observation_at: datetime | None = None

    def __post_init__(self) -> None:
        if not self.source_id.strip():
            raise ValueError("source_id is required")
        if not self.adapter_id.strip():
            raise ValueError("adapter_id is required")
        if self.version < 1:
            raise ValueError("checkpoint version must be positive")
        object.__setattr__(self, "payload", MappingProxyType(dict(self.payload)))
        object.__setattr__(
            self,
            "updated_at",
            require_aware_utc(self.updated_at, field_name="updated_at"),
        )
        for field_name in ("last_success_at", "last_observation_at"):
            value = getattr(self, field_name)
            if value is not None:
                object.__setattr__(
                    self,
                    field_name,
                    require_aware_utc(value, field_name=field_name),
                )
