from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from cip.modules.opportunities.domain.entities import OpportunityState, ReviewAction
from cip.modules.opportunities.domain.scoring import OpportunityScore
from cip.modules.opportunities.infrastructure.errors import (
    OpportunityNotFoundError,
    ScoreComponentNotFoundError,
)
from cip.modules.opportunities.infrastructure.mappers import (
    component_domain,
    opportunity_from_record,
    optional_database_utc,
)
from cip.modules.opportunities.infrastructure.models import (
    OpportunityRecord,
    OpportunityReviewRecord,
    OpportunityScoreComponentRecord,
)
from cip.shared.kernel.time import require_aware_utc


def review_opportunity(
    session: Session,
    opportunity_id: UUID,
    action: ReviewAction,
    *,
    actor: str,
    now: datetime,
    note: str | None = None,
    snoozed_until: datetime | None = None,
) -> OpportunityState:
    record = session.get(OpportunityRecord, opportunity_id, with_for_update=True)
    if record is None:
        raise OpportunityNotFoundError(str(opportunity_id))
    actor_name = _actor_name(actor)
    previous_state = record.state
    reviewed = opportunity_from_record(session, record).review(
        action,
        now=now,
        note=note,
        snoozed_until=snoozed_until,
    )
    record.state = reviewed.state.value
    record.updated_at = reviewed.updated_at
    record.snoozed_until = reviewed.snoozed_until
    record.review_note = reviewed.review_note
    record.rejected_reason = reviewed.rejected_reason
    session.add(
        OpportunityReviewRecord(
            id=uuid4(),
            opportunity_id=record.id,
            action=action.value,
            previous_state=previous_state,
            new_state=record.state,
            actor=actor_name,
            note=reviewed.review_note,
            occurred_at=reviewed.updated_at,
            snoozed_until=reviewed.snoozed_until,
        )
    )
    session.flush()
    return OpportunityState(record.state)


def override_score_component(
    session: Session,
    opportunity_id: UUID,
    component_id: UUID,
    *,
    actor: str,
    now: datetime,
    value: float | None = None,
    weight: float | None = None,
    reason: str | None = None,
) -> float:
    changed_at = require_aware_utc(now, field_name="now")
    actor_name = _actor_name(actor)
    component = session.get(OpportunityScoreComponentRecord, component_id, with_for_update=True)
    if component is None or component.opportunity_id != opportunity_id:
        raise ScoreComponentNotFoundError(str(component_id))
    opportunity = session.get(OpportunityRecord, opportunity_id, with_for_update=True)
    if opportunity is None:
        raise OpportunityNotFoundError(str(opportunity_id))
    _apply_override(component, value=value, weight=weight, reason=reason)
    records = tuple(
        session.scalars(
            select(OpportunityScoreComponentRecord)
            .where(OpportunityScoreComponentRecord.opportunity_id == opportunity_id)
            .order_by(OpportunityScoreComponentRecord.rule_id)
        )
    )
    score = _recalculate_score(opportunity, records, changed_at)
    session.add(
        OpportunityReviewRecord(
            id=uuid4(),
            opportunity_id=opportunity_id,
            action="override_score_component",
            previous_state=opportunity.state,
            new_state=opportunity.state,
            actor=actor_name,
            note=f"Overrode score component {component.rule_id}",
            occurred_at=changed_at,
        )
    )
    session.flush()
    return score.adjusted_score


def _apply_override(
    component: OpportunityScoreComponentRecord,
    *,
    value: float | None,
    weight: float | None,
    reason: str | None,
) -> None:
    if value is None and weight is None and reason is None:
        raise ValueError("at least one component field must change")
    if not component.analyst_overridden:
        component.original_value = component.value
        component.original_weight = component.weight
    component.value = component.value if value is None else value
    component.weight = component.weight if weight is None else weight
    if reason is not None:
        normalized_reason = reason.strip()
        if not normalized_reason:
            raise ValueError("reason cannot be empty")
        component.reason = normalized_reason
    component.analyst_overridden = True


def _recalculate_score(
    opportunity: OpportunityRecord,
    records: tuple[OpportunityScoreComponentRecord, ...],
    changed_at: datetime,
) -> OpportunityScore:
    expires_at = optional_database_utc(opportunity.expires_at)
    score = OpportunityScore(
        organization_id=opportunity.organization_id,
        score_version=opportunity.score_version,
        config_version=opportunity.config_version,
        components=tuple(component_domain(item) for item in records),
        generated_at=changed_at,
        expires_at=expires_at if expires_at is not None and expires_at > changed_at else None,
    )
    contributions = {item.rule_id: item.contribution for item in score.components}
    for item in records:
        item.contribution = contributions[item.rule_id]
    opportunity.raw_score = score.raw_score
    opportunity.adjusted_score = score.adjusted_score
    opportunity.calculation_hash = score.calculation_hash
    opportunity.generated_at = changed_at
    opportunity.updated_at = changed_at
    return score


def _actor_name(actor: str) -> str:
    value = actor.strip()
    if not value:
        raise ValueError("actor is required")
    return value
