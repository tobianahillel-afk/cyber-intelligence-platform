from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from cip.modules.incident_intelligence.domain.models import (
    IncidentClaimSnapshot,
    IncidentClaimType,
    IncidentSourceKind,
    IncidentType,
    OrganizationLinkStatus,
)
from cip.modules.incident_intelligence.infrastructure.models import (
    IncidentClaimSnapshotRecord,
)
from cip.modules.organizations.infrastructure.persistence_time import coerce_utc


def latest_incident_claims(
    session: Session,
    incident_id: UUID,
) -> tuple[IncidentClaimSnapshot, ...]:
    rows = list(
        session.scalars(
            select(IncidentClaimSnapshotRecord)
            .where(IncidentClaimSnapshotRecord.incident_id == incident_id)
            .order_by(
                IncidentClaimSnapshotRecord.source_id,
                IncidentClaimSnapshotRecord.source_record_key,
                IncidentClaimSnapshotRecord.modified_at.desc(),
            )
        )
    )
    latest: dict[tuple[str, str], IncidentClaimSnapshotRecord] = {}
    for row in rows:
        latest.setdefault((row.source_id, row.source_record_key), row)
    return tuple(_hydrate(row) for row in latest.values())


def all_incident_claims(
    session: Session,
    incident_id: UUID,
) -> tuple[IncidentClaimSnapshot, ...]:
    return tuple(
        _hydrate(row)
        for row in session.scalars(
            select(IncidentClaimSnapshotRecord)
            .where(IncidentClaimSnapshotRecord.incident_id == incident_id)
            .order_by(IncidentClaimSnapshotRecord.modified_at.desc())
        )
    )


def _hydrate(row: IncidentClaimSnapshotRecord) -> IncidentClaimSnapshot:
    return IncidentClaimSnapshot(
        source_id=row.source_id,
        source_kind=IncidentSourceKind(row.source_kind),
        source_record_key=row.source_record_key,
        source_url=row.source_url,
        incident_key=row.incident_key,
        claim_type=IncidentClaimType(row.claim_type),
        incident_type=IncidentType(row.incident_type),
        title=row.title,
        summary=row.summary,
        claimed_organization_name=row.claimed_organization_name,
        organization_id=row.organization_id,
        organization_link_status=OrganizationLinkStatus(
            row.organization_link_status
        ),
        published_at=coerce_utc(row.published_at),
        modified_at=coerce_utc(row.modified_at),
        occurrence_start_at=(
            coerce_utc(row.occurrence_start_at)
            if row.occurrence_start_at
            else None
        ),
        occurrence_end_at=(
            coerce_utc(row.occurrence_end_at)
            if row.occurrence_end_at
            else None
        ),
        discovered_at=(
            coerce_utc(row.discovered_at)
            if row.discovered_at
            else None
        ),
        confirmed_at=(
            coerce_utc(row.confirmed_at)
            if row.confirmed_at
            else None
        ),
        independence_key=row.independence_key,
        confidence=row.confidence,
        active=row.active,
        historical_only=row.historical_only,
        metadata_only=row.metadata_only,
        supersedes_record_key=row.supersedes_record_key,
    )
