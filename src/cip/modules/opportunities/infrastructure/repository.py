from __future__ import annotations

from collections.abc import Iterable
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from cip.modules.evidence.infrastructure.models import EvidenceRecord
from cip.modules.opportunities.application.view_models import (
    OpportunityDetail,
    OpportunityEvidenceItem,
    OpportunityListItem,
    OpportunityPage,
    OpportunityReviewItem,
    OpportunityScoreComponentItem,
)
from cip.modules.opportunities.domain.entities import (
    CommercialSignal,
    DataQuality,
    Opportunity,
    OpportunityFamily,
    OpportunityState,
    ReviewAction,
    SignalType,
)
from cip.modules.opportunities.domain.rules import evaluate_siem_soc_buying_intent
from cip.modules.opportunities.domain.scoring import (
    ComponentKind,
    OpportunityComponent,
    OpportunityScore,
)
from cip.modules.opportunities.infrastructure.models import (
    CommercialSignalRecord,
    NeedHypothesisRecord,
    NeedHypothesisSignalRecord,
    OpportunityEvidenceRecord,
    OpportunityRecord,
    OpportunityReviewRecord,
    OpportunityScoreComponentRecord,
)
from cip.modules.organizations.infrastructure.models import OrganizationRecord
from cip.shared.kernel.time import require_aware_utc


class OpportunityNotFoundError(LookupError):
    pass


class ScoreComponentNotFoundError(LookupError):
    pass


