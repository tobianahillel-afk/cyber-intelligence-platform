from __future__ import annotations

from collections.abc import Mapping
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from cip.modules.opportunities.domain.entities import CommercialSignal
from cip.modules.opportunities.infrastructure.models import CommercialSignalRecord

_MUTABLE_FIELDS = (
    "title",
    "summary",
    "confidence",
    "matched_terms",
    "published_at",
    "collected_at",
    "expires_at",
)


def store_commercial_signal(session: Session, signal: CommercialSignal) -> UUID:
    values = _signal_values(signal)
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
        _store_portable(session, values, signal.idempotency_key)
    session.flush()
    stored = _load_stored_signal(session, signal.idempotency_key)
    if stored is None:
        raise RuntimeError("commercial signal was not persisted")
    return stored.id


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
