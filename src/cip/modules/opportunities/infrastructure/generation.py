from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from cip.modules.opportunities.domain.entities import (
    NeedHypothesis,
    Opportunity,
    OpportunityState,
)
from cip.modules.opportunities.domain.rules import evaluate_siem_soc_buying_intent
from cip.modules.opportunities.domain.scoring import OpportunityComponent, OpportunityScore
from cip.modules.opportunities.infrastructure.mappers import (
    component_domain,
    database_utc,
    signal_from_record,
)
from cip.modules.opportunities.infrastructure.models import (
    CommercialSignalRecord,
    NeedHypothesisRecord,
    NeedHypothesisSignalRecord,
    OpportunityEvidenceRecord,
    OpportunityRecord,
    OpportunityScoreComponentRecord,
)
from cip.shared.kernel.time import require_aware_utc


def generate_siem_soc_opportunity(
    session: Session,
    organization_id: UUID,
    *,
    now: datetime,
) -> UUID | None:
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
    evaluation = evaluate_siem_soc_buying_intent(
        organization_id,
        tuple(signal_from_record(record) for record in records),
        now=evaluated_at,
    )
    if evaluation is None:
        return None
    hypothesis = _upsert_hypothesis(session, evaluation.hypothesis)
    opportunity = _upsert_opportunity(
        session,
        hypothesis_id=hypothesis.id,
        opportunity=evaluation.opportunity,
        now=evaluated_at,
    )
    components = _sync_score_components(
        session,
        opportunity.id,
        evaluation.opportunity.score.components,
    )
    _apply_score(opportunity, components, evaluation.opportunity.score)
    _replace_evidence_links(session, opportunity.id, evaluation.hypothesis.evidence_ids)
    session.flush()
    return opportunity.id


def _upsert_hypothesis(
    session: Session,
    hypothesis: NeedHypothesis,
) -> NeedHypothesisRecord:
    record = session.scalar(
        select(NeedHypothesisRecord).where(
            NeedHypothesisRecord.idempotency_key == hypothesis.idempotency_key
        )
    )
    if record is None:
        record = NeedHypothesisRecord(
            id=hypothesis.id,
            organization_id=hypothesis.organization_id,
            family=hypothesis.family.value,
            status="active",
            rule_id=hypothesis.rule_id,
            rule_version=hypothesis.rule_version,
            rationale=hypothesis.rationale,
            generated_at=hypothesis.generated_at,
            expires_at=hypothesis.expires_at,
            idempotency_key=hypothesis.idempotency_key,
        )
        session.add(record)
        session.flush()
    else:
        record.status = "active"
        record.rationale = hypothesis.rationale
        record.generated_at = hypothesis.generated_at
        record.expires_at = hypothesis.expires_at
    session.execute(
        delete(NeedHypothesisSignalRecord).where(
            NeedHypothesisSignalRecord.hypothesis_id == record.id
        )
    )
    session.add_all(
        NeedHypothesisSignalRecord(hypothesis_id=record.id, signal_id=signal_id)
        for signal_id in hypothesis.signal_ids
    )
    return record


def _upsert_opportunity(
    session: Session,
    *,
    hypothesis_id: UUID,
    opportunity: Opportunity,
    now: datetime,
) -> OpportunityRecord:
    record = session.scalar(
        select(OpportunityRecord).where(OpportunityRecord.hypothesis_id == hypothesis_id)
    )
    if record is None:
        record = OpportunityRecord(
            id=opportunity.id,
            organization_id=opportunity.organization_id,
            hypothesis_id=hypothesis_id,
            state=opportunity.state.value,
            created_at=opportunity.created_at,
            updated_at=opportunity.updated_at,
            snoozed_until=None,
            review_note=None,
            rejected_reason=None,
            **_opportunity_values(opportunity),
        )
        session.add(record)
        session.flush()
        return record
    _reopen_expired_snooze(record, now)
    for name, value in _opportunity_values(opportunity).items():
        setattr(record, name, value)
    record.updated_at = now
    return record


def _reopen_expired_snooze(record: OpportunityRecord, now: datetime) -> None:
    if (
        record.state == OpportunityState.SNOOZED.value
        and record.snoozed_until is not None
        and database_utc(record.snoozed_until) <= now
    ):
        record.state = OpportunityState.NEEDS_REVIEW.value
        record.snoozed_until = None


