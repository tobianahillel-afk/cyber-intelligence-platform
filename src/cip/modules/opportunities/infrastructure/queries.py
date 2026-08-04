from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from cip.modules.evidence.infrastructure.models import EvidenceRecord
from cip.modules.opportunities.application.view_models import OpportunityDetail, OpportunityPage
from cip.modules.opportunities.domain.entities import OpportunityFamily, OpportunityState
from cip.modules.opportunities.infrastructure.errors import OpportunityNotFoundError
from cip.modules.opportunities.infrastructure.mappers import (
    component_view,
    database_utc,
    evidence_view,
    list_item,
    optional_database_utc,
    review_view,
)
from cip.modules.opportunities.infrastructure.models import (
    NeedHypothesisRecord,
    OpportunityEvidenceRecord,
    OpportunityRecord,
    OpportunityReviewRecord,
    OpportunityScoreComponentRecord,
)
from cip.shared.kernel.time import require_aware_utc


def list_opportunities(
    session: Session,
    *,
    now: datetime,
    states: tuple[OpportunityState, ...] = (),
    family: OpportunityFamily | None = None,
    min_score: float = 0.0,
    limit: int = 50,
    offset: int = 0,
) -> OpportunityPage:
    generated_at = require_aware_utc(now, field_name="now")
    _validate_list_options(min_score=min_score, limit=limit, offset=offset)
    filters = [OpportunityRecord.adjusted_score >= min_score]
    if states:
        filters.append(OpportunityRecord.state.in_(state.value for state in states))
    if family is not None:
        filters.append(NeedHypothesisRecord.family == family.value)
    joined = select(OpportunityRecord).join(
        NeedHypothesisRecord,
        OpportunityRecord.hypothesis_id == NeedHypothesisRecord.id,
    )
    total = int(
        session.scalar(
            select(func.count())
            .select_from(OpportunityRecord)
            .join(
                NeedHypothesisRecord,
                OpportunityRecord.hypothesis_id == NeedHypothesisRecord.id,
            )
            .where(*filters)
        )
        or 0
    )
    records = tuple(
        session.scalars(
            joined.where(*filters)
            .order_by(
                OpportunityRecord.adjusted_score.desc(),
                OpportunityRecord.last_evidence_at.desc(),
            )
            .limit(limit)
            .offset(offset)
        )
    )
    return OpportunityPage(
        items=tuple(list_item(session, record) for record in records),
        total=total,
        limit=limit,
        offset=offset,
        generated_at=generated_at,
    )


def get_opportunity_detail(session: Session, opportunity_id: UUID) -> OpportunityDetail:
    record = session.get(OpportunityRecord, opportunity_id)
    if record is None:
        raise OpportunityNotFoundError(str(opportunity_id))
    hypothesis = session.get(NeedHypothesisRecord, record.hypothesis_id)
    if hypothesis is None:
        raise RuntimeError("opportunity hypothesis is missing")
    components = tuple(
        session.scalars(
            select(OpportunityScoreComponentRecord)
            .where(OpportunityScoreComponentRecord.opportunity_id == opportunity_id)
            .order_by(OpportunityScoreComponentRecord.rule_id)
        )
    )
    evidence = tuple(
        session.scalars(
            select(EvidenceRecord)
            .join(
                OpportunityEvidenceRecord,
                OpportunityEvidenceRecord.evidence_id == EvidenceRecord.id,
            )
            .where(OpportunityEvidenceRecord.opportunity_id == opportunity_id)
            .order_by(EvidenceRecord.published_at.desc(), EvidenceRecord.collected_at.desc())
        )
    )
    reviews = tuple(
        session.scalars(
            select(OpportunityReviewRecord)
            .where(OpportunityReviewRecord.opportunity_id == opportunity_id)
            .order_by(OpportunityReviewRecord.occurred_at.desc())
        )
    )
    return OpportunityDetail(
        opportunity=list_item(session, record),
        hypothesis_id=hypothesis.id,
        hypothesis_status=hypothesis.status,
        rule_id=hypothesis.rule_id,
        rule_version=hypothesis.rule_version,
        rationale=hypothesis.rationale,
        generated_at=database_utc(record.generated_at),
        expires_at=optional_database_utc(record.expires_at),
        score_version=record.score_version,
        config_version=record.config_version,
        raw_score=record.raw_score,
        calculation_hash=record.calculation_hash,
        review_note=record.review_note,
        rejected_reason=record.rejected_reason,
        components=tuple(component_view(item) for item in components),
        evidence=tuple(evidence_view(item) for item in evidence),
        reviews=tuple(review_view(item) for item in reviews),
    )


def _validate_list_options(*, min_score: float, limit: int, offset: int) -> None:
    if not 0.0 <= min_score <= 100.0:
        raise ValueError("min_score must be between 0 and 100")
    if not 1 <= limit <= 200 or offset < 0:
        raise ValueError("invalid pagination")
