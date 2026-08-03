from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from cip.modules.raw_observations.domain.entities import RawObservation
from cip.modules.source_governance.domain.models import DataCategory


@dataclass(frozen=True, slots=True)
class AdapterCollectionBatch:
    observations: tuple[RawObservation, ...]
    checkpoint_payload: Mapping[str, object]
    not_modified: bool


class CollectionAdapter(Protocol):
    source_id: str
    adapter_id: str
    data_category: DataCategory

    def collect(
        self,
        *,
        collection_job_id: UUID,
        checkpoint_payload: Mapping[str, object] | None,
        collected_at: datetime,
        retention_until: datetime,
    ) -> AdapterCollectionBatch: ...


@dataclass(frozen=True, slots=True)
class ClaimedJob:
    id: UUID
    source_id: str
    adapter_id: str
    attempt: int
    lease_owner: str
    lease_expires_at: datetime
    max_attempts: int
    base_delay_seconds: int
    max_delay_seconds: int
    circuit_failure_threshold: int
    circuit_reset_seconds: int
    checkpoint_payload: Mapping[str, object] | None
