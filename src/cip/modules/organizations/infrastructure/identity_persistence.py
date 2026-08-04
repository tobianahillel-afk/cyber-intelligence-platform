from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from uuid import NAMESPACE_URL, UUID, uuid5

from sqlalchemy import select
from sqlalchemy.orm import Session

from cip.modules.evidence.domain.entities import Evidence
from cip.modules.evidence.infrastructure.models import EvidenceRecord
from cip.modules.organizations.application.identity import IdentityProjection
from cip.modules.organizations.domain.entities import Organization
from cip.modules.organizations.domain.identity import MatchState
from cip.modules.organizations.domain.matching import normalized_organization_name
from cip.modules.organizations.infrastructure.identity_models import (
    OrganizationAliasRecord,
    OrganizationIdentifierRecord,
    OrganizationIdentityEvidenceRecord,
    OrganizationIdentityRecord,
    OrganizationMergeCandidateRecord,
    OrganizationRelationshipRecord,
)
from cip.modules.organizations.infrastructure.models import OrganizationRecord
from cip.shared.kernel.time import require_aware_utc


class IdentityPersistenceConflictError(RuntimeError):
    """Official identity data conflicts with already persisted exact identifiers."""


class IdentityReviewConflictError(RuntimeError):
    """A human confirmation would attach contradictory official identifiers."""


def persist_identity_projections(
    session: Session,
    projections: Sequence[IdentityProjection],
    *,
    now: datetime,
) -> tuple[UUID, ...]:
    if not projections:
        return ()
    persisted_at = require_aware_utc(now, field_name="now")
    for projection in projections:
        for organization in projection.projected_organizations:
            _upsert_organization(session, organization)
        _upsert_evidence(session, projection.evidence)
        _upsert_identity(session, projection, persisted_at)
    session.flush()
    for projection in projections:
        _replace_identifiers(session, projection)
        _upsert_aliases(session, projection)
        _link_evidence(session, projection)
        _upsert_candidates(session, projection)
    session.flush()
    for projection in projections:
        _upsert_relationships(session, projection)
    return tuple(dict.fromkeys(projection.identity.id for projection in projections))


def review_merge_candidate(
    session: Session,
    candidate_id: UUID,
    *,
    confirm: bool,
    actor: str,
    reviewed_at: datetime,
    note: str | None = None,
) -> OrganizationMergeCandidateRecord:
    reviewed = require_aware_utc(reviewed_at, field_name="reviewed_at")
    reviewer = actor.strip()
    if not reviewer:
        raise ValueError("actor is required")
    candidate = session.get(OrganizationMergeCandidateRecord, candidate_id)
    if candidate is None:
        raise LookupError("merge candidate not found")
    reviewable_states = {MatchState.NEEDS_REVIEW.value, MatchState.AUTO_CONFIRMED.value}
    if candidate.state not in reviewable_states:
        raise ValueError("merge candidate has already been reviewed")
    identity = session.get(OrganizationIdentityRecord, candidate.identity_id)
    if identity is None:
        raise LookupError("identity not found")
    if confirm:
        _ensure_no_identifier_conflict(session, identity, candidate.organization_id)
        identity.organization_id = candidate.organization_id
        candidate.state = MatchState.CONFIRMED.value
    else:
        candidate.state = MatchState.REJECTED.value
    candidate.reviewed_at = reviewed
    candidate.reviewed_by = reviewer
    candidate.review_note = note.strip() if note and note.strip() else None
    session.flush()
    return candidate


def _upsert_organization(session: Session, organization: Organization) -> None:
    record = session.get(OrganizationRecord, organization.id)
    if record is None:
        record = _pending_organization(session, organization.id)
    if record is None:
        session.add(
            OrganizationRecord(
                id=organization.id,
                canonical_name=organization.canonical_name,
                legal_name=organization.legal_name,
                country_code=organization.country_code,
                website_url=organization.website_url,
                registration_ids=list(organization.registration_ids),
                created_at=organization.created_at,
                updated_at=organization.updated_at,
            )
        )
        return
    record.canonical_name = organization.canonical_name
    record.legal_name = organization.legal_name or record.legal_name
    record.country_code = organization.country_code or record.country_code
    record.website_url = organization.website_url or record.website_url
    record.updated_at = max(record.updated_at, organization.updated_at)
    record.registration_ids = list(
        dict.fromkeys([*record.registration_ids, *organization.registration_ids])
    )


