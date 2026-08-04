from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from cip.modules.organizations.application.identity_views import (
    AliasView,
    IdentifierView,
    IdentityView,
    MergeCandidatePage,
    MergeCandidateView,
    RelationshipView,
)
from cip.modules.organizations.domain.identifiers import IdentifierScheme
from cip.modules.organizations.domain.identity import (
    IdentityKind,
    IdentityStatus,
    MatchMethod,
    MatchState,
    RelationshipType,
)
from cip.modules.organizations.infrastructure.identity_models import (
    OrganizationAliasRecord,
    OrganizationIdentifierRecord,
    OrganizationIdentityEvidenceRecord,
    OrganizationIdentityRecord,
    OrganizationMergeCandidateRecord,
    OrganizationRelationshipRecord,
)
from cip.modules.organizations.infrastructure.models import OrganizationRecord


class OrganizationNotFoundError(LookupError):
    pass


class OrganizationIdentityNotFoundError(LookupError):
    pass


class MergeCandidateNotFoundError(LookupError):
    pass


def list_organization_identities(
    session: Session,
    organization_id: UUID,
) -> tuple[IdentityView, ...]:
    if session.get(OrganizationRecord, organization_id) is None:
        raise OrganizationNotFoundError("organization not found")
    records = session.scalars(
        select(OrganizationIdentityRecord)
        .where(OrganizationIdentityRecord.organization_id == organization_id)
        .order_by(
            OrganizationIdentityRecord.kind,
            OrganizationIdentityRecord.official_name,
            OrganizationIdentityRecord.id,
        )
    ).all()
    return tuple(_identity_view(session, record) for record in records)


def get_organization_identity(session: Session, identity_id: UUID) -> IdentityView:
    record = session.get(OrganizationIdentityRecord, identity_id)
    if record is None:
        raise OrganizationIdentityNotFoundError("organization identity not found")
    return _identity_view(session, record)


def list_merge_candidates(
    session: Session,
    *,
    states: tuple[MatchState, ...] = (),
    limit: int = 50,
    offset: int = 0,
) -> MergeCandidatePage:
    if not 1 <= limit <= 200:
        raise ValueError("limit must be between 1 and 200")
    if offset < 0:
        raise ValueError("offset cannot be negative")
    filters = []
    if states:
        filters.append(
            OrganizationMergeCandidateRecord.state.in_(state.value for state in states)
        )
    count_statement = select(func.count()).select_from(OrganizationMergeCandidateRecord)
    statement = select(OrganizationMergeCandidateRecord)
    for condition in filters:
        count_statement = count_statement.where(condition)
        statement = statement.where(condition)
    total = int(session.scalar(count_statement) or 0)
    records = session.scalars(
        statement.order_by(
            OrganizationMergeCandidateRecord.state,
            OrganizationMergeCandidateRecord.score.desc(),
            OrganizationMergeCandidateRecord.created_at.desc(),
            OrganizationMergeCandidateRecord.id,
        )
        .offset(offset)
        .limit(limit)
    ).all()
    return MergeCandidatePage(
        items=tuple(_candidate_view(session, record) for record in records),
        total=total,
        limit=limit,
        offset=offset,
    )


def get_merge_candidate(session: Session, candidate_id: UUID) -> MergeCandidateView:
    record = session.get(OrganizationMergeCandidateRecord, candidate_id)
    if record is None:
        raise MergeCandidateNotFoundError("merge candidate not found")
    return _candidate_view(session, record)


def _identity_view(session: Session, record: OrganizationIdentityRecord) -> IdentityView:
    identifiers = session.scalars(
        select(OrganizationIdentifierRecord)
        .where(OrganizationIdentifierRecord.identity_id == record.id)
        .order_by(
            OrganizationIdentifierRecord.scheme,
            OrganizationIdentifierRecord.value,
        )
    ).all()
    aliases = session.scalars(
        select(OrganizationAliasRecord)
        .where(OrganizationAliasRecord.identity_id == record.id)
        .order_by(OrganizationAliasRecord.normalized_value)
    ).all()
    evidence_ids = session.scalars(
        select(OrganizationIdentityEvidenceRecord.evidence_id)
        .where(OrganizationIdentityEvidenceRecord.identity_id == record.id)
        .order_by(OrganizationIdentityEvidenceRecord.evidence_id)
    ).all()
    relationships = session.scalars(
        select(OrganizationRelationshipRecord)
        .where(
            (OrganizationRelationshipRecord.subject_identity_id == record.id)
            | (OrganizationRelationshipRecord.object_identity_id == record.id)
        )
        .order_by(
            OrganizationRelationshipRecord.relationship_type,
            OrganizationRelationshipRecord.id,
        )
    ).all()
    return IdentityView(
        id=record.id,
        organization_id=record.organization_id,
        kind=IdentityKind(record.kind),
        official_name=record.official_name,
        country_code=record.country_code,
        status=IdentityStatus(record.status),
        legal_form=record.legal_form,
        activity_code=record.activity_code,
        address=record.address,
        postal_code=record.postal_code,
        city=record.city,
        is_headquarters=record.is_headquarters,
        source_id=record.source_id,
        source_record_key=record.source_record_key,
        source_url=record.source_url,
        confidence=record.confidence,
        observed_at=record.observed_at,
        valid_from=record.valid_from,
        valid_until=record.valid_until,
        identifiers=tuple(
            IdentifierView(
                scheme=IdentifierScheme(item.scheme),
                value=item.value,
                issuing_country=item.issuing_country,
                source_id=item.source_id,
                verified_at=item.verified_at,
                is_current=item.is_current,
            )
            for item in identifiers
        ),
        aliases=tuple(
            AliasView(
                value=item.value,
                source_id=item.source_id,
                observed_at=item.observed_at,
            )
            for item in aliases
        ),
        evidence_ids=tuple(evidence_ids),
        relationships=tuple(_relationship_view(item) for item in relationships),
    )


def _candidate_view(
    session: Session,
    record: OrganizationMergeCandidateRecord,
) -> MergeCandidateView:
    identity = session.get(OrganizationIdentityRecord, record.identity_id)
    organization = session.get(OrganizationRecord, record.organization_id)
    if identity is None or organization is None:
        raise RuntimeError("merge candidate references missing records")
    return MergeCandidateView(
        id=record.id,
        identity_id=record.identity_id,
        organization_id=record.organization_id,
        organization_name=organization.canonical_name,
        identity_name=identity.official_name,
        method=MatchMethod(record.method),
        score=record.score,
        reasons=tuple(record.reasons),
        state=MatchState(record.state),
        created_at=record.created_at,
        reviewed_at=record.reviewed_at,
        reviewed_by=record.reviewed_by,
        review_note=record.review_note,
    )


def _relationship_view(record: OrganizationRelationshipRecord) -> RelationshipView:
    return RelationshipView(
        id=record.id,
        subject_identity_id=record.subject_identity_id,
        object_identity_id=record.object_identity_id,
        relationship_type=RelationshipType(record.relationship_type),
        source_id=record.source_id,
        source_url=record.source_url,
        confidence=record.confidence,
        observed_at=record.observed_at,
        valid_from=record.valid_from,
        valid_until=record.valid_until,
    )
