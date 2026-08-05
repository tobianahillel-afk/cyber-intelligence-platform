from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from cip.modules.evidence.domain.entities import Evidence
from cip.modules.opportunities.domain.entities import CommercialSignal
from cip.modules.organizations.application.identity import IdentityProjection
from cip.modules.organizations.domain.entities import Organization
from cip.modules.procurement_history.domain.models import ProcurementHistoryProjection
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
    identity_projections: tuple[IdentityProjection, ...] = ()
    procurement_organizations: tuple[Organization, ...] = ()
    procurement_projections: tuple[ProcurementHistoryProjection, ...] = ()
    quota_remaining: int | None = None
    request_cost: float = 0.0

    def __post_init__(self) -> None:
        organization_ids = {organization.id for organization in self.procurement_organizations}
        for projection in self.procurement_projections:
            if projection.publication.buyer_organization_id not in organization_ids:
                raise ValueError(
                    "procurement projection requires its buyer organization in the batch"
                )
        if self.quota_remaining is not None and self.quota_remaining < 0:
            raise ValueError("quota_remaining cannot be negative")
        if self.request_cost < 0:
            raise ValueError("request_cost cannot be negative")


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
