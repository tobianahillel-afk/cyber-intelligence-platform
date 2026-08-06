from __future__ import annotations

from datetime import datetime
from uuid import NAMESPACE_URL, UUID, uuid5

from sqlalchemy import select
from sqlalchemy.orm import Session

from cip.modules.passive_exposure.domain.models import (
    OrganizationLinkStatus,
    PassiveObservationSnapshot,
)
from cip.modules.passive_exposure.domain.reconciliation import (
    reconcile_passive_snapshots,
)
from cip.modules.passive_exposure.infrastructure.models import (
    PassiveAssetRecord,
    PassiveObservationSnapshotRecord,
    PassiveTechnologyRecord,
)
from cip.modules.passive_exposure.infrastructure.projection_hydration import (
    latest_passive_snapshots,
)
from cip.modules.passive_exposure.infrastructure.projection_payloads import (
    encode_text_values,
    encode_uuid_values,
    passive_snapshot_digest,
    passive_technology_digest,
)
from cip.shared.kernel.time import require_aware_utc


def persist_passive_snapshots(
    session: Session,
    snapshots: tuple[PassiveObservationSnapshot, ...],
    *,
    now: datetime,
) -> tuple[UUID, ...]:
    if not snapshots:
        return ()
    _validate_batch_source_assets(snapshots)
    persisted_at = require_aware_utc(now, field_name="now")
    touched: set[UUID] = set()
    for snapshot in snapshots:
        asset_id = _passive_asset_id(snapshot)
        _validate_source_record_asset(session, asset_id, snapshot)
        asset = _resolve_asset(session, snapshot, now=persisted_at)
        _insert_snapshot(session, asset.id, snapshot, now=persisted_at)
        touched.add(asset.id)
    for asset_id in touched:
        _refresh_asset(session, asset_id, now=persisted_at)
    session.flush()
    return tuple(sorted(touched, key=str))


def _passive_asset_id(snapshot: PassiveObservationSnapshot) -> UUID:
    return uuid5(NAMESPACE_URL, f"passive-asset:{snapshot.asset.key}")


def _validate_batch_source_assets(
    snapshots: tuple[PassiveObservationSnapshot, ...],
) -> None:
    assignments: dict[tuple[str, str], UUID] = {}
    for snapshot in snapshots:
        key = (snapshot.source_id, snapshot.source_record_key)
        asset_id = _passive_asset_id(snapshot)
        assigned = assignments.get(key)
        if assigned is not None and assigned != asset_id:
            raise ValueError("one source record cannot reference multiple passive assets")
        assignments[key] = asset_id
    for snapshot in snapshots:
        target = snapshot.supersedes_record_key
        if target is None or target == snapshot.source_record_key:
            continue
        target_asset_id = assignments.get((snapshot.source_id, target))
        if target_asset_id is not None and target_asset_id != _passive_asset_id(snapshot):
            raise ValueError("a supersession target must reference the same passive asset")


def _validate_source_record_asset(
    session: Session,
    asset_id: UUID,
    snapshot: PassiveObservationSnapshot,
) -> None:
    record_keys = [snapshot.source_record_key]
    target = snapshot.supersedes_record_key
    if target is not None and target != snapshot.source_record_key:
        record_keys.append(target)
    existing_asset_ids = set(
        session.scalars(
            select(PassiveObservationSnapshotRecord.asset_id).where(
                PassiveObservationSnapshotRecord.source_id == snapshot.source_id,
                PassiveObservationSnapshotRecord.source_record_key.in_(record_keys),
            )
        )
    )
    if any(existing_asset_id != asset_id for existing_asset_id in existing_asset_ids):
        raise ValueError("source record ownership conflicts with the canonical passive asset")


def _resolve_asset(
    session: Session,
    snapshot: PassiveObservationSnapshot,
    *,
    now: datetime,
) -> PassiveAssetRecord:
    existing = session.scalar(
        select(PassiveAssetRecord).where(
            PassiveAssetRecord.asset_key == snapshot.asset.key
        )
    )
    if existing is not None:
        return existing
    link = snapshot.organization_link
    candidate_ids = (
        (link.organization_id,)
        if link.organization_id is not None
        and link.status in {
            OrganizationLinkStatus.CANDIDATE,
            OrganizationLinkStatus.REVIEW_REQUIRED,
        }
        else ()
    )
    record = PassiveAssetRecord(
        id=_passive_asset_id(snapshot),
        asset_key=snapshot.asset.key,
        asset_kind=snapshot.asset.kind.value,
        asset_value=snapshot.asset.value,
        state=snapshot.state.value,
        observed_states=snapshot.state.value,
        first_seen_at=snapshot.observed_at,
        last_seen_at=snapshot.observed_at,
        expires_at=snapshot.expires_at,
        last_updated_at=snapshot.modified_at,
        source_count=1,
        independent_source_count=1 if snapshot.active else 0,
        active=snapshot.active,
        historical_only=snapshot.historical_only,
        has_conflict=False,
        organization_link_status=link.status.value,
        exact_organization_id=(
            link.organization_id
            if link.status is OrganizationLinkStatus.EXACT
            else None
        ),
        candidate_organization_ids=encode_uuid_values(candidate_ids),
        organization_link_reasons=encode_text_values(link.reasons),
        attribution_risks=encode_text_values(
            tuple(risk.value for risk in link.attribution_risks)
        ),
        created_at=now,
        updated_at=now,
    )
    session.add(record)
    session.flush()
    return record


