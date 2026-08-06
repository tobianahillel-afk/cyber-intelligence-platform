from __future__ import annotations

from datetime import datetime
from uuid import NAMESPACE_URL, UUID, uuid5

from sqlalchemy import select
from sqlalchemy.orm import Session

from cip.modules.incident_intelligence.domain.models import IncidentClaimSnapshot
from cip.modules.incident_intelligence.domain.reconciliation import (
    reconcile_incident_claims,
)
from cip.modules.incident_intelligence.infrastructure.models import (
    IncidentClaimSnapshotRecord,
    IncidentRecord,
)
from cip.modules.incident_intelligence.infrastructure.projection_hydration import (
    latest_incident_claims,
)
from cip.modules.incident_intelligence.infrastructure.projection_payloads import (
    incident_claim_digest,
)
from cip.shared.kernel.time import require_aware_utc


def persist_incident_claims(
    session: Session,
    claims: tuple[IncidentClaimSnapshot, ...],
    *,
    now: datetime,
) -> tuple[UUID, ...]:
    if not claims:
        return ()
    persisted_at = require_aware_utc(now, field_name="now")
    touched: set[UUID] = set()
    for claim in claims:
        incident = _resolve_incident(session, claim, now=persisted_at)
        _insert_claim_snapshot(
            session,
            incident.id,
            claim,
            now=persisted_at,
        )
        touched.add(incident.id)
    for incident_id in touched:
        _refresh_incident(session, incident_id, now=persisted_at)
    session.flush()
    return tuple(sorted(touched, key=str))


def _resolve_incident(
    session: Session,
    claim: IncidentClaimSnapshot,
    *,
    now: datetime,
) -> IncidentRecord:
    existing = session.scalar(
        select(IncidentRecord).where(
            IncidentRecord.incident_key == claim.incident_key
        )
    )
    if existing is not None:
        return existing
    record = IncidentRecord(
        id=uuid5(NAMESPACE_URL, f"incident:{claim.incident_key}"),
        incident_key=claim.incident_key,
        incident_type=claim.incident_type.value,
        title=claim.title,
        summary=claim.summary,
        status="under_review",
        organization_id=claim.organization_id,
        organization_link_status=claim.organization_link_status.value,
        occurrence_start_at=claim.occurrence_start_at,
        occurrence_end_at=claim.occurrence_end_at,
        discovered_at=claim.discovered_at,
        first_published_at=claim.published_at,
        confirmed_at=claim.confirmed_at,
        last_updated_at=claim.modified_at,
        claim_count=1,
        independent_source_count=1,
        officially_confirmed=claim.is_official_confirmation,
        has_denial=False,
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
    incident_id: UUID,
    claim: IncidentClaimSnapshot,
    *,
    now: datetime,
) -> IncidentClaimSnapshotRecord:
    snapshot_key = incident_claim_digest(claim)
    existing = session.scalar(
        select(IncidentClaimSnapshotRecord).where(
            IncidentClaimSnapshotRecord.snapshot_key == snapshot_key
        )
    )
    if existing is not None:
        if existing.incident_id != incident_id:
            raise ValueError("incident claim snapshot cannot move between incidents")
        return existing
    record = IncidentClaimSnapshotRecord(
        id=uuid5(NAMESPACE_URL, f"incident-claim:{snapshot_key}"),
        incident_id=incident_id,
        snapshot_key=snapshot_key,
        source_id=claim.source_id,
        source_kind=claim.source_kind.value,
        source_record_key=claim.source_record_key,
        source_url=claim.source_url,
        incident_key=claim.incident_key,
        claim_type=claim.claim_type.value,
        incident_type=claim.incident_type.value,
        title=claim.title,
        summary=claim.summary,
        claimed_organization_name=claim.claimed_organization_name,
        organization_id=claim.organization_id,
        organization_link_status=claim.organization_link_status.value,
        published_at=claim.published_at,
        modified_at=claim.modified_at,
        occurrence_start_at=claim.occurrence_start_at,
        occurrence_end_at=claim.occurrence_end_at,
        discovered_at=claim.discovered_at,
        confirmed_at=claim.confirmed_at,
        independence_key=claim.independence_key or claim.source_id,
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


def _refresh_incident(
    session: Session,
    incident_id: UUID,
    *,
    now: datetime,
) -> None:
    record = session.get(IncidentRecord, incident_id)
    if record is None:
        raise ValueError("incident disappeared during reconciliation")
    claims = latest_incident_claims(session, incident_id)
    reconciled = reconcile_incident_claims(claims)[0]
    record.incident_type = reconciled.incident_type.value
    record.title = reconciled.title
    record.summary = reconciled.summary
    record.status = reconciled.status.value
    record.organization_id = reconciled.organization_id
    record.organization_link_status = reconciled.organization_link_status.value
    record.occurrence_start_at = reconciled.occurrence_start_at
    record.occurrence_end_at = reconciled.occurrence_end_at
    record.discovered_at = reconciled.discovered_at
    record.first_published_at = reconciled.first_published_at
    record.confirmed_at = reconciled.confirmed_at
    record.last_updated_at = reconciled.last_updated_at
    record.claim_count = reconciled.claim_count
    record.independent_source_count = reconciled.independent_source_count
    record.officially_confirmed = reconciled.officially_confirmed
    record.has_denial = reconciled.has_denial
    record.has_retraction = reconciled.has_retraction
    record.historical_only = reconciled.historical_only
    record.updated_at = now
