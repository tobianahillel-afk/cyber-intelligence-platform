from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from uuid import UUID

from sqlalchemy.orm import Session

from cip.modules.collection_orchestration.application.ports import CommercialProjection
from cip.modules.evidence.domain.entities import Evidence
from cip.modules.evidence.infrastructure.models import EvidenceRecord
from cip.modules.opportunities.infrastructure.generation import (
    generate_siem_soc_opportunity,
)
from cip.modules.opportunities.infrastructure.signals import store_commercial_signal
from cip.modules.organizations.domain.entities import Organization
from cip.modules.organizations.infrastructure.models import OrganizationRecord
from cip.shared.kernel.time import require_aware_utc


def persist_commercial_projections(
    session: Session,
    projections: Sequence[CommercialProjection],
    *,
    now: datetime,
) -> tuple[UUID, ...]:
    evaluated_at = require_aware_utc(now, field_name="now")
    organization_ids: list[UUID] = []
    for projection in projections:
        _upsert_organization(session, projection.organization)
        _upsert_evidence(session, projection.evidence)
        store_commercial_signal(session, projection.signal)
        organization_ids.append(projection.organization.id)
    opportunity_ids: list[UUID] = []
    for organization_id in dict.fromkeys(organization_ids):
        opportunity_id = generate_siem_soc_opportunity(
            session,
            organization_id,
            now=evaluated_at,
        )
        if opportunity_id is not None:
            opportunity_ids.append(opportunity_id)
    return tuple(opportunity_ids)


def _upsert_organization(session: Session, organization: Organization) -> None:
    record = session.get(OrganizationRecord, organization.id)
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
        session.flush()
        return
    record.canonical_name = organization.canonical_name
    record.legal_name = organization.legal_name
    record.country_code = organization.country_code
    record.updated_at = organization.updated_at


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
        session.flush()
        return
    record.source_url = evidence.source_url
    record.summary = evidence.summary
    record.confidence = evidence.confidence
    record.collected_at = evidence.collected_at
    record.published_at = evidence.published_at
    record.content_hash_sha256 = evidence.content_hash_sha256
    record.retention_until = evidence.retention_until
