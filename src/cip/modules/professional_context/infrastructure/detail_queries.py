from __future__ import annotations

from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from cip.modules.organizations.infrastructure.persistence_time import coerce_utc
from cip.modules.professional_context.application.view_models import (
    CommunityContextView,
    OrganizationProfessionalMap,
    ProfessionalContactView,
    ProfessionalEvidenceView,
    ProfessionalPersonDetail,
    ProfessionalPersonFilters,
    ProfessionalRoleView,
    ReportingLineView,
    ServiceRelevanceView,
)
from cip.modules.professional_context.infrastructure.contact_models import (
    ProfessionalContactRecord,
    ProfessionalContactSnapshotRecord,
)
from cip.modules.professional_context.infrastructure.context_models import (
    ProfessionalCommunityRecord,
    ProfessionalCommunitySnapshotRecord,
    ProfessionalServiceRelevanceRecord,
)
from cip.modules.professional_context.infrastructure.person_models import (
    ProfessionalPersonSnapshotRecord,
)
from cip.modules.professional_context.infrastructure.queries import (
    get_professional_person_summary,
    list_professional_people,
)
from cip.modules.professional_context.infrastructure.role_models import (
    ProfessionalReportingLineRecord,
    ProfessionalReportingSnapshotRecord,
    ProfessionalRoleRecord,
    ProfessionalRoleSnapshotRecord,
)

ClaimEvidenceRow = (
    ProfessionalRoleSnapshotRecord
    | ProfessionalContactSnapshotRecord
    | ProfessionalCommunitySnapshotRecord
    | ProfessionalReportingSnapshotRecord
)


class ProfessionalPersonNotFoundError(LookupError):
    pass


def get_professional_person_detail(
    session: Session,
    person_key: str,
) -> ProfessionalPersonDetail:
    person = get_professional_person_summary(session, person_key)
    if person is None:
        raise ProfessionalPersonNotFoundError(person_key)
    roles = tuple(
        _role_view(row)
        for row in session.scalars(
            select(ProfessionalRoleRecord)
            .where(ProfessionalRoleRecord.person_key == person_key)
            .order_by(ProfessionalRoleRecord.last_observed_at.desc())
        )
    )
    reporting = tuple(
        _reporting_view(row)
        for row in session.scalars(
            select(ProfessionalReportingLineRecord)
            .where(
                or_(
                    ProfessionalReportingLineRecord.subject_person_key == person_key,
                    ProfessionalReportingLineRecord.manager_person_key == person_key,
                )
            )
            .order_by(ProfessionalReportingLineRecord.last_observed_at.desc())
        )
    )
    contacts = tuple(
        _contact_view(row)
        for row in session.scalars(
            select(ProfessionalContactRecord)
            .where(ProfessionalContactRecord.person_key == person_key)
            .order_by(ProfessionalContactRecord.last_observed_at.desc())
        )
    )
    community = tuple(
        _community_view(row)
        for row in session.scalars(
            select(ProfessionalCommunityRecord)
            .where(ProfessionalCommunityRecord.person_key == person_key)
            .order_by(ProfessionalCommunityRecord.last_observed_at.desc())
        )
    )
    relevance = tuple(
        _relevance_view(row)
        for row in session.scalars(
            select(ProfessionalServiceRelevanceRecord).where(
                ProfessionalServiceRelevanceRecord.person_key == person_key
            )
        )
    )
    return ProfessionalPersonDetail(
        person=person,
        roles=roles,
        reporting_as_subject=tuple(
            item for item in reporting if item.subject_person_key == person_key
        ),
        reporting_as_manager=tuple(
            item for item in reporting if item.manager_person_key == person_key
        ),
        contacts=contacts,
        community_context=community,
        service_relevance=relevance,
        evidence_history=_evidence_history(session, person_key),
    )


def get_organization_professional_map(
    session: Session,
    organization_id: UUID,
) -> OrganizationProfessionalMap:
    people = list_professional_people(
        session,
        filters=ProfessionalPersonFilters(organization_id=organization_id),
        limit=200,
        offset=0,
    ).items
    reporting = tuple(
        _reporting_view(row)
        for row in session.scalars(
            select(ProfessionalReportingLineRecord).where(
                ProfessionalReportingLineRecord.organization_id == organization_id,
                ProfessionalReportingLineRecord.deleted.is_(False),
            )
        )
    )
    contacts = tuple(
        _contact_view(row)
        for row in session.scalars(
            select(ProfessionalContactRecord).where(
                ProfessionalContactRecord.organization_id == organization_id,
                ProfessionalContactRecord.person_key.is_(None),
                ProfessionalContactRecord.deleted.is_(False),
            )
        )
    )
    community = tuple(
        _community_view(row)
        for row in session.scalars(
            select(ProfessionalCommunityRecord).where(
                ProfessionalCommunityRecord.organization_id == organization_id,
                ProfessionalCommunityRecord.deleted.is_(False),
            )
        )
    )
    return OrganizationProfessionalMap(
        organization_id=organization_id,
        people=people,
        reporting_lines=reporting,
        organization_contacts=contacts,
        community_context=community,
    )


