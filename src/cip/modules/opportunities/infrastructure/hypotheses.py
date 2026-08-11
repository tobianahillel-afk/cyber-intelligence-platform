from __future__ import annotations

from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from cip.modules.opportunities.domain.entities import (
    HypothesisStatus,
    NeedHorizon,
    NeedHypothesis,
    NeedHypothesisClass,
    NeedUrgency,
    OpportunityFamily,
    SignalPolarity,
    SourceContribution,
)
from cip.modules.opportunities.infrastructure.mappers import database_utc
from cip.modules.opportunities.infrastructure.models import (
    CommercialSignalRecord,
    NeedHypothesisRecord,
    NeedHypothesisSignalRecord,
)
from cip.modules.service_taxonomy.domain.models import parse_service_family

_MUTABLE_FIELDS = (
    "status",
    "rationale",
    "generated_at",
    "expires_at",
    "hypothesis_class",
    "service_families",
    "confidence",
    "urgency",
    "horizon",
    "applicable_offers",
    "conflicting_signal_ids",
    "negative_signal_ids",
    "source_contributions",
    "taxonomy_version",
)


def store_need_hypothesis(
    session: Session,
    hypothesis: NeedHypothesis,
) -> NeedHypothesisRecord:
    record = session.scalar(
        select(NeedHypothesisRecord).where(
            NeedHypothesisRecord.idempotency_key == hypothesis.idempotency_key
        )
    )
    values = _hypothesis_values(hypothesis)
    if record is None:
        record = NeedHypothesisRecord(id=hypothesis.id, **values)
        session.add(record)
        session.flush()
    else:
        for name in _MUTABLE_FIELDS:
            setattr(record, name, values[name])
    _replace_signal_links(session, record.id, hypothesis.all_signal_ids)
    session.flush()
    return record


def hypothesis_from_record(
    session: Session,
    record: NeedHypothesisRecord,
) -> NeedHypothesis:
    signal_ids = _signal_ids(session, record.id)
    conflicting = tuple(UUID(value) for value in record.conflicting_signal_ids)
    negative = tuple(UUID(value) for value in record.negative_signal_ids)
    excluded = set(conflicting + negative)
    supporting = tuple(signal_id for signal_id in signal_ids if signal_id not in excluded)
    evidence_ids = _evidence_ids(session, signal_ids)
    contributions = tuple(
        _source_contribution_from_json(item) for item in record.source_contributions
    )
    return NeedHypothesis(
        id=record.id,
        organization_id=record.organization_id,
        family=OpportunityFamily(record.family),
        rule_id=record.rule_id,
        rule_version=record.rule_version,
        rationale=record.rationale,
        signal_ids=supporting,
        evidence_ids=evidence_ids,
        generated_at=database_utc(record.generated_at),
        expires_at=database_utc(record.expires_at),
        status=HypothesisStatus(record.status),
        hypothesis_class=NeedHypothesisClass(record.hypothesis_class),
        service_families=tuple(
            parse_service_family(value) for value in record.service_families
        ),
        confidence=record.confidence,
        urgency=NeedUrgency(record.urgency),
        horizon=NeedHorizon(record.horizon),
        applicable_offers=tuple(record.applicable_offers),
        conflicting_signal_ids=conflicting,
        negative_signal_ids=negative,
        source_contributions=contributions,
        taxonomy_version=record.taxonomy_version,
    )


def _source_contribution_from_json(item: dict[str, object]) -> SourceContribution:
    independence_key = _required_text(item, "independence_key")
    polarity = _required_text(item, "polarity")
    raw_signal_ids = item.get("signal_ids")
    if not isinstance(raw_signal_ids, list) or not all(
        isinstance(value, str) for value in raw_signal_ids
    ):
        raise ValueError("source contribution signal_ids must be a list of UUID strings")
    max_confidence = _required_number(item, "max_confidence")
    contribution = _required_number(item, "contribution")
    return SourceContribution(
        independence_key=independence_key,
        polarity=SignalPolarity(polarity),
        signal_ids=tuple(UUID(value) for value in raw_signal_ids),
        max_confidence=max_confidence,
        contribution=contribution,
    )


def _required_text(item: dict[str, object], key: str) -> str:
    value = item.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"source contribution {key} must be a non-empty string")
    return value


def _required_number(item: dict[str, object], key: str) -> float:
    value = item.get(key)
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ValueError(f"source contribution {key} must be numeric")
    return float(value)


def _hypothesis_values(hypothesis: NeedHypothesis) -> dict[str, object]:
    return {
        "organization_id": hypothesis.organization_id,
        "family": hypothesis.family.value,
        "status": hypothesis.status.value,
        "rule_id": hypothesis.rule_id,
        "rule_version": hypothesis.rule_version,
        "rationale": hypothesis.rationale,
        "generated_at": hypothesis.generated_at,
        "expires_at": hypothesis.expires_at,
        "idempotency_key": hypothesis.idempotency_key,
        "hypothesis_class": hypothesis.hypothesis_class.value,
        "service_families": [family.value for family in hypothesis.service_families],
        "confidence": hypothesis.confidence,
        "urgency": hypothesis.urgency.value,
        "horizon": hypothesis.horizon.value,
        "applicable_offers": list(hypothesis.applicable_offers),
        "conflicting_signal_ids": [str(value) for value in hypothesis.conflicting_signal_ids],
        "negative_signal_ids": [str(value) for value in hypothesis.negative_signal_ids],
        "source_contributions": [
            {
                "independence_key": item.independence_key,
                "polarity": item.polarity.value,
                "signal_ids": [str(value) for value in item.signal_ids],
                "max_confidence": item.max_confidence,
                "contribution": item.contribution,
            }
            for item in hypothesis.source_contributions
        ],
        "taxonomy_version": hypothesis.taxonomy_version,
    }


def _signal_ids(session: Session, hypothesis_id: UUID) -> tuple[UUID, ...]:
    return tuple(
        session.scalars(
            select(NeedHypothesisSignalRecord.signal_id)
            .where(NeedHypothesisSignalRecord.hypothesis_id == hypothesis_id)
            .order_by(NeedHypothesisSignalRecord.signal_id)
        )
    )


def _evidence_ids(session: Session, signal_ids: tuple[UUID, ...]) -> tuple[UUID, ...]:
    if not signal_ids:
        return ()
    return tuple(
        dict.fromkeys(
            session.scalars(
                select(CommercialSignalRecord.evidence_id).where(
                    CommercialSignalRecord.id.in_(signal_ids)
                )
            )
        )
    )


def _replace_signal_links(
    session: Session,
    hypothesis_id: UUID,
    signal_ids: tuple[UUID, ...],
) -> None:
    session.execute(
        delete(NeedHypothesisSignalRecord).where(
            NeedHypothesisSignalRecord.hypothesis_id == hypothesis_id
        )
    )
    session.add_all(
        NeedHypothesisSignalRecord(hypothesis_id=hypothesis_id, signal_id=signal_id)
        for signal_id in signal_ids
    )