def _insert_snapshot(
    session: Session,
    asset_id: UUID,
    snapshot: PassiveObservationSnapshot,
    *,
    now: datetime,
) -> PassiveObservationSnapshotRecord:
    snapshot_key = passive_snapshot_digest(snapshot)
    existing = session.scalar(
        select(PassiveObservationSnapshotRecord).where(
            PassiveObservationSnapshotRecord.snapshot_key == snapshot_key
        )
    )
    if existing is not None:
        if existing.asset_id != asset_id:
            raise ValueError("passive snapshot cannot move between assets")
        return existing
    link = snapshot.organization_link
    record = PassiveObservationSnapshotRecord(
        id=uuid5(NAMESPACE_URL, f"passive-observation:{snapshot_key}"),
        asset_id=asset_id,
        snapshot_key=snapshot_key,
        source_id=snapshot.source_id,
        source_record_key=snapshot.source_record_key,
        source_url=snapshot.source_url,
        asset_kind=snapshot.asset.kind.value,
        asset_value=snapshot.asset.value,
        observation_kind=snapshot.observation_kind.value,
        state=snapshot.state.value,
        observed_at=snapshot.observed_at,
        published_at=snapshot.published_at,
        modified_at=snapshot.modified_at,
        expires_at=snapshot.expires_at,
        independence_key=snapshot.independence_key or snapshot.source_id,
        confidence=snapshot.confidence,
        organization_id=link.organization_id,
        organization_link_status=link.status.value,
        organization_link_method=link.method.value,
        organization_link_confidence=link.confidence,
        organization_link_reasons=encode_text_values(link.reasons),
        attribution_risks=encode_text_values(
            tuple(risk.value for risk in link.attribution_risks)
        ),
        port=snapshot.port,
        protocol=snapshot.protocol,
        active=snapshot.active,
        historical_only=snapshot.historical_only,
        metadata_only=snapshot.metadata_only,
        passive_only=snapshot.passive_only,
        active_probe_performed=snapshot.active_probe_performed,
        credentials_used=snapshot.credentials_used,
        access_control_bypassed=snapshot.access_control_bypassed,
        exploit_attempted=snapshot.exploit_attempted,
        direct_validation_performed=snapshot.direct_validation_performed,
        vulnerability_applicability_assessed=(
            snapshot.vulnerability_applicability_assessed
        ),
        exposure_verified=snapshot.exposure_verified,
        supersedes_record_key=snapshot.supersedes_record_key,
        created_at=now,
    )
    session.add(record)
    session.flush()
    _insert_technology(session, record.id, snapshot_key, snapshot)
    return record


def _insert_technology(
    session: Session,
    snapshot_id: UUID,
    snapshot_key: str,
    snapshot: PassiveObservationSnapshot,
) -> None:
    technology = snapshot.technology
    if technology is None:
        return
    key = passive_technology_digest(snapshot_key, technology)
    session.add(
        PassiveTechnologyRecord(
            id=uuid5(NAMESPACE_URL, f"passive-technology:{key}"),
            snapshot_id=snapshot_id,
            technology_key=key,
            evidence_level=technology.evidence_level.value,
            product_name=technology.product_name,
            product_version=technology.product_version,
            component_name=technology.component_name,
        )
    )
    session.flush()


def _refresh_asset(session: Session, asset_id: UUID, *, now: datetime) -> None:
    record = session.get(PassiveAssetRecord, asset_id)
    if record is None:
        raise ValueError("passive asset disappeared during reconciliation")
    snapshots = latest_passive_snapshots(session, asset_id)
    reconciled = reconcile_passive_snapshots(snapshots, at=now)[0]
    link = reconciled.organization_link
    record.asset_kind = reconciled.asset.kind.value
    record.asset_value = reconciled.asset.value
    record.state = reconciled.state.value
    record.observed_states = ",".join(state.value for state in reconciled.observed_states)
    record.first_seen_at = reconciled.first_seen_at
    record.last_seen_at = reconciled.last_seen_at
    record.expires_at = reconciled.expires_at
    record.last_updated_at = reconciled.last_updated_at
    record.source_count = reconciled.source_count
    record.independent_source_count = reconciled.independent_source_count
    record.active = reconciled.active
    record.historical_only = reconciled.historical_only
    record.has_conflict = reconciled.has_conflict
    record.organization_link_status = link.status.value
    record.exact_organization_id = link.exact_organization_id
    record.candidate_organization_ids = encode_uuid_values(
        link.candidate_organization_ids
    )
    record.organization_link_reasons = encode_text_values(link.reasons)
    record.attribution_risks = encode_text_values(
        tuple(risk.value for risk in reconciled.attribution_risks)
    )
    record.updated_at = now
