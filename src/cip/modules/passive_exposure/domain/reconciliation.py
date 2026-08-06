from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from cip.modules.passive_exposure.domain.models import (
    AttributionRisk,
    OrganizationLinkStatus,
    PassiveAsset,
    PassiveObservationSnapshot,
    PassiveObservationState,
    TechnologyObservation,
)
from cip.shared.kernel.time import require_aware_utc

_STATE_PRIORITY = {
    PassiveObservationState.DELETED: 90,
    PassiveObservationState.RETRACTED: 85,
    PassiveObservationState.CORRECTED: 80,
    PassiveObservationState.EXPIRED: 70,
    PassiveObservationState.CURRENT: 60,
    PassiveObservationState.HISTORICAL: 40,
    PassiveObservationState.UNKNOWN: 10,
}
_CONFLICTING_STATES = {
    PassiveObservationState.CURRENT,
    PassiveObservationState.CORRECTED,
    PassiveObservationState.RETRACTED,
    PassiveObservationState.DELETED,
}


@dataclass(frozen=True, slots=True)
class ObservedService:
    port: int
    protocol: str


@dataclass(frozen=True, slots=True)
class ReconciledOrganizationLink:
    status: OrganizationLinkStatus
    exact_organization_id: UUID | None
    candidate_organization_ids: tuple[UUID, ...]
    reasons: tuple[str, ...]
    attribution_risks: tuple[AttributionRisk, ...]

    @property
    def requires_review(self) -> bool:
        return self.status in {
            OrganizationLinkStatus.CANDIDATE,
            OrganizationLinkStatus.REVIEW_REQUIRED,
        }


@dataclass(frozen=True, slots=True)
class ReconciledPassiveAsset:
    asset: PassiveAsset
    state: PassiveObservationState
    observed_states: tuple[PassiveObservationState, ...]
    first_seen_at: datetime
    last_seen_at: datetime
    expires_at: datetime | None
    last_updated_at: datetime
    source_count: int
    independent_source_count: int
    active: bool
    historical_only: bool
    has_conflict: bool
    organization_link: ReconciledOrganizationLink
    attribution_risks: tuple[AttributionRisk, ...]
    technologies: tuple[TechnologyObservation, ...]
    services: tuple[ObservedService, ...]

    @property
    def can_support_exposure_conclusion(self) -> bool:
        return False


def reconcile_passive_snapshots(
    snapshots: tuple[PassiveObservationSnapshot, ...],
    *,
    at: datetime,
) -> tuple[ReconciledPassiveAsset, ...]:
    observed_at = require_aware_utc(at, field_name="at")
    grouped: dict[str, list[PassiveObservationSnapshot]] = defaultdict(list)
    for snapshot in snapshots:
        grouped[snapshot.asset.key].append(snapshot)
    return tuple(
        _reconcile_asset(group, at=observed_at)
        for _, group in sorted(grouped.items())
    )


def latest_passive_snapshots(
    snapshots: tuple[PassiveObservationSnapshot, ...],
) -> tuple[PassiveObservationSnapshot, ...]:
    latest: dict[tuple[str, str], PassiveObservationSnapshot] = {}
    for snapshot in snapshots:
        key = (snapshot.source_id, snapshot.source_record_key)
        current = latest.get(key)
        if current is None or _revision_order(snapshot) > _revision_order(current):
            latest[key] = snapshot
    superseded = {
        (snapshot.source_id, snapshot.supersedes_record_key)
        for snapshot in latest.values()
        if snapshot.supersedes_record_key is not None
        and snapshot.supersedes_record_key != snapshot.source_record_key
    }
    return tuple(
        latest[key]
        for key in sorted(latest)
        if key not in superseded
    )


def _revision_order(
    snapshot: PassiveObservationSnapshot,
) -> tuple[datetime, datetime, datetime, int, float, str]:
    return (
        snapshot.modified_at,
        snapshot.published_at,
        snapshot.observed_at,
        _STATE_PRIORITY[snapshot.state],
        snapshot.confidence,
        snapshot.source_url,
    )


