from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from cip.modules.source_portfolio.infrastructure.models import (
    SourcePortfolioRecord,
    SourceValueEventRecord,
)
from cip.shared.kernel.time import require_aware_utc


class SourceExecutionMode(StrEnum):
    INCREMENTAL = "incremental"
    HISTORICAL_BACKFILL = "historical_backfill"


@dataclass(frozen=True, slots=True)
class SourceValueEvent:
    source_id: str
    execution_id: UUID
    execution_mode: SourceExecutionMode
    observations_written: int
    commercial_projections: int
    identity_projections: int
    request_cost: float
    not_modified: bool
    occurred_at: datetime

    def __post_init__(self) -> None:
        if not self.source_id.strip():
            raise ValueError("source_id is required")
        for field_name in (
            "observations_written",
            "commercial_projections",
            "identity_projections",
        ):
            if getattr(self, field_name) < 0:
                raise ValueError(f"{field_name} cannot be negative")
        if self.request_cost < 0:
            raise ValueError("request_cost cannot be negative")
        object.__setattr__(
            self,
            "occurred_at",
            require_aware_utc(self.occurred_at, field_name="occurred_at"),
        )


@dataclass(frozen=True, slots=True)
class SourceValueSummary:
    executions: int
    modified_executions: int
    observations_written: int
    commercial_projections: int
    identity_projections: int
    request_cost: float


def record_source_value_event(
    session: Session,
    event: SourceValueEvent,
) -> bool:
    if session.get(SourcePortfolioRecord, event.source_id) is None:
        return False
    existing = session.scalar(
        select(SourceValueEventRecord.id).where(
            SourceValueEventRecord.source_id == event.source_id,
            SourceValueEventRecord.execution_id == event.execution_id,
            SourceValueEventRecord.execution_mode == event.execution_mode.value,
        )
    )
    if existing is not None:
        return False
    session.add(
        SourceValueEventRecord(
            id=uuid4(),
            source_id=event.source_id,
            execution_id=event.execution_id,
            execution_mode=event.execution_mode.value,
            observations_written=event.observations_written,
            commercial_projections=event.commercial_projections,
            identity_projections=event.identity_projections,
            request_cost=event.request_cost,
            not_modified=event.not_modified,
            occurred_at=event.occurred_at,
        )
    )
    session.flush()
    return True


def summarize_source_value(
    session: Session,
    *,
    source_id: str | None = None,
    excluded_source_id: str | None = None,
) -> SourceValueSummary:
    statement = select(
        func.count(SourceValueEventRecord.id),
        func.count(SourceValueEventRecord.id).filter(
            SourceValueEventRecord.not_modified.is_(False)
        ),
        func.coalesce(func.sum(SourceValueEventRecord.observations_written), 0),
        func.coalesce(func.sum(SourceValueEventRecord.commercial_projections), 0),
        func.coalesce(func.sum(SourceValueEventRecord.identity_projections), 0),
        func.coalesce(func.sum(SourceValueEventRecord.request_cost), 0.0),
    )
    if source_id is not None:
        statement = statement.where(SourceValueEventRecord.source_id == source_id.strip())
    if excluded_source_id is not None:
        statement = statement.where(
            SourceValueEventRecord.source_id != excluded_source_id.strip()
        )
    row = session.execute(statement).one()
    return SourceValueSummary(
        executions=int(row[0]),
        modified_executions=int(row[1]),
        observations_written=int(row[2]),
        commercial_projections=int(row[3]),
        identity_projections=int(row[4]),
        request_cost=float(row[5]),
    )
