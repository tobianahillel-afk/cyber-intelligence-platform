from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from cip.modules.collection_orchestration.domain.models import CollectionJob, SourceSchedule
from cip.modules.collection_orchestration.infrastructure.models import CollectionJobRecord
from cip.modules.collection_orchestration.infrastructure.repository import enqueue_job
from cip.modules.source_governance.infrastructure.models import SourceRecord
from cip.modules.source_portfolio.application.errors import SourcePortfolioStateError
from cip.modules.source_portfolio.application.execution import source_execution_allowed
from cip.modules.source_portfolio.application.records import (
    audit,
    get_portfolio_record,
    to_catalog_entry,
)
from cip.modules.source_portfolio.domain.models import CollectionMode
from cip.shared.kernel.time import require_aware_utc


@dataclass(frozen=True, slots=True)
class PriorityRefreshResult:
    job_id: UUID
    created: bool


def request_priority_refresh(
    session: Session,
    source_id: str,
    *,
    actor: str,
    now: datetime,
) -> PriorityRefreshResult:
    current = require_aware_utc(now, field_name="now")
    entry = to_catalog_entry(session, get_portfolio_record(session, source_id))
    if not entry.executable or entry.adapter is None:
        raise SourcePortfolioStateError("source is not executable")
    if not entry.adapter.supports(CollectionMode.PRIORITY_REFRESH):
        raise SourcePortfolioStateError("adapter does not support priority refresh")
    if not source_execution_allowed(session, entry.source_id, now=current):
        raise SourcePortfolioStateError("source execution is disabled or expired")
    if session.get(SourceRecord, entry.source_id) is None:
        raise SourcePortfolioStateError("source governance policy is not synchronized")
    schedule = SourceSchedule(
        source_id=entry.source_id,
        adapter_id=entry.adapter.adapter_id,
        interval_seconds=60,
    )
    slot = current.replace(second=0, microsecond=0)
    job = CollectionJob.from_schedule(schedule, scheduled_for=slot)
    created = enqueue_job(session, job)
    job_id = job.id if created else _existing_job_id(session, job.idempotency_key)
    audit(
        session,
        entry.source_id,
        "priority_refresh_requested",
        actor,
        current,
        details={"job_id": str(job_id), "created": created},
    )
    session.flush()
    return PriorityRefreshResult(job_id=job_id, created=created)


def _existing_job_id(session: Session, idempotency_key: str) -> UUID:
    job_id = session.scalar(
        select(CollectionJobRecord.id).where(
            CollectionJobRecord.idempotency_key == idempotency_key
        )
    )
    if job_id is None:
        raise RuntimeError("priority refresh idempotency conflict without an existing job")
    return job_id
