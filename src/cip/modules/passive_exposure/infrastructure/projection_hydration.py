from __future__ import annotations

from uuid import UUID

from sqlalchemy import case, select
from sqlalchemy.orm import Session

from cip.modules.passive_exposure.domain.models import (
    AttributionRisk,
    OrganizationLink,
    OrganizationLinkMethod,
    OrganizationLinkStatus,
    PassiveAsset,
    PassiveAssetKind,
    PassiveObservationKind,
    PassiveObservationSnapshot,
    PassiveObservationState,
    TechnologyEvidenceLevel,
    TechnologyObservation,
)
from cip.modules.passive_exposure.domain.reconciliation import (
    latest_passive_snapshots as select_latest_passive_snapshots,
)
from cip.modules.passive_exposure.infrastructure.models import (
    PassiveObservationSnapshotRecord,
    PassiveTechnologyRecord,
)
from cip.modules.passive_exposure.infrastructure.persistence_time import (
    normalize_optional_utc,
    normalize_utc,
)
from cip.modules.passive_exposure.infrastructure.projection_payloads import (
    decode_text_values,
)

_STATE_PRIORITY = {
    PassiveObservationState.DELETED.value: 90,
    PassiveObservationState.RETRACTED.value: 85,
    PassiveObservationState.CORRECTED.value: 80,
    PassiveObservationState.EXPIRED.value: 70,
    PassiveObservationState.CURRENT.value: 60,
    PassiveObservationState.HISTORICAL.value: 40,
    PassiveObservationState.UNKNOWN.value: 10,
}


def latest_passive_snapshots(
    session: Session,
    asset_id: UUID,
) -> tuple[PassiveObservationSnapshot, ...]:
    state_priority = case(
        _STATE_PRIORITY,
        value=PassiveObservationSnapshotRecord.state,
        else_=0,
    )
    records = tuple(
        session.scalars(
            select(PassiveObservationSnapshotRecord)
            .where(PassiveObservationSnapshotRecord.asset_id == asset_id)
            .order_by(
                PassiveObservationSnapshotRecord.modified_at.desc(),
                PassiveObservationSnapshotRecord.published_at.desc(),
                PassiveObservationSnapshotRecord.observed_at.desc(),
                state_priority.desc(),
                PassiveObservationSnapshotRecord.confidence.desc(),
                PassiveObservationSnapshotRecord.source_url.desc(),
                PassiveObservationSnapshotRecord.snapshot_key.desc(),
            )
        )
    )
    latest: dict[tuple[str, str], PassiveObservationSnapshotRecord] = {}
    for record in records:
        latest.setdefault((record.source_id, record.source_record_key), record)
    technologies = _technologies_by_snapshot(
        session,
        tuple(record.id for record in latest.values()),
    )
    hydrated = tuple(
        _to_domain(latest[key], technologies.get(latest[key].id))
        for key in sorted(latest)
    )
    return select_latest_passive_snapshots(hydrated)


def _technologies_by_snapshot(
    session: Session,
    snapshot_ids: tuple[UUID, ...],
) -> dict[UUID, TechnologyObservation]:
    if not snapshot_ids:
        return {}
    records = session.scalars(
        select(PassiveTechnologyRecord).where(
            PassiveTechnologyRecord.snapshot_id.in_(snapshot_ids)
        )
    )
    return {
        record.snapshot_id: TechnologyObservation(
            evidence_level=TechnologyEvidenceLevel(record.evidence_level),
            product_name=record.product_name,
            product_version=record.product_version,
            component_name=record.component_name,
        )
        for record in records
    }


def _to_domain(
    record: PassiveObservationSnapshotRecord,
    technology: TechnologyObservation | None,
) -> PassiveObservationSnapshot:
    return PassiveObservationSnapshot(
        source_id=record.source_id,
        source_record_key=record.source_record_key,
        source_url=record.source_url,
        asset=PassiveAsset(
            kind=PassiveAssetKind(record.asset_kind),
            value=record.asset_value,
        ),
        observation_kind=PassiveObservationKind(record.observation_kind),
        state=PassiveObservationState(record.state),
        observed_at=normalize_utc(record.observed_at),
        published_at=normalize_utc(record.published_at),
        modified_at=normalize_utc(record.modified_at),
        confidence=record.confidence,
        organization_link=OrganizationLink(
            status=OrganizationLinkStatus(record.organization_link_status),
            method=OrganizationLinkMethod(record.organization_link_method),
            confidence=record.organization_link_confidence,
            organization_id=record.organization_id,
            reasons=decode_text_values(record.organization_link_reasons),
            attribution_risks=tuple(
                AttributionRisk(value)
                for value in decode_text_values(record.attribution_risks)
            ),
        ),
        expires_at=normalize_optional_utc(record.expires_at),
        independence_key=record.independence_key,
        technology=technology,
        port=record.port,
        protocol=record.protocol,
        active=record.active,
        historical_only=record.historical_only,
        metadata_only=record.metadata_only,
        passive_only=record.passive_only,
        active_probe_performed=record.active_probe_performed,
        credentials_used=record.credentials_used,
        access_control_bypassed=record.access_control_bypassed,
        exploit_attempted=record.exploit_attempted,
        direct_validation_performed=record.direct_validation_performed,
        vulnerability_applicability_assessed=(
            record.vulnerability_applicability_assessed
        ),
        exposure_verified=record.exposure_verified,
        supersedes_record_key=record.supersedes_record_key,
    )
