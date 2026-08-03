from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime

from sqlalchemy.orm import Session

from cip.modules.collection_orchestration.domain.models import CollectionJob, SourceSchedule
from cip.modules.collection_orchestration.infrastructure.repository import (
    enqueue_job,
    has_active_job,
)
from cip.shared.kernel.time import require_aware_utc


def schedule_due_jobs(
    session: Session,
    schedules: Iterable[SourceSchedule],
    *,
    now: datetime,
) -> int:
    current = require_aware_utc(now, field_name="now")
    created = 0
    for schedule in schedules:
        if not schedule.enabled:
            continue
        if has_active_job(
            session,
            source_id=schedule.source_id,
            adapter_id=schedule.adapter_id,
        ):
            continue
        slot = schedule.slot_for(current)
        job = CollectionJob.from_schedule(schedule, scheduled_for=slot)
        if enqueue_job(session, job):
            created += 1
    return created