def store_commercial_signal(session: Session, signal: CommercialSignal) -> UUID:
    values = {
        "id": signal.id,
        "organization_id": signal.organization_id,
        "evidence_id": signal.evidence_id,
        "signal_type": signal.signal_type.value,
        "title": signal.title,
        "summary": signal.summary,
        "confidence": signal.confidence,
        "matched_terms": list(signal.matched_terms),
        "published_at": signal.published_at,
        "collected_at": signal.collected_at,
        "expires_at": signal.expires_at,
        "created_at": signal.created_at,
        "idempotency_key": signal.idempotency_key,
    }
    dialect = session.get_bind().dialect.name
    if dialect == "postgresql":
        statement = postgresql_insert(CommercialSignalRecord).values(**values)
        statement = statement.on_conflict_do_nothing(index_elements=["idempotency_key"])
        session.execute(statement)
    elif dialect == "sqlite":
        statement = sqlite_insert(CommercialSignalRecord).values(**values)
        statement = statement.on_conflict_do_nothing(index_elements=["idempotency_key"])
        session.execute(statement)
    else:
        existing = session.scalar(
            select(CommercialSignalRecord.id).where(
                CommercialSignalRecord.idempotency_key == signal.idempotency_key
            )
        )
        if existing is None:
            session.add(CommercialSignalRecord(**values))
    session.flush()
    stored_id = session.scalar(
        select(CommercialSignalRecord.id).where(
            CommercialSignalRecord.idempotency_key == signal.idempotency_key
        )
    )
    if stored_id is None:
        raise RuntimeError("commercial signal was not persisted")
    return stored_id


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
        tuple(_signal_from_record(record) for record in records),
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
    _replace_score_components(session, opportunity, evaluation.opportunity.score.components)
    _replace_evidence_links(session, opportunity.id, evaluation.hypothesis.evidence_ids)
    session.flush()
    return opportunity.id


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
    if not 0.0 <= min_score <= 100.0:
        raise ValueError("min_score must be between 0 and 100")
    if not 1 <= limit <= 200 or offset < 0:
        raise ValueError("invalid pagination")
    filters = [OpportunityRecord.adjusted_score >= min_score]
    if states:
        filters.append(OpportunityRecord.state.in_(state.value for state in states))
    if family is not None:
        filters.append(NeedHypothesisRecord.family == family.value)
    base = (
        select(OpportunityRecord)
        .join(NeedHypothesisRecord, OpportunityRecord.hypothesis_id == NeedHypothesisRecord.id)
        .where(*filters)
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
            base.order_by(
                OpportunityRecord.adjusted_score.desc(),
                OpportunityRecord.last_evidence_at.desc(),
            )
            .limit(limit)
            .offset(offset)
        )
    )
    return OpportunityPage(
        items=tuple(_list_item(session, record) for record in records),
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
    component_records = tuple(
        session.scalars(
            select(OpportunityScoreComponentRecord)
            .where(OpportunityScoreComponentRecord.opportunity_id == opportunity_id)
            .order_by(OpportunityScoreComponentRecord.rule_id)
        )
    )
    evidence_records = tuple(
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
        opportunity=_list_item(session, record),
        hypothesis_id=hypothesis.id,
        hypothesis_status=hypothesis.status,
        rule_id=hypothesis.rule_id,
        rule_version=hypothesis.rule_version,
        rationale=hypothesis.rationale,
        generated_at=_database_utc(record.generated_at),
        expires_at=_optional_database_utc(record.expires_at),
        score_version=record.score_version,
        config_version=record.config_version,
        raw_score=record.raw_score,
        calculation_hash=record.calculation_hash,
        review_note=record.review_note,
        rejected_reason=record.rejected_reason,
        components=tuple(_component_view(item) for item in component_records),
        evidence=tuple(_evidence_view(item) for item in evidence_records),
        reviews=tuple(_review_view(item) for item in reviews),
    )


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
    actor_name = actor.strip()
    if not actor_name:
        raise ValueError("actor is required")
    previous_state = record.state
    domain = _opportunity_from_record(session, record)
    reviewed = domain.review(
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
    actor_name = actor.strip()
    if not actor_name:
        raise ValueError("actor is required")
    component = session.get(OpportunityScoreComponentRecord, component_id, with_for_update=True)
    if component is None or component.opportunity_id != opportunity_id:
        raise ScoreComponentNotFoundError(str(component_id))
    opportunity = session.get(OpportunityRecord, opportunity_id, with_for_update=True)
    if opportunity is None:
        raise OpportunityNotFoundError(str(opportunity_id))
    if value is None and weight is None and reason is None:
        raise ValueError("at least one component field must change")
    if not component.analyst_overridden:
        component.original_value = component.value
        component.original_weight = component.weight
    component.value = component.value if value is None else value
    component.weight = component.weight if weight is None else weight
    component.reason = component.reason if reason is None else reason.strip()
    component.analyst_overridden = True
    records = tuple(
        session.scalars(
            select(OpportunityScoreComponentRecord)
            .where(OpportunityScoreComponentRecord.opportunity_id == opportunity_id)
            .order_by(OpportunityScoreComponentRecord.rule_id)
        )
    )
    components = tuple(_component_domain(item) for item in records)
    expires_at = _optional_database_utc(opportunity.expires_at)
    score = OpportunityScore(
        organization_id=opportunity.organization_id,
        score_version=opportunity.score_version,
        config_version=opportunity.config_version,
        components=components,
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


def _upsert_hypothesis(session: Session, hypothesis: object) -> NeedHypothesisRecord:
    from cip.modules.opportunities.domain.entities import NeedHypothesis

    if not isinstance(hypothesis, NeedHypothesis):
        raise TypeError("hypothesis must be NeedHypothesis")
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
    if (
        record.state == OpportunityState.SNOOZED.value
        and record.snoozed_until is not None
        and _database_utc(record.snoozed_until) <= now
    ):
        record.state = OpportunityState.NEEDS_REVIEW.value
        record.snoozed_until = None
    for name, value in _opportunity_values(opportunity).items():
        setattr(record, name, value)
    record.updated_at = now
    return record


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


def _replace_score_components(
    session: Session,
    opportunity: OpportunityRecord,
    components: Iterable[OpportunityComponent],
) -> None:
    session.execute(
        delete(OpportunityScoreComponentRecord).where(
            OpportunityScoreComponentRecord.opportunity_id == opportunity.id
        )
    )
    session.add_all(
        OpportunityScoreComponentRecord(
            id=uuid4(),
            opportunity_id=opportunity.id,
            rule_id=component.rule_id,
            value=component.value,
            weight=component.weight,
            contribution=component.contribution,
            kind=component.kind.value,
            reason=component.reason,
            evidence_ids=[str(value) for value in component.evidence_ids],
            analyst_overridden=False,
        )
        for component in components
    )


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


def _signal_from_record(record: CommercialSignalRecord) -> CommercialSignal:
    return CommercialSignal(
        id=record.id,
        organization_id=record.organization_id,
        evidence_id=record.evidence_id,
        signal_type=SignalType(record.signal_type),
        title=record.title,
        summary=record.summary,
        confidence=record.confidence,
        matched_terms=tuple(record.matched_terms),
        published_at=_optional_database_utc(record.published_at),
        collected_at=_database_utc(record.collected_at),
        expires_at=_optional_database_utc(record.expires_at),
        created_at=_database_utc(record.created_at),
    )


def _opportunity_from_record(
    session: Session,
    record: OpportunityRecord,
) -> Opportunity:
    components = tuple(
        _component_domain(item)
        for item in session.scalars(
            select(OpportunityScoreComponentRecord)
            .where(OpportunityScoreComponentRecord.opportunity_id == record.id)
            .order_by(OpportunityScoreComponentRecord.rule_id)
        )
    )
    expires_at = _optional_database_utc(record.expires_at)
    score = OpportunityScore(
        organization_id=record.organization_id,
        score_version=record.score_version,
        config_version=record.config_version,
        components=components,
        generated_at=_database_utc(record.generated_at),
        expires_at=expires_at,
    )
    return Opportunity(
        id=record.id,
        organization_id=record.organization_id,
        hypothesis_id=record.hypothesis_id,
        recommended_offer=record.recommended_offer,
        relevant_roles=tuple(record.relevant_roles),
        trigger_summary=record.trigger_summary,
        next_action=record.next_action,
        score=score,
        confidence=record.confidence,
        last_evidence_at=_database_utc(record.last_evidence_at),
        data_quality=DataQuality(record.data_quality),
        state=OpportunityState(record.state),
        created_at=_database_utc(record.created_at),
        updated_at=_database_utc(record.updated_at),
        snoozed_until=_optional_database_utc(record.snoozed_until),
        review_note=record.review_note,
        rejected_reason=record.rejected_reason,
    )


def _list_item(session: Session, record: OpportunityRecord) -> OpportunityListItem:
    organization = session.get(OrganizationRecord, record.organization_id)
    hypothesis = session.get(NeedHypothesisRecord, record.hypothesis_id)
    if organization is None or hypothesis is None:
        raise RuntimeError("opportunity organization or hypothesis is missing")
    evidence_count = int(
        session.scalar(
            select(func.count()).where(
                OpportunityEvidenceRecord.opportunity_id == record.id
            )
        )
        or 0
    )
    return OpportunityListItem(
        id=record.id,
        organization_id=record.organization_id,
        organization=organization.canonical_name,
        country=organization.country_code,
        family=hypothesis.family,
        state=record.state,
        data_quality=record.data_quality,
        recommended_offer=record.recommended_offer,
        score=record.adjusted_score,
        confidence=record.confidence,
        trigger=record.trigger_summary,
        last_evidence_at=_database_utc(record.last_evidence_at),
        updated_at=_database_utc(record.updated_at),
        relevant_roles=tuple(record.relevant_roles),
        next_action=record.next_action,
        evidence_count=evidence_count,
        snoozed_until=_optional_database_utc(record.snoozed_until),
    )


def _component_domain(record: OpportunityScoreComponentRecord) -> OpportunityComponent:
    return OpportunityComponent(
        rule_id=record.rule_id,
        value=record.value,
        weight=record.weight,
        reason=record.reason,
        kind=ComponentKind(record.kind),
        evidence_ids=tuple(UUID(value) for value in record.evidence_ids),
    )


def _component_view(
    record: OpportunityScoreComponentRecord,
) -> OpportunityScoreComponentItem:
    return OpportunityScoreComponentItem(
        id=record.id,
        rule_id=record.rule_id,
        value=record.value,
        weight=record.weight,
        contribution=record.contribution,
        kind=record.kind,
        reason=record.reason,
        evidence_ids=tuple(UUID(value) for value in record.evidence_ids),
        analyst_overridden=record.analyst_overridden,
        original_value=record.original_value,
        original_weight=record.original_weight,
    )


def _evidence_view(record: EvidenceRecord) -> OpportunityEvidenceItem:
    return OpportunityEvidenceItem(
        id=record.id,
        source_id=record.source_id,
        source_url=record.source_url,
        source_record_key=record.source_record_key,
        summary=record.summary,
        confidence=record.confidence,
        collected_at=_database_utc(record.collected_at),
        published_at=_optional_database_utc(record.published_at),
        observed_at=_optional_database_utc(record.observed_at),
    )


def _review_view(record: OpportunityReviewRecord) -> OpportunityReviewItem:
    return OpportunityReviewItem(
        id=record.id,
        action=record.action,
        previous_state=record.previous_state,
        new_state=record.new_state,
        actor=record.actor,
        note=record.note,
        occurred_at=_database_utc(record.occurred_at),
        snoozed_until=_optional_database_utc(record.snoozed_until),
    )


def _database_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _optional_database_utc(value: datetime | None) -> datetime | None:
    return _database_utc(value) if value is not None else None
