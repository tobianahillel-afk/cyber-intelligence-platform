from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from cip.modules.professional_context.domain import ProfessionalServiceRelevance
from cip.modules.professional_context.infrastructure.context_models import (
    ProfessionalServiceRelevanceRecord,
)
from cip.shared.kernel.time import require_aware_utc


def persist_service_relevance(
    session: Session,
    mappings: Iterable[ProfessionalServiceRelevance],
    *,
    now: datetime,
) -> tuple[ProfessionalServiceRelevanceRecord, ...]:
    current = require_aware_utc(now, field_name="now")
    records: list[ProfessionalServiceRelevanceRecord] = []
    for mapping in mappings:
        record = session.scalar(
            select(ProfessionalServiceRelevanceRecord).where(
                ProfessionalServiceRelevanceRecord.mapping_key == mapping.mapping_key
            )
        )
        if record is None:
            record = ProfessionalServiceRelevanceRecord(
                id=uuid4(),
                mapping_key=mapping.mapping_key,
                person_key=mapping.person_key,
                organization_id=mapping.organization_id,
                service_family=mapping.service_family.value,
                rationale=mapping.rationale,
                confidence=mapping.confidence,
                source_claim_keys=list(mapping.source_claim_keys),
                review_state=mapping.review_state.value,
                created_at=mapping.created_at,
                updated_at=current,
            )
            session.add(record)
        else:
            record.person_key = mapping.person_key
            record.organization_id = mapping.organization_id
            record.service_family = mapping.service_family.value
            record.rationale = mapping.rationale
            record.confidence = mapping.confidence
            record.source_claim_keys = list(mapping.source_claim_keys)
            record.review_state = mapping.review_state.value
            record.updated_at = current
        records.append(record)
    session.flush()
    return tuple(records)
