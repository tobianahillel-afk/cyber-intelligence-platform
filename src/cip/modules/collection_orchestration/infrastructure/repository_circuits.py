from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from cip.modules.collection_orchestration.domain.models import CircuitState
from cip.modules.collection_orchestration.infrastructure.models import (
    CollectionCircuitRecord,
    CollectionJobRecord,
)
from cip.modules.collection_orchestration.infrastructure.repository_common import (
    database_utc,
    optional_database_utc,
)


def circuit_allows_claim(
    session: Session,
    *,
    record: CollectionJobRecord,
    now: datetime,
) -> bool:
    circuit = session.get(
        CollectionCircuitRecord,
        (record.source_id, record.adapter_id),
        with_for_update=True,
    )
    if circuit is None or circuit.state == CircuitState.CLOSED.value:
        return True
    reopen_at = optional_database_utc(circuit.reopen_at)
    if reopen_at is not None and reopen_at > now:
        record.available_at = max(database_utc(record.available_at), reopen_at)
        return False
    circuit.state = CircuitState.HALF_OPEN.value
    circuit.updated_at = now
    return True


def register_circuit_failure(
    session: Session,
    *,
    record: CollectionJobRecord,
    now: datetime,
    error_code: str,
) -> CollectionCircuitRecord:
    circuit = session.get(
        CollectionCircuitRecord,
        (record.source_id, record.adapter_id),
        with_for_update=True,
    )
    if circuit is None:
        circuit = CollectionCircuitRecord(
            source_id=record.source_id,
            adapter_id=record.adapter_id,
            state=CircuitState.CLOSED.value,
            consecutive_failures=0,
            updated_at=now,
        )
        session.add(circuit)
    circuit.consecutive_failures += 1
    circuit.last_error_code = error_code
    circuit.updated_at = now
    _apply_circuit_state(circuit, record=record, now=now)
    return circuit


def reset_circuit(
    session: Session,
    *,
    source_id: str,
    adapter_id: str,
    now: datetime,
) -> None:
    circuit = session.get(
        CollectionCircuitRecord,
        (source_id, adapter_id),
        with_for_update=True,
    )
    if circuit is None:
        return
    circuit.state = CircuitState.CLOSED.value
    circuit.consecutive_failures = 0
    circuit.opened_at = None
    circuit.reopen_at = None
    circuit.last_error_code = None
    circuit.updated_at = now


def _apply_circuit_state(
    circuit: CollectionCircuitRecord,
    *,
    record: CollectionJobRecord,
    now: datetime,
) -> None:
    if circuit.consecutive_failures < record.circuit_failure_threshold:
        circuit.state = CircuitState.CLOSED.value
        circuit.opened_at = None
        circuit.reopen_at = None
        return
    circuit.state = CircuitState.OPEN.value
    circuit.opened_at = now
    circuit.reopen_at = now + timedelta(seconds=record.circuit_reset_seconds)
