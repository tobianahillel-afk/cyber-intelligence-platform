from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy.orm import Session

from cip.modules.organizations.domain.entities import Organization
from cip.modules.organizations.infrastructure.models import OrganizationRecord
from cip.modules.organizations.infrastructure.persistence_time import latest_utc


def upsert_organizations(
    session: Session,
    organizations: Sequence[Organization],
) -> tuple[UUID, ...]:
    persisted: list[UUID] = []
    for organization in organizations:
        _upsert_organization(session, organization)
        persisted.append(organization.id)
    if persisted:
        session.flush()
    return tuple(dict.fromkeys(persisted))


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
    record.updated_at = latest_utc(record.updated_at, organization.updated_at)
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