def _pending_organization(
    session: Session,
    organization_id: UUID,
) -> OrganizationRecord | None:
    for record in session.new:
        if isinstance(record, OrganizationRecord) and record.id == organization_id:
            return record
    return None


def _upsert_evidence(session: Session, evidence: Evidence) -> None:
    record = session.get(EvidenceRecord, evidence.id)
    if record is None:
        session.add(
            EvidenceRecord(
                id=evidence.id,
                source_id=evidence.source_id,
                source_record_key=evidence.source_record_key,
                source_url=evidence.source_url,
                summary=evidence.summary,
                confidence=evidence.confidence,
                collected_at=evidence.collected_at,
                published_at=evidence.published_at,
                observed_at=evidence.observed_at,
                content_hash_sha256=evidence.content_hash_sha256,
                raw_storage_uri=evidence.raw_storage_uri,
                raw_storage_permitted=evidence.raw_storage_permitted,
                retention_until=evidence.retention_until,
            )
        )
        return
    record.source_url = evidence.source_url
    record.summary = evidence.summary
    record.confidence = evidence.confidence
    record.collected_at = evidence.collected_at
    record.observed_at = evidence.observed_at
    record.content_hash_sha256 = evidence.content_hash_sha256
    record.retention_until = evidence.retention_until


def _upsert_identity(
    session: Session,
    projection: IdentityProjection,
    persisted_at: datetime,
) -> None:
    identity = projection.identity
    record = session.get(OrganizationIdentityRecord, identity.id)
    attached_id = projection.attached_organization_id
    if record is None:
        session.add(
            OrganizationIdentityRecord(
                id=identity.id,
                organization_id=attached_id,
                kind=identity.kind.value,
                official_name=identity.official_name,
                country_code=identity.country_code,
                status=identity.status.value,
                legal_form=identity.legal_form,
                activity_code=identity.activity_code,
                address=identity.address,
                postal_code=identity.postal_code,
                city=identity.city,
                is_headquarters=identity.is_headquarters,
                source_id=identity.source_id,
                source_record_key=identity.source_record_key,
                source_url=identity.source_url,
                confidence=identity.confidence,
                observed_at=identity.observed_at,
                valid_from=identity.valid_from,
                valid_until=identity.valid_until,
                created_at=persisted_at,
                updated_at=persisted_at,
            )
        )
        return
    if (
        record.organization_id is not None
        and attached_id not in {None, record.organization_id}
    ):
        raise IdentityPersistenceConflictError(
            "identity is already attached to another organization"
        )
    record.organization_id = attached_id or record.organization_id
    record.official_name = identity.official_name
    record.status = identity.status.value
    record.legal_form = identity.legal_form
    record.activity_code = identity.activity_code
    record.address = identity.address
    record.postal_code = identity.postal_code
    record.city = identity.city
    record.is_headquarters = identity.is_headquarters
    record.source_url = identity.source_url
    record.confidence = identity.confidence
    record.observed_at = identity.observed_at
    record.valid_from = identity.valid_from
    record.valid_until = identity.valid_until
    record.updated_at = persisted_at


def _replace_identifiers(session: Session, projection: IdentityProjection) -> None:
    identity = projection.identity
    for identifier in identity.identifiers:
        existing = session.scalar(
            select(OrganizationIdentifierRecord).where(
                OrganizationIdentifierRecord.exact_key == identifier.exact_key
            )
        )
        if existing is not None and existing.identity_id != identity.id:
            raise IdentityPersistenceConflictError(
                f"identifier {identifier.exact_key} is already linked to another identity"
            )
        if existing is None:
            session.add(
                OrganizationIdentifierRecord(
                    id=uuid5(
                        NAMESPACE_URL,
                        f"organization-identifier:{identifier.exact_key}",
                    ),
                    identity_id=identity.id,
                    scheme=identifier.scheme.value,
                    value=identifier.value,
                    issuing_country=identifier.issuing_country,
                    exact_key=identifier.exact_key,
                    source_id=identifier.source_id,
                    verified_at=identifier.verified_at,
                    is_current=identifier.is_current,
                )
            )
            continue
        existing.source_id = identifier.source_id
        existing.verified_at = identifier.verified_at
        existing.is_current = identifier.is_current


