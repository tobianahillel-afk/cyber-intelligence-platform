from __future__ import annotations

from uuid import UUID

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from cip.modules.opportunities.application.hypothesis_views import (
    NeedHypothesisView,
    SourceContributionView,
)
from cip.modules.opportunities.infrastructure.hypotheses import hypothesis_from_record
from cip.modules.opportunities.infrastructure.models import NeedHypothesisRecord
from cip.modules.organizations.infrastructure.models import OrganizationRecord
from cip.modules.service_taxonomy.domain.models import parse_service_family


def list_need_hypotheses(
    session: Session,
    *,
    organization_id: UUID | None = None,
    hypothesis_class: str | None = None,
    status: str | None = None,
    service_family: str | None = None,
    min_confidence: float | None = None,
    limit: int = 100,
) -> tuple[NeedHypothesisView, ...]:
    statement = _list_statement(
        organization_id=organization_id,
        hypothesis_class=hypothesis_class,
        status=status,
        min_confidence=min_confidence,
    )
    records = tuple(session.scalars(statement.limit(max(limit * 4, 200))))
    normalized_family = (
        parse_service_family(service_family).value if service_family is not None else None
    )
    filtered = (
        record
        for record in records
        if normalized_family is None or normalized_family in record.service_families
    )
    return tuple(_view(session, record) for record in list(filtered)[:limit])


def get_need_hypothesis(
    session: Session,
    hypothesis_id: UUID,
) -> NeedHypothesisView | None:
    record = session.get(NeedHypothesisRecord, hypothesis_id)
    return _view(session, record) if record is not None else None


def _list_statement(
    *,
    organization_id: UUID | None,
    hypothesis_class: str | None,
    status: str | None,
    min_confidence: float | None,
) -> Select[tuple[NeedHypothesisRecord]]:
    statement = select(NeedHypothesisRecord)
    if organization_id is not None:
        statement = statement.where(
            NeedHypothesisRecord.organization_id == organization_id
        )
    if hypothesis_class is not None:
        statement = statement.where(
            NeedHypothesisRecord.hypothesis_class == hypothesis_class
        )
    if status is not None:
        statement = statement.where(NeedHypothesisRecord.status == status)
    if min_confidence is not None:
        statement = statement.where(NeedHypothesisRecord.confidence >= min_confidence)
    return statement.order_by(
        NeedHypothesisRecord.confidence.desc(),
        NeedHypothesisRecord.generated_at.desc(),
        NeedHypothesisRecord.id,
    )


def _view(session: Session, record: NeedHypothesisRecord) -> NeedHypothesisView:
    hypothesis = hypothesis_from_record(session, record)
    organization = session.get(OrganizationRecord, record.organization_id)
    if organization is None:
        raise RuntimeError("hypothesis organization is missing")
    return NeedHypothesisView(
        id=hypothesis.id,
        organization_id=hypothesis.organization_id,
        organization=organization.canonical_name,
        family=hypothesis.family.value,
        status=hypothesis.status.value,
        hypothesis_class=hypothesis.hypothesis_class.value,
        service_families=tuple(family.value for family in hypothesis.service_families),
        confidence=hypothesis.confidence,
        urgency=hypothesis.urgency.value,
        horizon=hypothesis.horizon.value,
        rationale=hypothesis.rationale,
        applicable_offers=hypothesis.applicable_offers,
        signal_ids=hypothesis.signal_ids,
        evidence_ids=hypothesis.evidence_ids,
        conflicting_signal_ids=hypothesis.conflicting_signal_ids,
        negative_signal_ids=hypothesis.negative_signal_ids,
        source_contributions=tuple(
            SourceContributionView(
                independence_key=item.independence_key,
                polarity=item.polarity.value,
                signal_ids=item.signal_ids,
                max_confidence=item.max_confidence,
                contribution=item.contribution,
            )
            for item in hypothesis.source_contributions
        ),
        rule_id=hypothesis.rule_id,
        rule_version=hypothesis.rule_version,
        taxonomy_version=hypothesis.taxonomy_version,
        generated_at=hypothesis.generated_at,
        expires_at=hypothesis.expires_at,
    )
