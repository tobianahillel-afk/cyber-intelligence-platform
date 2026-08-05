from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from cip.modules.collection_orchestration.infrastructure.models import (
    CollectionCircuitRecord,
)
from cip.modules.raw_observations.domain.entities import RawObservation
from cip.modules.source_portfolio.application.quality import evaluate_quality
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


@dataclass(frozen=True, slots=True)
class CollectionHealthUpdate:
    source_record_at: datetime | None
    schema_state: SchemaState
    quota_remaining: int | None
    cost: float
    observations: Sequence[RawObservation] | None = None
    not_modified: bool = False
    volume_state: AnomalyState = AnomalyState.NORMAL
    field_population_state: AnomalyState = AnomalyState.NORMAL

    def __post_init__(self) -> None:
        if self.quota_remaining is not None and self.quota_remaining < 0:
            raise ValueError("quota_remaining cannot be negative")
        if self.cost < 0:
            raise ValueError("cost cannot be negative")


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
            cost_window_started_at=_month_start(now),
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
    update: CollectionHealthUpdate,
    *,
    now: datetime,
) -> SourceHealth:
    changed_at = require_aware_utc(now, field_name="now")
    record = get_health_record(session, source_id)
    _roll_cost_window(record, changed_at)
    record.last_attempt_at = changed_at
    record.last_success_at = changed_at
    if update.source_record_at is not None:
        record.last_source_record_at = require_aware_utc(
            update.source_record_at,
            field_name="source_record_at",
        )
    evaluation = (
        evaluate_quality(
            session,
            source_id,
            update.observations,
            not_modified=update.not_modified,
            now=changed_at,
        )
        if update.observations is not None
        else None
    )
    if evaluation is not None:
        record.schema_state = (
            SchemaState.DRIFTED.value
            if update.schema_state is SchemaState.DRIFTED
            or evaluation.schema_state is SchemaState.DRIFTED
            else SchemaState.STABLE.value
        )
        record.volume_state = evaluation.volume_state.value
        record.field_population_state = evaluation.field_population_state.value
    elif not update.not_modified:
        record.schema_state = update.schema_state.value
        record.volume_state = update.volume_state.value
        record.field_population_state = update.field_population_state.value
    record.consecutive_failures = 0
    if update.quota_remaining is not None:
        record.quota_remaining = update.quota_remaining
    record.monthly_cost_used += non_negative(update.cost, "cost")
    record.last_error_code = None
    record.freshness_state = _freshness_state(session, source_id, changed_at).value
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
    _roll_cost_window(record, changed_at)
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
    _roll_cost_window(record, changed_at)
    last_success = persistence_utc(record.last_success_at)
    state = _freshness_state(session, source_id, changed_at)
    if state is FreshnessState.FRESH:
        historical_only = (
            entry.adapter is not None
            and entry.adapter.modes
            == frozenset({CollectionMode.HISTORICAL_BACKFILL})
        )
        if historical_only:
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


def _freshness_state(
    session: Session,
    source_id: str,
    now: datetime,
) -> FreshnessState:
    entry = to_catalog_entry(session, get_portfolio_record(session, source_id))
    record = get_health_record(session, source_id)
    if entry.authorization_expires_at is not None and entry.authorization_expires_at <= now:
        return FreshnessState.AUTHORIZATION_EXPIRED
    if record.quota_remaining == 0:
        return FreshnessState.QUOTA_EXHAUSTED
    capability = capability_record(session, source_id)
    next_cost = capability.cost_per_request if capability is not None else 0.0
    if (
        next_cost > 0
        and entry.monthly_cost_limit is not None
        and record.monthly_cost_used + next_cost > entry.monthly_cost_limit
    ):
        return FreshnessState.COST_BUDGET_EXHAUSTED
    return FreshnessState.FRESH


def _roll_cost_window(record: SourceHealthRecord, now: datetime) -> None:
    current_start = _month_start(now)
    stored_start = persistence_utc(record.cost_window_started_at)
    if stored_start != current_start:
        record.monthly_cost_used = 0.0
        record.cost_window_started_at = current_start


def _month_start(value: datetime) -> datetime:
    current = require_aware_utc(value, field_name="value")
    return datetime(current.year, current.month, 1, tzinfo=UTC)


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