def _role_view(row: ProfessionalRoleRecord) -> ProfessionalRoleView:
    return ProfessionalRoleView(
        claim_key=row.claim_key,
        role_title=row.role_title,
        team_name=row.team_name,
        organization_id=row.organization_id,
        claimed_organization_name=row.claimed_organization_name,
        employment_state=row.employment_state,
        confidence=row.confidence,
        review_state=row.review_state,
        first_observed_at=coerce_utc(row.first_observed_at),
        last_observed_at=coerce_utc(row.last_observed_at),
        retention_until=coerce_utc(row.retention_until),
        suppressed=row.suppressed,
        deleted=row.deleted,
    )


def _reporting_view(row: ProfessionalReportingLineRecord) -> ReportingLineView:
    return ReportingLineView(
        claim_key=row.claim_key,
        subject_person_key=row.subject_person_key,
        manager_person_key=row.manager_person_key,
        organization_id=row.organization_id,
        confidence=row.confidence,
        review_state=row.review_state,
        current=row.current,
        suppressed=row.suppressed,
        deleted=row.deleted,
        first_observed_at=coerce_utc(row.first_observed_at),
        last_observed_at=coerce_utc(row.last_observed_at),
    )


def _contact_view(row: ProfessionalContactRecord) -> ProfessionalContactView:
    return ProfessionalContactView(
        contact_key=row.contact_key,
        channel_type=row.channel_type,
        value=row.value,
        organization_id=row.organization_id,
        confidence=row.confidence,
        review_state=row.review_state,
        current=row.current,
        suppressed=row.suppressed,
        deleted=row.deleted,
        last_observed_at=coerce_utc(row.last_observed_at),
        retention_until=coerce_utc(row.retention_until),
    )


def _community_view(row: ProfessionalCommunityRecord) -> CommunityContextView:
    return CommunityContextView(
        context_key=row.context_key,
        community_name=row.community_name,
        context_type=row.context_type,
        context_value=row.context_value,
        acquisition_mode=row.acquisition_mode,
        organization_id=row.organization_id,
        confidence=row.confidence,
        review_state=row.review_state,
        current=row.current,
        suppressed=row.suppressed,
        deleted=row.deleted,
        last_observed_at=coerce_utc(row.last_observed_at),
    )


def _relevance_view(row: ProfessionalServiceRelevanceRecord) -> ServiceRelevanceView:
    return ServiceRelevanceView(
        mapping_key=row.mapping_key,
        service_family=row.service_family,
        rationale=row.rationale,
        confidence=row.confidence,
        review_state=row.review_state,
        source_claim_keys=tuple(row.source_claim_keys),
    )


def _evidence_history(
    session: Session,
    person_key: str,
) -> tuple[ProfessionalEvidenceView, ...]:
    rows: list[ProfessionalEvidenceView] = []
    for snapshot in session.scalars(
        select(ProfessionalPersonSnapshotRecord).where(
            ProfessionalPersonSnapshotRecord.person_key == person_key
        )
    ):
        rows.append(_person_evidence(snapshot))
    for model, label in (
        (ProfessionalRoleSnapshotRecord, "role"),
        (ProfessionalContactSnapshotRecord, "contact"),
        (ProfessionalCommunitySnapshotRecord, "community"),
    ):
        for snapshot in session.scalars(select(model).where(model.person_key == person_key)):
            rows.append(_claim_evidence(snapshot, label))
    for snapshot in session.scalars(
        select(ProfessionalReportingSnapshotRecord).where(
            or_(
                ProfessionalReportingSnapshotRecord.subject_person_key == person_key,
                ProfessionalReportingSnapshotRecord.manager_person_key == person_key,
            )
        )
    ):
        rows.append(_claim_evidence(snapshot, "reporting_line"))
    return tuple(sorted(rows, key=lambda item: item.observed_at, reverse=True))


def _person_evidence(row: ProfessionalPersonSnapshotRecord) -> ProfessionalEvidenceView:
    return ProfessionalEvidenceView(
        evidence_type="person_reference",
        source_id=row.source_id,
        source_record_key=row.source_record_key,
        source_url=row.source_url,
        observed_at=coerce_utc(row.observed_at),
        claim_type=None,
        review_state=row.review_state,
        suppressed=row.suppressed,
        deleted=row.deleted,
        retention_until=coerce_utc(row.retention_until),
    )


def _claim_evidence(row: ClaimEvidenceRow, label: str) -> ProfessionalEvidenceView:
    return ProfessionalEvidenceView(
        evidence_type=label,
        source_id=row.source_id,
        source_record_key=row.source_record_key,
        source_url=row.source_url,
        observed_at=coerce_utc(row.observed_at),
        claim_type=row.claim_type,
        review_state=row.review_state,
        suppressed=row.suppressed,
        deleted=row.deleted,
        retention_until=coerce_utc(row.retention_until),
    )