def _opportunity_values(opportunity: Opportunity) -> dict[str, object]:
    return {
        "recommended_offer": opportunity.recommended_offer,
        "relevant_roles": list(opportunity.relevant_roles),
        "trigger_summary": opportunity.trigger_summary,
        "next_action": opportunity.next_action,
        "confidence": opportunity.confidence,
        "raw_score": opportunity.score.raw_score,
        "adjusted_score": opportunity.score.adjusted_score,
        "score_version": opportunity.score.score_version,
        "config_version": opportunity.score.config_version,
        "calculation_hash": opportunity.score.calculation_hash,
        "generated_at": opportunity.score.generated_at,
        "expires_at": opportunity.score.expires_at,
        "last_evidence_at": opportunity.last_evidence_at,
        "data_quality": opportunity.data_quality.value,
    }


def _sync_score_components(
    session: Session,
    opportunity_id: UUID,
    generated: Iterable[OpportunityComponent],
) -> tuple[OpportunityScoreComponentRecord, ...]:
    existing = {
        record.rule_id: record
        for record in session.scalars(
            select(OpportunityScoreComponentRecord).where(
                OpportunityScoreComponentRecord.opportunity_id == opportunity_id
            )
        )
    }
    generated_components = tuple(generated)
    generated_rules = {component.rule_id for component in generated_components}
    for rule_id, existing_record in existing.items():
        if rule_id not in generated_rules:
            session.delete(existing_record)
    for component in generated_components:
        current_record: OpportunityScoreComponentRecord | None = existing.get(component.rule_id)
        if current_record is None:
            session.add(_new_component_record(opportunity_id, component))
        else:
            _refresh_component(current_record, component)
    session.flush()
    return tuple(
        session.scalars(
            select(OpportunityScoreComponentRecord)
            .where(OpportunityScoreComponentRecord.opportunity_id == opportunity_id)
            .order_by(OpportunityScoreComponentRecord.rule_id)
        )
    )


def _new_component_record(
    opportunity_id: UUID,
    component: OpportunityComponent,
) -> OpportunityScoreComponentRecord:
    return OpportunityScoreComponentRecord(
        id=uuid4(),
        opportunity_id=opportunity_id,
        rule_id=component.rule_id,
        value=component.value,
        weight=component.weight,
        contribution=component.contribution,
        kind=component.kind.value,
        reason=component.reason,
        evidence_ids=[str(value) for value in component.evidence_ids],
        analyst_overridden=False,
    )


def _refresh_component(
    record: OpportunityScoreComponentRecord,
    component: OpportunityComponent,
) -> None:
    record.kind = component.kind.value
    record.evidence_ids = [str(value) for value in component.evidence_ids]
    if record.analyst_overridden:
        record.original_value = component.value
        record.original_weight = component.weight
        return
    record.value = component.value
    record.weight = component.weight
    record.contribution = component.contribution
    record.reason = component.reason
    record.original_value = None
    record.original_weight = None


def _apply_score(
    opportunity: OpportunityRecord,
    records: tuple[OpportunityScoreComponentRecord, ...],
    generated: OpportunityScore,
) -> None:
    score = OpportunityScore(
        organization_id=opportunity.organization_id,
        score_version=generated.score_version,
        config_version=generated.config_version,
        components=tuple(component_domain(record) for record in records),
        generated_at=generated.generated_at,
        expires_at=generated.expires_at,
    )
    contributions = {component.rule_id: component.contribution for component in score.components}
    for record in records:
        record.contribution = contributions[record.rule_id]
    opportunity.raw_score = score.raw_score
    opportunity.adjusted_score = score.adjusted_score
    opportunity.score_version = score.score_version
    opportunity.config_version = score.config_version
    opportunity.calculation_hash = score.calculation_hash
    opportunity.generated_at = score.generated_at
    opportunity.expires_at = score.expires_at


def _replace_evidence_links(
    session: Session,
    opportunity_id: UUID,
    evidence_ids: Iterable[UUID],
) -> None:
    session.execute(
        delete(OpportunityEvidenceRecord).where(
            OpportunityEvidenceRecord.opportunity_id == opportunity_id
        )
    )
    session.add_all(
        OpportunityEvidenceRecord(opportunity_id=opportunity_id, evidence_id=evidence_id)
        for evidence_id in dict.fromkeys(evidence_ids)
    )
