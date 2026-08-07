from __future__ import annotations

from datetime import datetime
from uuid import NAMESPACE_URL, UUID, uuid5

from sqlalchemy import select
from sqlalchemy.orm import Session

from cip.modules.corporate_changes.domain.models import (
    ChangeClaimSnapshot,
    ChangeServiceMapping,
)
from cip.modules.corporate_changes.domain.reconciliation import reconcile_change_claims
from cip.modules.corporate_changes.infrastructure.models import (
    CorporateChangeClaimSnapshotRecord,
    CorporateChangeEventRecord,
    CorporateChangeServiceMappingRecord,
)
from cip.modules.corporate_changes.infrastructure.projection_hydration import (
    latest_change_claims,
)
from cip.modules.corporate_changes.infrastructure.projection_payloads import (
    change_claim_digest,
)
from cip.shared.kernel.time import require_aware_utc


def persist_change_claims(
    session: Session,
    claims: tuple[ChangeClaimSnapshot, ...],
    *,
    now: datetime,
) -> tuple[UUID, ...]:
    if not claims:
        return ()
    persisted_at = require_aware_utc(now, field_name="now")
    touched: set[UUID] = set()
    for claim in claims:
        event = _resolve_event(session, claim, now=persisted_at)
        _insert_claim_snapshot(session, event.id, claim, now=persisted_at)
        touched.add(event.id)
    for event_id in touched:
        _refresh_event(session, event_id, now=persisted_at)
    session.flush()
    return tuple(sorted(touched, key=str))


def persist_service_mappings(
    session: Session,
    event_id: UUID,
    mappings: tuple[ChangeServiceMapping, ...],
    *,
    now: datetime,
) -> tuple[UUID, ...]:
    persisted_at = require_aware_utc(now, field_name="now")
    event = session.get(CorporateChangeEventRecord, event_id)
    if event is None:
        raise ValueError("change event does not exist")
    ids: list[UUID] = []
    for mapping in mappings:
        if mapping.event_key != event.event_key:
            raise ValueError("service mapping event_key does not match event")
        existing = session.scalar(
            select(CorporateChangeServiceMappingRecord).where(
                CorporateChangeServiceMappingRecord.event_id == event_id,
                CorporateChangeServiceMappingRecord.service_family
                == mapping.service_family,
            )
        )
        if existing is None:
            existing = CorporateChangeServiceMappingRecord(
                id=uuid5(
                    NAMESPACE_URL,
                    f"change-service:{event.event_key}:{mapping.service_family}",
                ),
                event_id=event_id,
                service_family=mapping.service_family,
                rationale=mapping.rationale,
                confidence=mapping.confidence,
                created_at=persisted_at,
            )
            session.add(existing)
        else:
            existing.rationale = mapping.rationale
            existing.confidence = mapping.confidence
        ids.append(existing.id)
    session.flush()
    return tuple(ids)


def _resolve_event(
    session: Session,
    claim: ChangeClaimSnapshot,
    *,
    now: datetime,
) -> CorporateChangeEventRecord:
    existing = session.scalar(
        select(CorporateChangeEventRecord).where(
            CorporateChangeEventRecord.event_key == claim.event_key
        )
    )
    if existing is not None:
        return existing
    record = CorporateChangeEventRecord(
        id=uuid5(NAMESPACE_URL, f"corporate-change:{claim.event_key}"),
        event_key=claim.event_key,
        event_type=claim.event_type.value,
        title=claim.title,
        excerpt=claim.excerpt,
        status="under_review",
        organization_id=claim.organization_id,
        organization_link_status=claim.organization_link_status.value,
        event_at=claim.event_at,
        first_published_at=claim.published_at,
        last_updated_at=claim.modified_at,
        claim_count=1,
        independent_source_count=1,
        officially_confirmed=claim.is_official_confirmation,
        has_dispute=False,
        has_correction=False,
        has_retraction=False,
        historical_only=claim.historical_only,
        created_at=now,
        updated_at=now,
    )
    session.add(record)
    session.flush()
    return record


def _insert_claim_snapshot(
    session: Session,
    event_id: UUID,
    claim: ChangeClaimSnapshot,
    *,
    now: datetime,
) -> CorporateChangeClaimSnapshotRecord:
    snapshot_key = change_claim_digest(claim)
    existing = session.scalar(
        select(CorporateChangeClaimSnapshotRecord).where(
            CorporateChangeClaimSnapshotRecord.snapshot_key == snapshot_key
        )
    )
    if existing is not None:
        if existing.event_id != event_id:
            raise ValueError("change claim snapshot cannot move between events")
        return existing
    record = CorporateChangeClaimSnapshotRecord(
        id=uuid5(NAMESPACE_URL, f"corporate-change-claim:{snapshot_key}"),
        event_id=event_id,
        snapshot_key=snapshot_key,
        source_id=claim.source_id,
        source_kind=claim.source_kind.value,
        source_record_key=claim.source_record_key,
        article_id=claim.article_id,
        source_url=claim.source_url,
        event_key=claim.event_key,
        claim_type=claim.claim_type.value,
        event_type=claim.event_type.value,
        title=claim.title,
        excerpt=claim.excerpt,
        claimed_organization_name=claim.claimed_organization_name,
        organization_id=claim.organization_id,
        organization_link_status=claim.organization_link_status.value,
        published_at=claim.published_at,
        modified_at=claim.modified_at,
        event_at=claim.event_at,
        expires_at=claim.expires_at,
        independence_key=claim.independence_key or claim.source_id,
        syndication_group_key=claim.syndication_group_key,
        confidence=claim.confidence,
        active=claim.active,
        historical_only=claim.historical_only,
        metadata_only=claim.metadata_only,
        supersedes_record_key=claim.supersedes_record_key,
        created_at=now,
    )
    session.add(record)
    session.flush()
    return record


def _refresh_event(session: Session, event_id: UUID, *, now: datetime) -> None:
    record = session.get(CorporateChangeEventRecord, event_id)
    if record is None:
        raise ValueError("change event disappeared during reconciliation")
    claims = latest_change_claims(session, event_id)
    reconciled = reconcile_change_claims(claims, now=now)[0]
    record.event_type = reconciled.event_type.value
    record.title = reconciled.title
    record.excerpt = reconciled.excerpt
    record.status = reconciled.status.value
    record.organization_id = reconciled.organization_id
    record.organization_link_status = reconciled.organization_link_status.value
    record.event_at = reconciled.event_at
    record.first_published_at = reconciled.first_published_at
    record.last_updated_at = reconciled.last_updated_at
    record.claim_count = reconciled.claim_count
    record.independent_source_count = reconciled.independent_source_count
    record.officially_confirmed = reconciled.officially_confirmed
    record.has_dispute = reconciled.has_dispute
    record.has_correction = reconciled.has_correction
    record.has_retraction = reconciled.has_retraction
    record.historical_only = reconciled.historical_only
    record.updated_at = now
