from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from cip.modules.evidence.domain.entities import Evidence
from cip.modules.opportunities.domain.entities import CommercialSignal
from cip.modules.organizations.domain.entities import Organization
from cip.modules.raw_observations.domain.entities import RawObservation
from cip.modules.source_governance.domain.models import DataCategory


class AdapterExecutionError(RuntimeError):
    def __init__(self, message: str, *, error_code: str, retryable: bool) -> None:
        super().__init__(message)
        self.error_code = error_code
        self.retryable = retryable


@dataclass(frozen=True, slots=True)
class CommercialProjection:
    organization: Organization
    evidence: Evidence
    signal: CommercialSignal

    def __post_init__(self) -> None:
        if self.signal.organization_id != self.organization.id:
            raise ValueError("signal organization must match projected organization")
        if self.signal.evidence_id != self.evidence.id:
            raise ValueError("signal evidence must match projected evidence")


@dataclass(frozen=True, slots=True)
class AdapterCollectionBatch:
    observations: tuple[RawObservation, ...]
    checkpoint_payload: Mapping[str, object]
    not_modified: bool
    commercial_projections: tuple[CommercialProjection, ...] = ()


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
