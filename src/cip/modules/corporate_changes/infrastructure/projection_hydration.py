from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from cip.modules.corporate_changes.domain.models import (
    ChangeClaimSnapshot,
    ChangeClaimType,
    ChangeEventType,
    ChangeSourceKind,
    OrganizationLinkStatus,
)
from cip.modules.corporate_changes.infrastructure.models import (
    CorporateChangeClaimSnapshotRecord,
)
from cip.modules.organizations.infrastructure.persistence_time import coerce_utc


def latest_change_claims(
    session: Session,
    event_id: UUID,
) -> tuple[ChangeClaimSnapshot, ...]:
    rows = list(
        session.scalars(
            select(CorporateChangeClaimSnapshotRecord)
            .where(CorporateChangeClaimSnapshotRecord.event_id == event_id)
            .order_by(
                CorporateChangeClaimSnapshotRecord.source_id,
                CorporateChangeClaimSnapshotRecord.source_record_key,
                CorporateChangeClaimSnapshotRecord.modified_at.desc(),
            )
        )
    )
    latest: dict[tuple[str, str], CorporateChangeClaimSnapshotRecord] = {}
    for row in rows:
        latest.setdefault((row.source_id, row.source_record_key), row)
    return tuple(_hydrate(row) for row in latest.values())


def all_change_claims(
    session: Session,
    event_id: UUID,
) -> tuple[ChangeClaimSnapshot, ...]:
    return tuple(
        _hydrate(row)
        for row in session.scalars(
            select(CorporateChangeClaimSnapshotRecord)
            .where(CorporateChangeClaimSnapshotRecord.event_id == event_id)
            .order_by(CorporateChangeClaimSnapshotRecord.modified_at.desc())
        )
    )


def _hydrate(row: CorporateChangeClaimSnapshotRecord) -> ChangeClaimSnapshot:
    return ChangeClaimSnapshot(
        source_id=row.source_id,
        source_kind=ChangeSourceKind(row.source_kind),
        source_record_key=row.source_record_key,
        article_id=row.article_id,
        source_url=row.source_url,
        event_key=row.event_key,
        claim_type=ChangeClaimType(row.claim_type),
        event_type=ChangeEventType(row.event_type),
        title=row.title,
        excerpt=row.excerpt,
        claimed_organization_name=row.claimed_organization_name,
        organization_id=row.organization_id,
        organization_link_status=OrganizationLinkStatus(row.organization_link_status),
        published_at=coerce_utc(row.published_at),
        modified_at=coerce_utc(row.modified_at),
        event_at=coerce_utc(row.event_at) if row.event_at else None,
        expires_at=coerce_utc(row.expires_at) if row.expires_at else None,
        independence_key=row.independence_key,
        syndication_group_key=row.syndication_group_key,
        confidence=row.confidence,
        active=row.active,
        historical_only=row.historical_only,
        metadata_only=row.metadata_only,
        supersedes_record_key=row.supersedes_record_key,
    )
