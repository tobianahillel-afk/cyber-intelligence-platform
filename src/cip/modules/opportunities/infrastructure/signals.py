from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from cip.modules.opportunities.domain.entities import CommercialSignal
from cip.modules.opportunities.infrastructure.models import CommercialSignalRecord


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
        _store_portable(session, values, signal.idempotency_key)
    session.flush()
    stored_id = session.scalar(
        select(CommercialSignalRecord.id).where(
            CommercialSignalRecord.idempotency_key == signal.idempotency_key
        )
    )
    if stored_id is None:
        raise RuntimeError("commercial signal was not persisted")
    return stored_id


def _store_portable(
    session: Session,
    values: dict[str, object],
    idempotency_key: str,
) -> None:
    existing = session.scalar(
        select(CommercialSignalRecord.id).where(
            CommercialSignalRecord.idempotency_key == idempotency_key
        )
    )
    if existing is None:
        session.add(CommercialSignalRecord(**values))
