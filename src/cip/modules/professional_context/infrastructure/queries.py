from __future__ import annotations

from sqlalchemy import exists, func, or_, select
from sqlalchemy.orm import Session

from cip.modules.organizations.infrastructure.persistence_time import coerce_utc
from cip.modules.professional_context.application.view_models import (
    ProfessionalPersonFilters,
    ProfessionalPersonPage,
    ProfessionalPersonSummary,
)
from cip.modules.professional_context.infrastructure.person_models import (
    ProfessionalPersonRecord,
)
from cip.modules.professional_context.infrastructure.role_models import ProfessionalRoleRecord


def list_professional_people(
    session: Session,
    *,
    filters: ProfessionalPersonFilters,
    limit: int,
    offset: int,
) -> ProfessionalPersonPage:
    _validate_page(limit, offset)
    statement = _apply_filters(select(ProfessionalPersonRecord), filters)
    total = session.scalar(select(func.count()).select_from(statement.subquery())) or 0
    people = tuple(
        session.scalars(
            statement.order_by(
                ProfessionalPersonRecord.last_observed_at.desc(),
                ProfessionalPersonRecord.person_key,
            )
            .limit(limit)
            .offset(offset)
        )
    )
    return ProfessionalPersonPage(
        items=tuple(_person_summary(session, person) for person in people),
        total=int(total),
        limit=limit,
        offset=offset,
    )


def get_professional_person_summary(
    session: Session,
    person_key: str,
) -> ProfessionalPersonSummary | None:
    record = session.scalar(
        select(ProfessionalPersonRecord).where(
            ProfessionalPersonRecord.person_key == person_key
        )
    )
    return _person_summary(session, record) if record is not None else None


def _apply_filters(statement, filters: ProfessionalPersonFilters):
    if not filters.include_suppressed:
        statement = statement.where(ProfessionalPersonRecord.suppressed.is_(False))
    if not filters.include_deleted:
        statement = statement.where(ProfessionalPersonRecord.deleted.is_(False))
    if filters.review_state:
        statement = statement.where(
            ProfessionalPersonRecord.review_state == filters.review_state
        )
    if filters.lawful_basis:
        statement = statement.where(
            ProfessionalPersonRecord.lawful_basis == filters.lawful_basis
        )
    if filters.organization_id is not None:
        statement = statement.where(
            exists(
                select(ProfessionalRoleRecord.id).where(
                    ProfessionalRoleRecord.person_key == ProfessionalPersonRecord.person_key,
                    ProfessionalRoleRecord.organization_id == filters.organization_id,
                    ProfessionalRoleRecord.deleted.is_(False),
                )
            )
        )
    if filters.employment_state:
        statement = statement.where(
            exists(
                select(ProfessionalRoleRecord.id).where(
                    ProfessionalRoleRecord.person_key == ProfessionalPersonRecord.person_key,
                    ProfessionalRoleRecord.employment_state == filters.employment_state,
                    ProfessionalRoleRecord.deleted.is_(False),
                )
            )
        )
    if filters.query:
        pattern = f"%{filters.query.strip()}%"
        statement = statement.where(
            or_(
                ProfessionalPersonRecord.display_name.ilike(pattern),
                exists(
                    select(ProfessionalRoleRecord.id).where(
                        ProfessionalRoleRecord.person_key == ProfessionalPersonRecord.person_key,
                        ProfessionalRoleRecord.role_title.ilike(pattern),
                    )
                ),
            )
        )
    return statement


def _person_summary(
    session: Session,
    record: ProfessionalPersonRecord,
) -> ProfessionalPersonSummary:
    role = session.scalar(
        select(ProfessionalRoleRecord)
        .where(
            ProfessionalRoleRecord.person_key == record.person_key,
            ProfessionalRoleRecord.employment_state == "current",
            ProfessionalRoleRecord.deleted.is_(False),
            ProfessionalRoleRecord.suppressed.is_(False),
        )
        .order_by(ProfessionalRoleRecord.last_observed_at.desc())
        .limit(1)
    )
    return ProfessionalPersonSummary(
        person_key=record.person_key,
        display_name=record.display_name,
        confidence=record.confidence,
        review_state=record.review_state,
        lawful_basis=record.lawful_basis,
        processing_purpose=record.processing_purpose,
        current=record.current,
        suppressed=record.suppressed,
        deleted=record.deleted,
        last_observed_at=coerce_utc(record.last_observed_at),
        retention_until=coerce_utc(record.retention_until),
        current_role=role.role_title if role else None,
        current_team=role.team_name if role else None,
        organization_id=role.organization_id if role else None,
    )


def _validate_page(limit: int, offset: int) -> None:
    if not 1 <= limit <= 200:
        raise ValueError("limit must be between 1 and 200")
    if offset < 0:
        raise ValueError("offset cannot be negative")
