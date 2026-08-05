from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from cip.modules.source_portfolio.application.errors import SourcePortfolioNotFoundError
from cip.modules.source_portfolio.domain.models import (
    AdapterCapabilityManifest,
    AnomalyState,
    BackfillState,
    CatalogStatus,
    CollectionMode,
    FreshnessState,
    SchemaState,
    SourceCatalogEntry,
    SourceHealth,
)
from cip.modules.source_portfolio.infrastructure.models import (
    AdapterCapabilityRecord,
    BackfillPartitionRecord,
    SourceHealthRecord,
    SourcePortfolioAuditRecord,
    SourcePortfolioRecord,
)
from cip.modules.source_portfolio.infrastructure.persistence_time import persistence_utc


def get_portfolio_record(session: Session, source_id: str) -> SourcePortfolioRecord:
    record = session.get(SourcePortfolioRecord, source_id.strip())
    if record is None:
        raise SourcePortfolioNotFoundError(source_id)
    return record


def get_health_record(session: Session, source_id: str) -> SourceHealthRecord:
    record = session.get(SourceHealthRecord, source_id.strip())
    if record is None:
        raise SourcePortfolioNotFoundError(source_id)
    return record


def get_partition(session: Session, partition_id: UUID) -> BackfillPartitionRecord:
    record = session.get(BackfillPartitionRecord, partition_id)
    if record is None:
        raise SourcePortfolioNotFoundError(str(partition_id))
    return record


def capability_record(
    session: Session,
    source_id: str,
) -> AdapterCapabilityRecord | None:
    return session.scalar(
        select(AdapterCapabilityRecord).where(AdapterCapabilityRecord.source_id == source_id)
    )


def to_catalog_entry(session: Session, record: SourcePortfolioRecord) -> SourceCatalogEntry:
    capability = capability_record(session, record.source_id)
    return SourceCatalogEntry(
        source_id=record.source_id,
        display_name=record.display_name,
        canonical_url=record.canonical_url,
        category=record.category,
        status=CatalogStatus(record.status),
        freshness_max_age_seconds=record.freshness_max_age_seconds,
        commercial_use_cases=tuple(record.commercial_use_cases),
        adapter=to_manifest(capability) if capability is not None else None,
        authorization_expires_at=persistence_utc(record.authorization_expires_at),
        review_due_at=persistence_utc(record.review_due_at),
        candidate_origin=record.candidate_origin,
        monthly_cost_limit=record.monthly_cost_limit,
        metadata=record.extra_metadata,
    )


def to_manifest(record: AdapterCapabilityRecord) -> AdapterCapabilityManifest:
    return AdapterCapabilityManifest(
        source_id=record.source_id,
        adapter_id=record.adapter_id,
        adapter_version=record.adapter_version,
        provider_schema_version=record.provider_schema_version,
        modes=frozenset(CollectionMode(value) for value in record.modes),
        canonical_output_types=tuple(record.canonical_output_types),
        supports_corrections=record.supports_corrections,
        supports_tombstones=record.supports_tombstones,
        supports_retractions=record.supports_retractions,
        max_page_size=record.max_page_size,
        max_window_days=record.max_window_days,
        cost_per_request=record.cost_per_request,
    )


def to_health(
    record: SourceHealthRecord,
    *,
    circuit_state: str = "unknown",
) -> SourceHealth:
    return SourceHealth(
        source_id=record.source_id,
        freshness_state=FreshnessState(record.freshness_state),
        schema_state=SchemaState(record.schema_state),
        volume_state=AnomalyState(record.volume_state),
        field_population_state=AnomalyState(record.field_population_state),
        circuit_state=circuit_state,
        last_attempt_at=persistence_utc(record.last_attempt_at),
        last_success_at=persistence_utc(record.last_success_at),
        last_source_record_at=persistence_utc(record.last_source_record_at),
        consecutive_failures=record.consecutive_failures,
        quota_remaining=record.quota_remaining,
        monthly_cost_used=record.monthly_cost_used,
        cost_window_started_at=persistence_utc(record.cost_window_started_at),
        current_backfill_state=(
            BackfillState(record.current_backfill_state)
            if record.current_backfill_state is not None
            else None
        ),
        last_error_code=record.last_error_code,
    )


def audit(
    session: Session,
    source_id: str,
    action: str,
    actor: str,
    occurred_at: datetime,
    *,
    details: dict[str, object] | None = None,
) -> None:
    session.add(
        SourcePortfolioAuditRecord(
            id=uuid4(),
            source_id=source_id,
            action=bounded_value(action, "action", maximum=100),
            actor=bounded_value(actor, "actor", maximum=200),
            details=details or {},
            occurred_at=occurred_at,
            note=None,
        )
    )


def bounded_value(value: str, field_name: str, *, maximum: int = 300) -> str:
    normalized = value.strip()
    if not normalized or len(normalized) > maximum:
        raise ValueError(f"{field_name} must be non-empty and at most {maximum} characters")
    return normalized


def non_negative(value: float, field_name: str) -> float:
    if value < 0:
        raise ValueError(f"{field_name} cannot be negative")
    return value
