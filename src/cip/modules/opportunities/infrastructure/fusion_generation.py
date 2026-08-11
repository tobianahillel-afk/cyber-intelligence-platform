from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from cip.modules.opportunities.domain.fusion import (
    DEFAULT_FUSION_CONFIG,
    FusionConfig,
    fuse_need_hypotheses,
)
from cip.modules.opportunities.infrastructure.hypotheses import store_need_hypothesis
from cip.modules.opportunities.infrastructure.mappers import signal_from_record
from cip.modules.opportunities.infrastructure.models import CommercialSignalRecord
from cip.shared.kernel.time import require_aware_utc


def generate_need_hypotheses(
    session: Session,
    organization_id: UUID,
    *,
    now: datetime,
    config: FusionConfig = DEFAULT_FUSION_CONFIG,
) -> tuple[UUID, ...]:
    evaluated_at = require_aware_utc(now, field_name="now")
    records = tuple(
        session.scalars(
            select(CommercialSignalRecord).where(
                CommercialSignalRecord.organization_id == organization_id,
                (CommercialSignalRecord.expires_at.is_(None))
                | (CommercialSignalRecord.expires_at > evaluated_at),
            )
        )
    )
    signals = tuple(signal_from_record(record) for record in records)
    hypotheses = fuse_need_hypotheses(
        organization_id,
        signals,
        now=evaluated_at,
        config=config,
    )
    stored = tuple(store_need_hypothesis(session, hypothesis) for hypothesis in hypotheses)
    session.flush()
    return tuple(record.id for record in stored)
