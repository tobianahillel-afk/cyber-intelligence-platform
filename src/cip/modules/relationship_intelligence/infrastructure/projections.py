from __future__ import annotations

from datetime import datetime
from uuid import NAMESPACE_URL, UUID, uuid5

from sqlalchemy import select
from sqlalchemy.orm import Session

from cip.modules.relationship_intelligence.domain.models import (
    RelationshipContext,
    RelationshipEvidenceSnapshot,
)
from cip.modules.relationship_intelligence.domain.reconciliation import (
    reconcile_relationship_evidence,
)
from cip.modules.relationship_intelligence.infrastructure.models import (
    BusinessRelationshipRecord,
    RelationshipContextRecord,
    RelationshipEvidenceSnapshotRecord,
)
from cip.modules.relationship_intelligence.infrastructure.projection_hydration import (
    latest_relationship_evidence,
)
from cip.modules.relationship_intelligence.infrastructure.projection_payloads import (
    relationship_evidence_digest,
)
from cip.shared.kernel.time import require_aware_utc


def persist_relationship_evidence(
    session: Session,
    evidence: tuple[RelationshipEvidenceSnapshot, ...],
    *,
    now: datetime,
) -> tuple[UUID, ...]:
    if not evidence:
        return ()
    persisted_at = require_aware_utc(now, field_name="now")
    touched: set[UUID] = set()
    for snapshot in evidence:
        relationship = _resolve_relationship(session, snapshot, now=persisted_at)
        _insert_evidence_snapshot(session, relationship.id, snapshot, now=persisted_at)
        touched.add(relationship.id)
    for relationship_id in touched:
        _refresh_relationship(session, relationship_id, now=persisted_at)
    session.flush()
    return tuple(sorted(touched, key=str))


def persist_relationship_contexts(
    session: Session,
    relationship_id: UUID,
    contexts: tuple[RelationshipContext, ...],
    *,
    now: datetime,
) -> tuple[UUID, ...]:
    persisted_at = require_aware_utc(now, field_name="now")
    relationship = session.get(BusinessRelationshipRecord, relationship_id)
    if relationship is None:
        raise ValueError("business relationship does not exist")
    ids: list[UUID] = []
    for context in contexts:
        if context.relationship_key != relationship.relationship_key:
            raise ValueError("relationship context key does not match relationship")
        existing = session.scalar(
            select(RelationshipContextRecord).where(
                RelationshipContextRecord.relationship_id == relationship_id,
                RelationshipContextRecord.context_type == context.context_type,
                RelationshipContextRecord.value == context.value,
            )
        )
        if existing is None:
            existing = RelationshipContextRecord(
                id=uuid5(
                    NAMESPACE_URL,
                    "relationship-context:"
                    f"{relationship.relationship_key}:{context.context_type}:{context.value}",
                ),
                relationship_id=relationship_id,
                context_type=context.context_type,
                value=context.value,
                reference=context.reference,
                confidence=context.confidence,
                created_at=persisted_at,
            )
            session.add(existing)
        else:
            existing.reference = context.reference
            existing.confidence = context.confidence
        ids.append(existing.id)
    session.flush()
    return tuple(ids)


def _resolve_relationship(
    session: Session,
    snapshot: RelationshipEvidenceSnapshot,
    *,
    now: datetime,
) -> BusinessRelationshipRecord:
    existing = session.scalar(
        select(BusinessRelationshipRecord).where(
            BusinessRelationshipRecord.relationship_key == snapshot.relationship_key
        )
    )
    if existing is not None:
        return existing
    record = BusinessRelationshipRecord(
        id=uuid5(NAMESPACE_URL, f"business-relationship:{snapshot.relationship_key}"),
        relationship_key=snapshot.relationship_key,
        role=snapshot.role.value,
        status="under_review",
        source_organization_id=snapshot.source_organization_id,
        target_organization_id=snapshot.target_organization_id,
        source_link_status=snapshot.source_link_status.value,
        target_link_status=snapshot.target_link_status.value,
        source_name=snapshot.claimed_source_organization_name,
        target_name=snapshot.claimed_target_organization_name,
        valid_from=snapshot.valid_from,
        valid_until=snapshot.valid_until,
        first_published_at=snapshot.published_at,
        last_updated_at=snapshot.modified_at,
        last_observed_at=snapshot.observed_at,
        evidence_count=1,
        independent_source_count=1,
        strongest_evidence_class=snapshot.evidence_class.value,
        confidence=snapshot.confidence,
        has_contract_evidence=False,
        contract_backed_current=False,
        next_renewal_at=None,
        has_role_conflict=False,
        has_dispute=False,
        has_correction=False,
        has_retraction=False,
        historical_only=snapshot.historical_only,
        created_at=now,
        updated_at=now,
    )
    session.add(record)
    session.flush()
    return record


