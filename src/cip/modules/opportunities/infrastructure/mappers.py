from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from cip.modules.evidence.infrastructure.models import EvidenceRecord
from cip.modules.opportunities.application.view_models import (
    OpportunityEvidenceItem,
    OpportunityListItem,
    OpportunityReviewItem,
    OpportunityScoreComponentItem,
)
from cip.modules.opportunities.domain.entities import (
    CommercialSignal,
    DataQuality,
    Opportunity,
    OpportunityState,
    SignalType,
)
from cip.modules.opportunities.domain.scoring import (
    ComponentKind,
    OpportunityComponent,
    OpportunityScore,
)
from cip.modules.opportunities.infrastructure.models import (
    CommercialSignalRecord,
    NeedHypothesisRecord,
    OpportunityEvidenceRecord,
    OpportunityRecord,
    OpportunityReviewRecord,
    OpportunityScoreComponentRecord,
)
from cip.modules.organizations.infrastructure.models import OrganizationRecord


def signal_from_record(record: CommercialSignalRecord) -> CommercialSignal:
    return CommercialSignal(
        id=record.id,
        organization_id=record.organization_id,
        evidence_id=record.evidence_id,
        signal_type=SignalType(record.signal_type),
        title=record.title,
        summary=record.summary,
        confidence=record.confidence,
        matched_terms=tuple(record.matched_terms),
        published_at=optional_database_utc(record.published_at),
        collected_at=database_utc(record.collected_at),
        expires_at=optional_database_utc(record.expires_at),
        created_at=database_utc(record.created_at),
    )


def opportunity_from_record(session: Session, record: OpportunityRecord) -> Opportunity:
    components = tuple(
        component_domain(item)
        for item in session.scalars(
            select(OpportunityScoreComponentRecord)
            .where(OpportunityScoreComponentRecord.opportunity_id == record.id)
            .order_by(OpportunityScoreComponentRecord.rule_id)
        )
    )
    score = OpportunityScore(
        organization_id=record.organization_id,
        score_version=record.score_version,
        config_version=record.config_version,
        components=components,
        generated_at=database_utc(record.generated_at),
        expires_at=optional_database_utc(record.expires_at),
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
        last_evidence_at=database_utc(record.last_evidence_at),
        data_quality=DataQuality(record.data_quality),
        state=OpportunityState(record.state),
        created_at=database_utc(record.created_at),
        updated_at=database_utc(record.updated_at),
        snoozed_until=optional_database_utc(record.snoozed_until),
        review_note=record.review_note,
        rejected_reason=record.rejected_reason,
    )


def list_item(session: Session, record: OpportunityRecord) -> OpportunityListItem:
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
        last_evidence_at=database_utc(record.last_evidence_at),
        updated_at=database_utc(record.updated_at),
        relevant_roles=tuple(record.relevant_roles),
        next_action=record.next_action,
        evidence_count=evidence_count,
        snoozed_until=optional_database_utc(record.snoozed_until),
    )


def component_domain(record: OpportunityScoreComponentRecord) -> OpportunityComponent:
    return OpportunityComponent(
        rule_id=record.rule_id,
        value=record.value,
        weight=record.weight,
        reason=record.reason,
        kind=ComponentKind(record.kind),
        evidence_ids=tuple(UUID(value) for value in record.evidence_ids),
    )


def component_view(record: OpportunityScoreComponentRecord) -> OpportunityScoreComponentItem:
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


def evidence_view(record: EvidenceRecord) -> OpportunityEvidenceItem:
    return OpportunityEvidenceItem(
        id=record.id,
        source_id=record.source_id,
        source_url=record.source_url,
        source_record_key=record.source_record_key,
        summary=record.summary,
        confidence=record.confidence,
        collected_at=database_utc(record.collected_at),
        published_at=optional_database_utc(record.published_at),
        observed_at=optional_database_utc(record.observed_at),
    )


def review_view(record: OpportunityReviewRecord) -> OpportunityReviewItem:
    return OpportunityReviewItem(
        id=record.id,
        action=record.action,
        previous_state=record.previous_state,
        new_state=record.new_state,
        actor=record.actor,
        note=record.note,
        occurred_at=database_utc(record.occurred_at),
        snoozed_until=optional_database_utc(record.snoozed_until),
    )


def database_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def optional_database_utc(value: datetime | None) -> datetime | None:
    return database_utc(value) if value is not None else None
