from __future__ import annotations

from collections import defaultdict
from datetime import datetime

from cip.modules.threat_telemetry.domain.models import (
    IndicatorSnapshot,
    IndicatorState,
    ReconciledIndicator,
    TelemetryRelation,
)

_STATE_PRIORITY = {
    IndicatorState.BENIGN: 90,
    IndicatorState.RETRACTED: 85,
    IndicatorState.SINKHOLED: 80,
    IndicatorState.MALICIOUS: 70,
    IndicatorState.SUSPICIOUS: 60,
    IndicatorState.SHARED_INFRASTRUCTURE: 50,
    IndicatorState.HISTORICAL: 40,
    IndicatorState.EXPIRED: 30,
    IndicatorState.UNKNOWN: 10,
}
_CONFLICTING_STATES = {
    IndicatorState.MALICIOUS,
    IndicatorState.SUSPICIOUS,
    IndicatorState.BENIGN,
    IndicatorState.RETRACTED,
}


def reconcile_indicator_snapshots(
    snapshots: tuple[IndicatorSnapshot, ...],
) -> tuple[ReconciledIndicator, ...]:
    grouped: dict[str, list[IndicatorSnapshot]] = defaultdict(list)
    for snapshot in snapshots:
        grouped[snapshot.indicator_key].append(snapshot)
    return tuple(
        _reconcile_indicator(group)
        for _, group in sorted(grouped.items())
    )


def latest_indicator_snapshots(
    snapshots: tuple[IndicatorSnapshot, ...],
) -> tuple[IndicatorSnapshot, ...]:
    latest: dict[tuple[str, str], IndicatorSnapshot] = {}
    for snapshot in snapshots:
        key = (snapshot.source_id, snapshot.source_record_key)
        current = latest.get(key)
        if current is None or snapshot.modified_at > current.modified_at:
            latest[key] = snapshot
    return tuple(latest.values())


def _reconcile_indicator(
    snapshots: list[IndicatorSnapshot],
) -> ReconciledIndicator:
    current = latest_indicator_snapshots(tuple(snapshots))
    if not current:
        raise ValueError("indicator reconciliation requires at least one snapshot")
    identity = current[0]
    if any(snapshot.indicator_key != identity.indicator_key for snapshot in current):
        raise ValueError("indicator reconciliation cannot mix canonical identities")
    selected = max(
        current,
        key=lambda snapshot: (
            snapshot.source_precedence,
            snapshot.modified_at,
            _STATE_PRIORITY[snapshot.state],
        ),
    )
    active = tuple(snapshot for snapshot in current if snapshot.active)
    observed_states = tuple(
        sorted({snapshot.state for snapshot in current}, key=lambda state: state.value)
    )
    positive_groups = {
        snapshot.independence_key
        for snapshot in active
        if snapshot.is_positive_detection
    }
    return ReconciledIndicator(
        indicator_key=identity.indicator_key,
        indicator_type=identity.indicator_type,
        indicator_value=identity.indicator_value,
        state=selected.state,
        observed_states=observed_states,
        first_seen_at=_minimum_time(
            tuple(snapshot.first_seen_at for snapshot in current)
        ),
        last_seen_at=_maximum_time(
            tuple(snapshot.last_seen_at for snapshot in current)
        ),
        expires_at=_maximum_time(tuple(snapshot.expires_at for snapshot in current)),
        last_updated_at=max(snapshot.modified_at for snapshot in current),
        source_count=len({snapshot.source_id for snapshot in current}),
        independent_source_count=len(positive_groups),
        active=bool(active),
        shared_infrastructure=any(
            snapshot.shared_infrastructure
            or snapshot.state is IndicatorState.SHARED_INFRASTRUCTURE
            for snapshot in current
        ),
        historical_only=all(snapshot.historical_only for snapshot in current),
        has_conflict=len(set(observed_states) & _CONFLICTING_STATES) > 1,
        relations=_merge_relations(current),
    )


def _merge_relations(
    snapshots: tuple[IndicatorSnapshot, ...],
) -> tuple[TelemetryRelation, ...]:
    relations: dict[tuple[str, str], TelemetryRelation] = {}
    for snapshot in snapshots:
        for relation in snapshot.relations:
            key = (relation.relation_type.value, relation.target_key)
            current = relations.get(key)
            if current is None or relation.confidence > current.confidence:
                relations[key] = relation
    return tuple(relations[key] for key in sorted(relations))


def _minimum_time(values: tuple[datetime | None, ...]) -> datetime | None:
    present = tuple(value for value in values if value is not None)
    return min(present) if present else None


def _maximum_time(values: tuple[datetime | None, ...]) -> datetime | None:
    present = tuple(value for value in values if value is not None)
    return max(present) if present else None
