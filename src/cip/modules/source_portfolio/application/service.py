from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from cip.modules.source_portfolio.domain.models import (
    AdapterCapabilityManifest,
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
from cip.shared.kernel.time import require_aware_utc


class SourcePortfolioNotFoundError(LookupError):
    pass


class SourcePortfolioStateError(RuntimeError):
    pass


def sync_source_portfolio(
    session: Session,
    entries: Sequence[SourceCatalogEntry],
    *,
    now: datetime,
) -> tuple[str, ...]:
    synchronized_at = require_aware_utc(now, field_name="now")
    synchronized: list[str] = []
    for entry in entries:
        record = session.get(SourcePortfolioRecord, entry.source_id)
        if record is None:
            record = SourcePortfolioRecord(
                source_id=entry.source_id,
                created_at=synchronized_at,
                updated_at=synchronized_at,
                display_name=entry.display_name,
                canonical_url=entry.canonical_url,
                category=entry.category,
                status=entry.status.value,
                freshness_max_age_seconds=entry.freshness_max_age_seconds,
                commercial_use_cases=list(entry.commercial_use_cases),
                authorization_expires_at=entry.authorization_expires_at,
                review_due_at=entry.review_due_at,
                candidate_origin=entry.candidate_origin,
                monthly_cost_limit=entry.monthly_cost_limit,
                extra_metadata=dict(entry.metadata),
            )
            session.add(record)
            _audit(session, entry.source_id, "catalog_created", "system", synchronized_at)
        else:
            _refresh_portfolio_record(record, entry, synchronized_at)
        _sync_capability(session, entry.adapter, synchronized_at)
        _ensure_health(session, entry, synchronized_at)
        synchronized.append(entry.source_id)
    session.flush()
    return tuple(synchronized)


def list_source_portfolio(session: Session) -> tuple[SourceCatalogEntry, ...]:
    records = session.scalars(
        select(SourcePortfolioRecord).order_by(SourcePortfolioRecord.source_id)
    ).all()
    return tuple(_to_catalog_entry(session, record) for record in records)


def get_source_portfolio(session: Session, source_id: str) -> SourceCatalogEntry:
    return _to_catalog_entry(session, _get_portfolio_record(session, source_id))


def get_source_health(session: Session, source_id: str) -> SourceHealth:
    record = session.get(SourceHealthRecord, source_id.strip())
    if record is None:
        raise SourcePortfolioNotFoundError(source_id)
    return _to_health(record)


def request_backfill(
    session: Session,
    source_id: str,
    partitions: Sequence[tuple[str, str]],
    *,
    actor: str,
    now: datetime,
) -> tuple[UUID, ...]:
    entry = get_source_portfolio(session, source_id)
    if not entry.executable or entry.adapter is None:
        raise SourcePortfolioStateError("catalog candidates and disabled sources cannot execute")
    if not entry.adapter.supports(CollectionMode.HISTORICAL_BACKFILL):
        raise SourcePortfolioStateError("adapter does not support historical backfill")
    if not partitions:
        raise ValueError("at least one backfill partition is required")
    changed_at = require_aware_utc(now, field_name="now")
    created: list[UUID] = []
    for lower_bound, upper_bound in partitions:
        lower = _bounded_value(lower_bound, "lower_bound")
        upper = _bounded_value(upper_bound, "upper_bound")
        if lower >= upper:
            raise ValueError("partition lower_bound must be below upper_bound")
        partition_key = f"{lower}..{upper}"
        existing = session.scalar(
            select(BackfillPartitionRecord).where(
                BackfillPartitionRecord.source_id == entry.source_id,
                BackfillPartitionRecord.adapter_id == entry.adapter.adapter_id,
                BackfillPartitionRecord.partition_key == partition_key,
            )
        )
        if existing is not None:
            created.append(existing.id)
            continue
        partition = BackfillPartitionRecord(
            id=uuid4(),
            source_id=entry.source_id,
            adapter_id=entry.adapter.adapter_id,
            partition_key=partition_key,
            lower_bound=lower,
            upper_bound=upper,
            state=BackfillState.PENDING.value,
            cursor={},
            attempts=0,
            records_written=0,
            last_error_code=None,
            created_at=changed_at,
            updated_at=changed_at,
            completed_at=None,
        )
        session.add(partition)
        created.append(partition.id)
    _set_backfill_health(session, entry.source_id, BackfillState.PENDING, changed_at)
    _audit(
        session,
        entry.source_id,
        "backfill_requested",
        actor,
        changed_at,
        details={"partition_count": len(partitions)},
    )
    session.flush()
    return tuple(created)


def claim_backfill_partition(
    session: Session,
    source_id: str,
    *,
    actor: str,
    now: datetime,
) -> BackfillPartitionRecord | None:
    entry = get_source_portfolio(session, source_id)
    if entry.status is not CatalogStatus.EXECUTABLE:
        return None
    partition = session.scalar(
        select(BackfillPartitionRecord)
        .where(
            BackfillPartitionRecord.source_id == entry.source_id,
            BackfillPartitionRecord.state.in_(
                (BackfillState.PENDING.value, BackfillState.FAILED.value)
            ),
        )
        .order_by(BackfillPartitionRecord.created_at)
        .with_for_update(skip_locked=True)
    )
    if partition is None:
        return None
    changed_at = require_aware_utc(now, field_name="now")
    partition.state = BackfillState.RUNNING.value
    partition.attempts += 1
    partition.updated_at = changed_at
    partition.last_error_code = None
    _set_backfill_health(session, entry.source_id, BackfillState.RUNNING, changed_at)
    _audit(session, entry.source_id, "backfill_partition_claimed", actor, changed_at)
    session.flush()
    return partition


def complete_backfill_partition(
    session: Session,
    partition_id: UUID,
    *,
    cursor: dict[str, object],
    records_written: int,
    actor: str,
    now: datetime,
) -> None:
    partition = _get_partition(session, partition_id)
    if partition.state != BackfillState.RUNNING.value:
        raise SourcePortfolioStateError("only running partitions can complete")
    if records_written < 0:
        raise ValueError("records_written cannot be negative")
    changed_at = require_aware_utc(now, field_name="now")
    partition.cursor = dict(cursor)
    partition.records_written += records_written
    partition.state = BackfillState.COMPLETED.value
    partition.updated_at = changed_at
    partition.completed_at = changed_at
    remaining = session.scalar(
        select(BackfillPartitionRecord.id).where(
            BackfillPartitionRecord.source_id == partition.source_id,
            BackfillPartitionRecord.state.in_(
                (
                    BackfillState.PENDING.value,
                    BackfillState.RUNNING.value,
                    BackfillState.FAILED.value,
                )
            ),
        )
    )
    state = BackfillState.COMPLETED if remaining is None else BackfillState.RUNNING
    _set_backfill_health(session, partition.source_id, state, changed_at)
    _audit(session, partition.source_id, "backfill_partition_completed", actor, changed_at)
    session.flush()


def pause_source(
    session: Session,
    source_id: str,
    *,
    actor: str,
    now: datetime,
) -> SourceCatalogEntry:
    return _change_source_status(session, source_id, CatalogStatus.PAUSED, actor, now)


def resume_source(
    session: Session,
    source_id: str,
    *,
    actor: str,
    now: datetime,
) -> SourceCatalogEntry:
    record = _get_portfolio_record(session, source_id)
    if _capability_record(session, record.source_id) is None:
        raise SourcePortfolioStateError("catalog candidates cannot be resumed")
    return _change_source_status(session, source_id, CatalogStatus.EXECUTABLE, actor, now)


def disable_source(
    session: Session,
    source_id: str,
    *,
    actor: str,
    now: datetime,
) -> SourceCatalogEntry:
    return _change_source_status(session, source_id, CatalogStatus.DISABLED, actor, now)


def record_collection_success(
    session: Session,
    source_id: str,
    *,
    source_record_at: datetime | None,
    schema_state: SchemaState,
    quota_remaining: int | None,
    cost: float,
    now: datetime,
) -> SourceHealth:
    changed_at = require_aware_utc(now, field_name="now")
    record = _get_health_record(session, source_id)
    record.last_attempt_at = changed_at
    record.last_success_at = changed_at
    record.last_source_record_at = (
        require_aware_utc(source_record_at, field_name="source_record_at")
        if source_record_at is not None
        else record.last_source_record_at
    )
    record.schema_state = schema_state.value
    record.consecutive_failures = 0
    record.quota_remaining = quota_remaining
    record.monthly_cost_used += _non_negative(cost, "cost")
    record.last_error_code = None
    record.freshness_state = _freshness_for_success(session, source_id, record, changed_at).value
    record.updated_at = changed_at
    session.flush()
    return _to_health(record)


def record_collection_failure(
    session: Session,
    source_id: str,
    *,
    error_code: str,
    schema_drift: bool,
    now: datetime,
) -> SourceHealth:
    changed_at = require_aware_utc(now, field_name="now")
    record = _get_health_record(session, source_id)
    record.last_attempt_at = changed_at
    record.consecutive_failures += 1
    record.last_error_code = _bounded_value(error_code, "error_code", maximum=100)
    if schema_drift:
        record.schema_state = SchemaState.DRIFTED.value
    record.freshness_state = FreshnessState.SOURCE_UNAVAILABLE.value
    record.updated_at = changed_at
    session.flush()
    return _to_health(record)


def refresh_freshness(session: Session, source_id: str, *, now: datetime) -> SourceHealth:
    changed_at = require_aware_utc(now, field_name="now")
    entry = get_source_portfolio(session, source_id)
    record = _get_health_record(session, source_id)
    if entry.authorization_expires_at is not None and entry.authorization_expires_at <= changed_at:
        state = FreshnessState.AUTHORIZATION_EXPIRED
    elif entry.adapter is not None and entry.adapter.modes == {CollectionMode.HISTORICAL_BACKFILL}:
        state = FreshnessState.HISTORICAL_ONLY
    elif record.last_success_at is None:
        state = FreshnessState.STALE_REFRESH_QUEUED
    else:
        age = changed_at - persistence_utc(record.last_success_at)
        maximum = timedelta(seconds=entry.freshness_max_age_seconds)
        state = FreshnessState.FRESH if age <= maximum / 2 else FreshnessState.AGING
        if age > maximum:
            state = FreshnessState.STALE_REFRESH_QUEUED
    record.freshness_state = state.value
    record.updated_at = changed_at
    session.flush()
    return _to_health(record)


def _refresh_portfolio_record(
    record: SourcePortfolioRecord,
    entry: SourceCatalogEntry,
    now: datetime,
) -> None:
    record.display_name = entry.display_name
    record.canonical_url = entry.canonical_url
    record.category = entry.category
    if record.status not in {CatalogStatus.PAUSED.value, CatalogStatus.DISABLED.value}:
        record.status = entry.status.value
    record.freshness_max_age_seconds = entry.freshness_max_age_seconds
    record.commercial_use_cases = list(entry.commercial_use_cases)
    record.authorization_expires_at = entry.authorization_expires_at
    record.review_due_at = entry.review_due_at
    record.candidate_origin = entry.candidate_origin
    record.monthly_cost_limit = entry.monthly_cost_limit
    record.extra_metadata = dict(entry.metadata)
    record.updated_at = now


def _sync_capability(
    session: Session,
    manifest: AdapterCapabilityManifest | None,
    now: datetime,
) -> None:
    if manifest is None:
        return
    record = session.get(AdapterCapabilityRecord, (manifest.source_id, manifest.adapter_id))
    if record is None:
        record = AdapterCapabilityRecord(
            source_id=manifest.source_id,
            adapter_id=manifest.adapter_id,
            updated_at=now,
        )
        session.add(record)
    record.adapter_version = manifest.adapter_version
    record.provider_schema_version = manifest.provider_schema_version
    record.modes = sorted(mode.value for mode in manifest.modes)
    record.canonical_output_types = list(manifest.canonical_output_types)
    record.supports_corrections = manifest.supports_corrections
    record.supports_tombstones = manifest.supports_tombstones
    record.supports_retractions = manifest.supports_retractions
    record.max_page_size = manifest.max_page_size
    record.max_window_days = manifest.max_window_days
    record.cost_per_request = manifest.cost_per_request
    record.updated_at = now


def _ensure_health(session: Session, entry: SourceCatalogEntry, now: datetime) -> None:
    if session.get(SourceHealthRecord, entry.source_id) is not None:
        return
    state = (
        FreshnessState.HISTORICAL_ONLY
        if entry.adapter is not None
        and entry.adapter.modes == {CollectionMode.HISTORICAL_BACKFILL}
        else FreshnessState.STALE_REFRESH_QUEUED
    )
    session.add(
        SourceHealthRecord(
            source_id=entry.source_id,
            freshness_state=state.value,
            schema_state=SchemaState.UNKNOWN.value,
            last_attempt_at=None,
            last_success_at=None,
            last_source_record_at=None,
            consecutive_failures=0,
            quota_remaining=None,
            monthly_cost_used=0.0,
            current_backfill_state=None,
            last_error_code=None,
            updated_at=now,
        )
    )


def _change_source_status(
    session: Session,
    source_id: str,
    target: CatalogStatus,
    actor: str,
    now: datetime,
) -> SourceCatalogEntry:
    record = _get_portfolio_record(session, source_id)
    if record.status == CatalogStatus.CANDIDATE.value and target is not CatalogStatus.DISABLED:
        raise SourcePortfolioStateError("catalog candidates cannot execute")
    changed_at = require_aware_utc(now, field_name="now")
    record.status = target.value
    record.updated_at = changed_at
    if target in {CatalogStatus.PAUSED, CatalogStatus.DISABLED}:
        session.execute(
            BackfillPartitionRecord.__table__.update()
            .where(
                BackfillPartitionRecord.source_id == record.source_id,
                BackfillPartitionRecord.state.in_(
                    (BackfillState.PENDING.value, BackfillState.RUNNING.value)
                ),
            )
            .values(state=BackfillState.PAUSED.value, updated_at=changed_at)
        )
        _set_backfill_health(session, record.source_id, BackfillState.PAUSED, changed_at)
    _audit(session, record.source_id, f"source_{target.value}", actor, changed_at)
    session.flush()
    return _to_catalog_entry(session, record)


def _freshness_for_success(
    session: Session,
    source_id: str,
    health: SourceHealthRecord,
    now: datetime,
) -> FreshnessState:
    entry = get_source_portfolio(session, source_id)
    if entry.authorization_expires_at is not None and entry.authorization_expires_at <= now:
        return FreshnessState.AUTHORIZATION_EXPIRED
    if health.schema_state == SchemaState.DRIFTED.value:
        return FreshnessState.SOURCE_UNAVAILABLE
    return FreshnessState.FRESH


def _set_backfill_health(
    session: Session,
    source_id: str,
    state: BackfillState,
    now: datetime,
) -> None:
    health = _get_health_record(session, source_id)
    health.current_backfill_state = state.value
    health.updated_at = now


def _to_catalog_entry(session: Session, record: SourcePortfolioRecord) -> SourceCatalogEntry:
    capability = _capability_record(session, record.source_id)
    return SourceCatalogEntry(
        source_id=record.source_id,
        display_name=record.display_name,
        canonical_url=record.canonical_url,
        category=record.category,
        status=CatalogStatus(record.status),
        freshness_max_age_seconds=record.freshness_max_age_seconds,
        commercial_use_cases=tuple(record.commercial_use_cases),
        adapter=_to_manifest(capability) if capability is not None else None,
        authorization_expires_at=persistence_utc(record.authorization_expires_at),
        review_due_at=persistence_utc(record.review_due_at),
        candidate_origin=record.candidate_origin,
        monthly_cost_limit=record.monthly_cost_limit,
        metadata=record.extra_metadata,
    )


def _to_manifest(record: AdapterCapabilityRecord) -> AdapterCapabilityManifest:
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


def _to_health(record: SourceHealthRecord) -> SourceHealth:
    return SourceHealth(
        source_id=record.source_id,
        freshness_state=FreshnessState(record.freshness_state),
        schema_state=SchemaState(record.schema_state),
        last_attempt_at=persistence_utc(record.last_attempt_at),
        last_success_at=persistence_utc(record.last_success_at),
        last_source_record_at=persistence_utc(record.last_source_record_at),
        consecutive_failures=record.consecutive_failures,
        quota_remaining=record.quota_remaining,
        monthly_cost_used=record.monthly_cost_used,
        current_backfill_state=(
            BackfillState(record.current_backfill_state)
            if record.current_backfill_state is not None
            else None
        ),
        last_error_code=record.last_error_code,
    )


def _get_portfolio_record(session: Session, source_id: str) -> SourcePortfolioRecord:
    record = session.get(SourcePortfolioRecord, source_id.strip())
    if record is None:
        raise SourcePortfolioNotFoundError(source_id)
    return record


def _get_health_record(session: Session, source_id: str) -> SourceHealthRecord:
    record = session.get(SourceHealthRecord, source_id.strip())
    if record is None:
        raise SourcePortfolioNotFoundError(source_id)
    return record


def _capability_record(session: Session, source_id: str) -> AdapterCapabilityRecord | None:
    return session.scalar(
        select(AdapterCapabilityRecord).where(AdapterCapabilityRecord.source_id == source_id)
    )


def _get_partition(session: Session, partition_id: UUID) -> BackfillPartitionRecord:
    record = session.get(BackfillPartitionRecord, partition_id)
    if record is None:
        raise SourcePortfolioNotFoundError(str(partition_id))
    return record


def _audit(
    session: Session,
    source_id: str,
    action: str,
    actor: str,
    occurred_at: datetime,
    *,
    details: dict[str, object] | None = None,
) -> None:
    normalized_actor = _bounded_value(actor, "actor", maximum=200)
    session.add(
        SourcePortfolioAuditRecord(
            id=uuid4(),
            source_id=source_id,
            action=action,
            actor=normalized_actor,
            details=details or {},
            occurred_at=occurred_at,
            note=None,
        )
    )


def _bounded_value(value: str, field_name: str, *, maximum: int = 300) -> str:
    normalized = value.strip()
    if not normalized or len(normalized) > maximum:
        raise ValueError(f"{field_name} must be non-empty and at most {maximum} characters")
    return normalized


def _non_negative(value: float, field_name: str) -> float:
    if value < 0:
        raise ValueError(f"{field_name} cannot be negative")
    return value