def _upsert_aliases(session: Session, projection: IdentityProjection) -> None:
    identity = projection.identity
    for alias in identity.aliases:
        normalized = normalized_organization_name(alias)
        existing = session.scalar(
            select(OrganizationAliasRecord).where(
                OrganizationAliasRecord.identity_id == identity.id,
                OrganizationAliasRecord.normalized_value == normalized,
            )
        )
        if existing is None:
            session.add(
                OrganizationAliasRecord(
                    id=uuid5(
                        NAMESPACE_URL,
                        f"organization-alias:{identity.id}:{normalized}",
                    ),
                    identity_id=identity.id,
                    value=alias,
                    normalized_value=normalized,
                    source_id=identity.source_id,
                    observed_at=identity.observed_at,
                )
            )
        else:
            existing.value = alias
            existing.observed_at = identity.observed_at


def _link_evidence(session: Session, projection: IdentityProjection) -> None:
    link = session.get(
        OrganizationIdentityEvidenceRecord,
        (projection.identity.id, projection.evidence.id),
    )
    if link is None:
        session.add(
            OrganizationIdentityEvidenceRecord(
                identity_id=projection.identity.id,
                evidence_id=projection.evidence.id,
            )
        )


def _upsert_candidates(session: Session, projection: IdentityProjection) -> None:
    reviewable_states = {MatchState.NEEDS_REVIEW.value, MatchState.AUTO_CONFIRMED.value}
    for candidate in projection.merge_candidates:
        record = session.get(OrganizationMergeCandidateRecord, candidate.id)
        if record is None:
            session.add(
                OrganizationMergeCandidateRecord(
                    id=candidate.id,
                    identity_id=candidate.identity_id,
                    organization_id=candidate.organization_id,
                    method=candidate.method.value,
                    score=candidate.score,
                    reasons=list(candidate.reasons),
                    state=candidate.state.value,
                    created_at=candidate.created_at,
                    reviewed_at=candidate.reviewed_at,
                    reviewed_by=candidate.reviewed_by,
                    review_note=candidate.review_note,
                )
            )
        elif record.state in reviewable_states:
            record.method = candidate.method.value
            record.score = candidate.score
            record.reasons = list(candidate.reasons)
            record.state = candidate.state.value
        if candidate.state is MatchState.AUTO_CONFIRMED:
            identity = session.get(OrganizationIdentityRecord, candidate.identity_id)
            if identity is not None:
                identity.organization_id = candidate.organization_id


def _upsert_relationships(session: Session, projection: IdentityProjection) -> None:
    for relationship in projection.relationships:
        if session.get(OrganizationIdentityRecord, relationship.subject_identity_id) is None:
            raise IdentityPersistenceConflictError(
                "relationship subject identity is missing"
            )
        if session.get(OrganizationIdentityRecord, relationship.object_identity_id) is None:
            raise IdentityPersistenceConflictError(
                "relationship object identity is missing"
            )
        record = session.get(OrganizationRelationshipRecord, relationship.id)
        if record is None:
            session.add(
                OrganizationRelationshipRecord(
                    id=relationship.id,
                    subject_identity_id=relationship.subject_identity_id,
                    object_identity_id=relationship.object_identity_id,
                    relationship_type=relationship.relationship_type.value,
                    source_id=relationship.source_id,
                    source_url=relationship.source_url,
                    confidence=relationship.confidence,
                    observed_at=relationship.observed_at,
                    valid_from=relationship.valid_from,
                    valid_until=relationship.valid_until,
                )
            )
        else:
            record.confidence = relationship.confidence
            record.observed_at = relationship.observed_at
            record.valid_from = relationship.valid_from
            record.valid_until = relationship.valid_until


def _ensure_no_identifier_conflict(
    session: Session,
    identity: OrganizationIdentityRecord,
    organization_id: UUID,
) -> None:
    incoming = _identifier_values(session, identity.id)
    existing_identity_ids = session.scalars(
        select(OrganizationIdentityRecord.id).where(
            OrganizationIdentityRecord.organization_id == organization_id,
            OrganizationIdentityRecord.id != identity.id,
        )
    ).all()
    for existing_identity_id in existing_identity_ids:
        existing = _identifier_values(session, existing_identity_id)
        for scheme in incoming.keys() & existing.keys():
            if incoming[scheme].isdisjoint(existing[scheme]):
                raise IdentityReviewConflictError(
                    f"cannot confirm candidate with conflicting {scheme} identifiers"
                )


def _identifier_values(session: Session, identity_id: UUID) -> dict[str, set[str]]:
    records = session.scalars(
        select(OrganizationIdentifierRecord).where(
            OrganizationIdentifierRecord.identity_id == identity_id,
            OrganizationIdentifierRecord.is_current.is_(True),
        )
    ).all()
    values: dict[str, set[str]] = {}
    for record in records:
        values.setdefault(record.scheme, set()).add(record.value)
    return values
