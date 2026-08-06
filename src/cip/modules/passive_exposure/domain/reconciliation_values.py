from __future__ import annotations

from datetime import datetime

from cip.modules.passive_exposure.domain.enums import (
    AttributionRisk,
    PassiveObservationState,
)
from cip.modules.passive_exposure.domain.observation_models import (
    PassiveObservationSnapshot,
)


def active_snapshots(
    snapshots: tuple[PassiveObservationSnapshot, ...],
    *,
    at: datetime,
) -> tuple[PassiveObservationSnapshot, ...]:
    return tuple(snapshot for snapshot in snapshots if _is_active(snapshot, at=at))


def observed_states(
    snapshots: tuple[PassiveObservationSnapshot, ...],
) -> tuple[PassiveObservationState, ...]:
    return tuple(
        sorted(
            {snapshot.state for snapshot in snapshots},
            key=lambda state: state.value,
        )
    )


def active_risks(
    snapshots: tuple[PassiveObservationSnapshot, ...],
) -> tuple[AttributionRisk, ...]:
    return tuple(
        sorted(
            {
                risk
                for snapshot in snapshots
                for risk in snapshot.organization_link.attribution_risks
            },
            key=lambda risk: risk.value,
        )
    )


def maximum_time(values: tuple[datetime | None, ...]) -> datetime | None:
    present = tuple(value for value in values if value is not None)
    return max(present) if present else None


def _is_active(snapshot: PassiveObservationSnapshot, *, at: datetime) -> bool:
    if not snapshot.active:
        return False
    return snapshot.expires_at is None or snapshot.expires_at > at
