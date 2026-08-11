from __future__ import annotations

from collections.abc import Mapping
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from cip.modules.evidence.infrastructure.models import EvidenceRecord
from cip.modules.opportunities.domain.entities import CommercialSignal
from cip.modules.opportunities.domain.signal_mapping import map_signal_to_canonical_needs
from cip.modules.opportunities.infrastructure.models import CommercialSignalRecord

_MUTABLE_FIELDS = (
    "title",
    "summary",
    "confidence",
    "matched_terms",
    "published_at",
    "collected_at",
    "expires_at",
    "service_families",
    "hypothesis_classes",
    "independence_key",
    "corroboration_group_key",
    "polarity",
    "is_explicit",
    "historical_only",
    "mapping_rule_id",
    "mapping_rule_version",
)


def store_commercial_signal(session: Session, signal: CommercialSignal) -> UUID:
    canonical = _canonical_signal(session, signal)
    values = _signal_values(canonical)
    dialect = session.get_bind().dialect.name
    if dialect == "postgresql":
        postgres_statement = postgresql_insert(CommercialSignalRecord).values(**values)
        session.execute(
            postgres_statement.on_conflict_do_update(
                index_elements=["idempotency_key"],
                set_={
                    name: getattr(postgres_statement.excluded, name)
                    for name in _MUTABLE_FIELDS
                },
            )
        )
    elif dialect == "sqlite":
        sqlite_statement = sqlite_insert(CommercialSignalRecord).values(**values)
        session.execute(
            sqlite_statement.on_conflict_do_update(
                index_elements=["idempotency_key"],
                set_={
                    name: getattr(sqlite_statement.excluded, name)
                    for name in _MUTABLE_FIELDS
                },
            )
        )
    else:
        _store_portable(session, values, canonical.idempotency_key)
    session.flush()
    stored = _load_stored_signal(session, canonical.idempotency_key)
    if stored is None:
        raise RuntimeError("commercial signal was not persisted")
    return stored.id


def _canonical_signal(session: Session, signal: CommercialSignal) -> CommercialSignal:
    source_id = session.scalar(
        select(EvidenceRecord.source_id).where(EvidenceRecord.id == signal.evidence_id)
    )
    if source_id is None:
        raise RuntimeError("commercial signal evidence must be persisted first")
    return map_signal_to_canonical_needs(signal, source_id=source_id)


def _signal_values(signal: CommercialSignal) -> dict[str, object]:
    return {
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
        "service_families": [family.value for family in signal.service_families],
        "hypothesis_classes": [
            hypothesis_class.value for hypothesis_class in signal.hypothesis_classes
        ],
        "independence_key": signal.independence_key,
        "corroboration_group_key": signal.corroboration_group_key,
        "polarity": signal.polarity.value,
        "is_explicit": signal.is_explicit,
        "historical_only": signal.historical_only,
        "mapping_rule_id": signal.mapping_rule_id,
        "mapping_rule_version": signal.mapping_rule_version,
    }


def _store_portable(
    session: Session,
    values: Mapping[str, object],
    idempotency_key: str,
) -> None:
    existing = session.scalar(
        select(CommercialSignalRecord).where(
            CommercialSignalRecord.idempotency_key == idempotency_key
        )
    )
    if existing is None:
        session.add(CommercialSignalRecord(**dict(values)))
        return
    for name in _MUTABLE_FIELDS:
        setattr(existing, name, values[name])


def _load_stored_signal(
    session: Session,
    idempotency_key: str,
) -> CommercialSignalRecord | None:
    statement = (
        select(CommercialSignalRecord)
        .where(CommercialSignalRecord.idempotency_key == idempotency_key)
        .execution_options(populate_existing=True)
    )
    return session.scalar(statement)