def _insert_evidence_snapshot(
    session: Session,
    relationship_id: UUID,
    snapshot: RelationshipEvidenceSnapshot,
    *,
    now: datetime,
) -> RelationshipEvidenceSnapshotRecord:
    snapshot_key = relationship_evidence_digest(snapshot)
    existing = session.scalar(
        select(RelationshipEvidenceSnapshotRecord).where(
            RelationshipEvidenceSnapshotRecord.snapshot_key == snapshot_key
        )
    )
    if existing is not None:
        if existing.relationship_id != relationship_id:
            raise ValueError("relationship evidence cannot move between relationships")
        return existing
    record = _snapshot_record(
        relationship_id=relationship_id,
        snapshot_key=snapshot_key,
        snapshot=snapshot,
        now=now,
    )
    session.add(record)
    session.flush()
    return record


def _snapshot_record(
    *,
    relationship_id: UUID,
    snapshot_key: str,
    snapshot: RelationshipEvidenceSnapshot,
    now: datetime,
) -> RelationshipEvidenceSnapshotRecord:
    return RelationshipEvidenceSnapshotRecord(
        id=uuid5(NAMESPACE_URL, f"relationship-evidence:{snapshot_key}"),
        relationship_id=relationship_id,
        snapshot_key=snapshot_key,
        source_id=snapshot.source_id,
        source_kind=snapshot.source_kind.value,
        source_record_key=snapshot.source_record_key,
        source_url=snapshot.source_url,
        relationship_key=snapshot.relationship_key,
        claim_type=snapshot.claim_type.value,
        role=snapshot.role.value,
        evidence_class=snapshot.evidence_class.value,
        title=snapshot.title,
        excerpt=snapshot.excerpt,
        claimed_source_organization_name=snapshot.claimed_source_organization_name,
        claimed_target_organization_name=snapshot.claimed_target_organization_name,
        source_organization_id=snapshot.source_organization_id,
        target_organization_id=snapshot.target_organization_id,
        source_link_status=snapshot.source_link_status.value,
        target_link_status=snapshot.target_link_status.value,
        published_at=snapshot.published_at,
        modified_at=snapshot.modified_at,
        observed_at=snapshot.observed_at,
        valid_from=snapshot.valid_from,
        valid_until=snapshot.valid_until,
        expires_at=snapshot.expires_at,
        contract_reference=snapshot.contract_reference,
        product_context=snapshot.product_context,
        service_context=snapshot.service_context,
        renewal_at=snapshot.renewal_at,
        independence_key=snapshot.independence_key or snapshot.source_id,
        confidence=snapshot.confidence,
        active=snapshot.active,
        historical_only=snapshot.historical_only,
        metadata_only=snapshot.metadata_only,
        supersedes_record_key=snapshot.supersedes_record_key,
        created_at=now,
    )


def _refresh_relationship(
    session: Session,
    relationship_id: UUID,
    *,
    now: datetime,
) -> None:
    record = session.get(BusinessRelationshipRecord, relationship_id)
    if record is None:
        raise ValueError("business relationship disappeared during reconciliation")
    evidence = latest_relationship_evidence(session, relationship_id)
    reconciled = reconcile_relationship_evidence(evidence, now=now)[0]
    record.role = reconciled.role.value
    record.status = reconciled.status.value
    record.source_organization_id = reconciled.source_organization_id
    record.target_organization_id = reconciled.target_organization_id
    record.source_link_status = reconciled.source_link_status.value
    record.target_link_status = reconciled.target_link_status.value
    record.source_name = _first_name(reconciled.claimed_source_organization_names)
    record.target_name = _first_name(reconciled.claimed_target_organization_names)
    record.valid_from = reconciled.valid_from
    record.valid_until = reconciled.valid_until
    record.first_published_at = reconciled.first_published_at
    record.last_updated_at = reconciled.last_updated_at
    record.last_observed_at = reconciled.last_observed_at
    record.evidence_count = reconciled.evidence_count
    record.independent_source_count = reconciled.independent_source_count
    record.strongest_evidence_class = reconciled.strongest_evidence_class.value
    record.confidence = reconciled.confidence
    record.has_contract_evidence = reconciled.has_contract_evidence
    record.contract_backed_current = reconciled.contract_backed_current
    record.next_renewal_at = reconciled.next_renewal_at
    record.has_role_conflict = reconciled.has_role_conflict
    record.has_dispute = reconciled.has_dispute
    record.has_correction = reconciled.has_correction
    record.has_retraction = reconciled.has_retraction
    record.historical_only = reconciled.historical_only
    record.updated_at = now


def _first_name(names: tuple[str, ...]) -> str | None:
    return names[0] if names else None
