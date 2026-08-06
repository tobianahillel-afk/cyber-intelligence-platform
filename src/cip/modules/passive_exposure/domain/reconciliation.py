from __future__ import annotations

from collections import defaultdict
from datetime import datetime

from cip.modules.passive_exposure.domain.asset_models import TechnologyObservation
from cip.modules.passive_exposure.domain.enums import (
    AttributionRisk,
    OrganizationLinkStatus,
    PassiveObservationState,
)
from cip.modules.passive_exposure.domain.observation_models import (
    PassiveObservationSnapshot,
)
from cip.modules.passive_exposure.domain.reconciled_models import (
    ObservedService,
    ReconciledOrganizationLink,
    ReconciledPassiveAsset,
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
    history = _latest_revisions(snapshots)
    return _effective_revisions(history)


def _latest_revisions(
    snapshots: tuple[PassiveObservationSnapshot, ...],
) -> tuple[PassiveObservationSnapshot, ...]:
    latest: dict[tuple[str, str], PassiveObservationSnapshot] = {}
    for snapshot in snapshots:
        key = (snapshot.source_id, snapshot.source_record_key)
        current = latest.get(key)
        if current is None or _revision_order(snapshot) > _revision_order(current):
            latest[key] = snapshot
    return tuple(latest[key] for key in sorted(latest))


def _effective_revisions(
    history: tuple[PassiveObservationSnapshot, ...],
) -> tuple[PassiveObservationSnapshot, ...]:
    _validate_supersession_graph(history)
    superseded: set[tuple[str, str]] = set()
    for snapshot in history:
        target = snapshot.supersedes_record_key
        if target is not None and target != snapshot.source_record_key:
            superseded.add((snapshot.source_id, target))
    effective = tuple(
        snapshot
        for snapshot in history
        if (snapshot.source_id, snapshot.source_record_key) not in superseded
    )
    if history and not effective:
        raise ValueError("passive supersession cycle removes every provider record")
    return effective


def _validate_supersession_graph(
    history: tuple[PassiveObservationSnapshot, ...],
) -> None:
    known = {
        (snapshot.source_id, snapshot.source_record_key)
        for snapshot in history
    }
    edges: dict[tuple[str, str], tuple[str, str]] = {}
    for snapshot in history:
        target = snapshot.supersedes_record_key
        if target is None or target == snapshot.source_record_key:
            continue
        destination = (snapshot.source_id, target)
        if destination in known:
            edges[(snapshot.source_id, snapshot.source_record_key)] = destination
    visited: set[tuple[str, str]] = set()
    for start in edges:
        if start in visited:
            continue
        path: list[tuple[str, str]] = []
        active: set[tuple[str, str]] = set()
        node = start
        while node in edges and node not in visited:
            if node in active:
                raise ValueError("passive supersession cycle detected")
            active.add(node)
            path.append(node)
            node = edges[node]
        visited.update(path)


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
    complete_history = tuple(snapshots)
    if not complete_history:
        raise ValueError("passive reconciliation requires at least one snapshot")
    current = _effective_revisions(_latest_revisions(complete_history))
    identity = complete_history[0].asset
    if any(snapshot.asset.key != identity.key for snapshot in complete_history):
        raise ValueError("passive reconciliation cannot mix canonical assets")
    active = _active_snapshots(current, at=at)
    observed_states = _observed_states(complete_history)
    risks = _active_risks(active)
    expiry_snapshots = active or current
    return ReconciledPassiveAsset(
        asset=identity,
        state=_reconciled_state(current, active),
        observed_states=observed_states,
        first_seen_at=min(snapshot.observed_at for snapshot in complete_history),
        last_seen_at=max(snapshot.observed_at for snapshot in complete_history),
        expires_at=_maximum_time(
            tuple(snapshot.expires_at for snapshot in expiry_snapshots)
        ),
        last_updated_at=max(snapshot.modified_at for snapshot in complete_history),
        source_count=len({snapshot.source_id for snapshot in complete_history}),
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


def _active_snapshots(
    snapshots: tuple[PassiveObservationSnapshot, ...],
    *,
    at: datetime,
) -> tuple[PassiveObservationSnapshot, ...]:
    return tuple(snapshot for snapshot in snapshots if _is_active(snapshot, at=at))


def _observed_states(
    snapshots: tuple[PassiveObservationSnapshot, ...],
) -> tuple[PassiveObservationState, ...]:
    return tuple(
        sorted(
            {snapshot.state for snapshot in snapshots},
            key=lambda state: state.value,
        )
    )


def _active_risks(
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


def _reconciled_state(
    current: tuple[PassiveObservationSnapshot, ...],
    active: tuple[PassiveObservationSnapshot, ...],
) -> PassiveObservationState:
    selected = max(active or current, key=_revision_order)
    if selected.state is PassiveObservationState.CURRENT and not active:
        return PassiveObservationState.EXPIRED
    return selected.state


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
