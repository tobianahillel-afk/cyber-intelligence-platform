from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from cip.modules.collection_orchestration.infrastructure.models import (
    CollectionCircuitRecord,
)
from cip.modules.source_portfolio.application.records import (
    bounded_value,
    capability_record,
    get_health_record,
    get_portfolio_record,
    non_negative,
    to_catalog_entry,
    to_health,
)
from cip.modules.source_portfolio.domain.models import (
    AnomalyState,
    BackfillState,
    CollectionMode,
    FreshnessState,
    SchemaState,
    SourceCatalogEntry,
    SourceHealth,
)
from cip.modules.source_portfolio.infrastructure.models import SourceHealthRecord
from cip.modules.source_portfolio.infrastructure.persistence_time import persistence_utc
from cip.shared.kernel.time import require_aware_utc


def ensure_health(session: Session, entry: SourceCatalogEntry, now: datetime) -> None:
    if session.get(SourceHealthRecord, entry.source_id) is not None:
        return
    historical_only = (
        entry.adapter is not None
        and entry.adapter.modes
        == frozenset({CollectionMode.HISTORICAL_BACKFILL})
    )
    state = (
        FreshnessState.HISTORICAL_ONLY
        if historical_only
        else FreshnessState.STALE_REFRESH_QUEUED
    )
    session.add(
        SourceHealthRecord(
            source_id=entry.source_id,
            freshness_state=state.value,
            schema_state=SchemaState.UNKNOWN.value,
            volume_state=AnomalyState.UNKNOWN.value,
            field_population_state=AnomalyState.UNKNOWN.value,
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


def get_source_health(session: Session, source_id: str) -> SourceHealth:
    return _health_projection(session, get_health_record(session, source_id))


def set_backfill_health(
    session: Session,
    source_id: str,
    state: BackfillState | None,
    now: datetime,
) -> None:
    health = get_health_record(session, source_id)
    health.current_backfill_state = state.value if state is not None else None
    health.updated_at = now


def record_collection_success(
    session: Session,
    source_id: str,
    *,
    source_record_at: datetime | None,
    schema_state: SchemaState,
    quota_remaining: int | None,
    cost: float,
    now: datetime,
    volume_state: AnomalyState = AnomalyState.NORMAL,
    field_population_state: AnomalyState = AnomalyState.NORMAL,
) -> SourceHealth:
    changed_at = require_aware_utc(now, field_name="now")
    if quota_remaining is not None and quota_remaining < 0:
        raise ValueError("quota_remaining cannot be negative")
    record = get_health_record(session, source_id)
    record.last_attempt_at = changed_at
    record.last_success_at = changed_at
    if source_record_at is not None:
        record.last_source_record_at = require_aware_utc(
            source_record_at,
            field_name="source_record_at",
        )
    record.schema_state = schema_state.value
    record.volume_state = volume_state.value
    record.field_population_state = field_population_state.value
    record.consecutive_failures = 0
    if quota_remaining is not None:
        record.quota_remaining = quota_remaining
    record.monthly_cost_used += non_negative(cost, "cost")
    record.last_error_code = None
    record.freshness_state = _freshness_for_success(session, source_id, changed_at).value
    record.updated_at = changed_at
    session.flush()
    return _health_projection(session, record)


def record_collection_failure(
    session: Session,
    source_id: str,
    *,
    error_code: str,
    schema_drift: bool,
    now: datetime,
) -> SourceHealth:
    changed_at = require_aware_utc(now, field_name="now")
    record = get_health_record(session, source_id)
    record.last_attempt_at = changed_at
    record.consecutive_failures += 1
    record.last_error_code = bounded_value(error_code, "error_code", maximum=100)
    if schema_drift:
        record.schema_state = SchemaState.DRIFTED.value
    record.freshness_state = FreshnessState.SOURCE_UNAVAILABLE.value
    record.updated_at = changed_at
    session.flush()
    return _health_projection(session, record)


def refresh_freshness(session: Session, source_id: str, *, now: datetime) -> SourceHealth:
    changed_at = require_aware_utc(now, field_name="now")
    entry = to_catalog_entry(session, get_portfolio_record(session, source_id))
    record = get_health_record(session, source_id)
    last_success = persistence_utc(record.last_success_at)
    historical_only = (
        entry.adapter is not None
        and entry.adapter.modes
        == frozenset({CollectionMode.HISTORICAL_BACKFILL})
    )
    if entry.authorization_expires_at is not None and entry.authorization_expires_at <= changed_at:
        state = FreshnessState.AUTHORIZATION_EXPIRED
    elif historical_only:
        state = FreshnessState.HISTORICAL_ONLY
    elif last_success is None:
        state = FreshnessState.STALE_REFRESH_QUEUED
    else:
        age = changed_at - last_success
        maximum = timedelta(seconds=entry.freshness_max_age_seconds)
        state = FreshnessState.FRESH if age <= maximum / 2 else FreshnessState.AGING
        if age > maximum:
            state = FreshnessState.STALE_REFRESH_QUEUED
    record.freshness_state = state.value
    record.updated_at = changed_at
    session.flush()
    return _health_projection(session, record)


def _freshness_for_success(
    session: Session,
    source_id: str,
    now: datetime,
) -> FreshnessState:
    entry = to_catalog_entry(session, get_portfolio_record(session, source_id))
    if entry.authorization_expires_at is not None and entry.authorization_expires_at <= now:
        return FreshnessState.AUTHORIZATION_EXPIRED
    return FreshnessState.FRESH


def _health_projection(session: Session, record: SourceHealthRecord) -> SourceHealth:
    capability = capability_record(session, record.source_id)
    if capability is None:
        circuit_state = "not_applicable"
    else:
        circuit = session.get(
            CollectionCircuitRecord,
            (record.source_id, capability.adapter_id),
        )
        circuit_state = circuit.state if circuit is not None else "closed"
    return to_health(record, circuit_state=circuit_state)