def _reconcile_asset(
    snapshots: list[PassiveObservationSnapshot],
    *,
    at: datetime,
) -> ReconciledPassiveAsset:
    current = latest_passive_snapshots(tuple(snapshots))
    if not current:
        raise ValueError("passive reconciliation requires at least one snapshot")
    identity = current[0].asset
    if any(snapshot.asset.key != identity.key for snapshot in current):
        raise ValueError("passive reconciliation cannot mix canonical assets")
    selected = max(current, key=_revision_order)
    active = tuple(snapshot for snapshot in current if _is_active(snapshot, at=at))
    selected_active = max(active, key=_revision_order) if active else None
    expiry_snapshots = active or current
    observed_states = tuple(
        sorted({snapshot.state for snapshot in current}, key=lambda state: state.value)
    )
    state = selected_active.state if selected_active is not None else selected.state
    if state is PassiveObservationState.CURRENT and not active:
        state = PassiveObservationState.EXPIRED
    risks = tuple(
        sorted(
            {
                risk
                for snapshot in active
                for risk in snapshot.organization_link.attribution_risks
            },
            key=lambda risk: risk.value,
        )
    )
    return ReconciledPassiveAsset(
        asset=identity,
        state=state,
        observed_states=observed_states,
        first_seen_at=min(snapshot.observed_at for snapshot in current),
        last_seen_at=max(snapshot.observed_at for snapshot in current),
        expires_at=_maximum_time(
            tuple(snapshot.expires_at for snapshot in expiry_snapshots)
        ),
        last_updated_at=max(snapshot.modified_at for snapshot in current),
        source_count=len({snapshot.source_id for snapshot in current}),
        independent_source_count=len(
            {snapshot.independence_key for snapshot in active}
        ),
        active=bool(active),
        historical_only=not active or all(snapshot.historical_only for snapshot in active),
        has_conflict=len(set(observed_states) & _CONFLICTING_STATES) > 1,
        organization_link=_reconcile_organization_link(active, risks=risks),
        attribution_risks=risks,
        technologies=_merge_technologies(active),
        services=_merge_services(active),
    )


def _reconcile_organization_link(
    snapshots: tuple[PassiveObservationSnapshot, ...],
    *,
    risks: tuple[AttributionRisk, ...],
) -> ReconciledOrganizationLink:
    linked = tuple(
        snapshot.organization_link
        for snapshot in snapshots
        if snapshot.organization_link.organization_id is not None
        and snapshot.organization_link.status is not OrganizationLinkStatus.REJECTED
    )
    linked_ids = tuple(
        sorted(
            {link.organization_id for link in linked if link.organization_id is not None},
            key=str,
        )
    )
    exact_ids = {
        link.organization_id
        for link in linked
        if link.status is OrganizationLinkStatus.EXACT
        and link.organization_id is not None
    }
    reasons = _merge_text(tuple(reason for link in linked for reason in link.reasons))
    if len(exact_ids) == 1 and len(linked_ids) == 1 and not risks:
        exact_id = next(iter(exact_ids))
        return ReconciledOrganizationLink(
            status=OrganizationLinkStatus.EXACT,
            exact_organization_id=exact_id,
            candidate_organization_ids=(),
            reasons=reasons,
            attribution_risks=(),
        )
    if linked_ids:
        status = (
            OrganizationLinkStatus.REVIEW_REQUIRED
            if risks or len(linked_ids) > 1 or len(exact_ids) > 1
            else OrganizationLinkStatus.CANDIDATE
        )
        return ReconciledOrganizationLink(
            status=status,
            exact_organization_id=None,
            candidate_organization_ids=linked_ids,
            reasons=reasons,
            attribution_risks=risks,
        )
    return ReconciledOrganizationLink(
        status=OrganizationLinkStatus.UNRESOLVED,
        exact_organization_id=None,
        candidate_organization_ids=(),
        reasons=(),
        attribution_risks=risks,
    )


def _merge_technologies(
    snapshots: tuple[PassiveObservationSnapshot, ...],
) -> tuple[TechnologyObservation, ...]:
    values: dict[tuple[str, str, str, str], TechnologyObservation] = {}
    for snapshot in snapshots:
        technology = snapshot.technology
        if technology is None:
            continue
        key = (
            technology.evidence_level.value,
            technology.product_name or "",
            technology.product_version or "",
            technology.component_name or "",
        )
        values[key] = technology
    return tuple(values[key] for key in sorted(values))


def _merge_services(
    snapshots: tuple[PassiveObservationSnapshot, ...],
) -> tuple[ObservedService, ...]:
    services: set[tuple[int, str]] = set()
    for snapshot in snapshots:
        if snapshot.port is None or snapshot.protocol is None:
            continue
        services.add((snapshot.port, snapshot.protocol))
    return tuple(
        ObservedService(port=port, protocol=protocol)
        for port, protocol in sorted(services)
    )


def _is_active(snapshot: PassiveObservationSnapshot, *, at: datetime) -> bool:
    if not snapshot.active:
        return False
    return snapshot.expires_at is None or snapshot.expires_at > at


def _maximum_time(values: tuple[datetime | None, ...]) -> datetime | None:
    present = tuple(value for value in values if value is not None)
    return max(present) if present else None


def _merge_text(values: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(value for value in values if value))
