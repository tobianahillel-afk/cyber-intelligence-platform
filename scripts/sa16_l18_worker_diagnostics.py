from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session, sessionmaker

from cip.modules.collection_orchestration.infrastructure.models import CollectionJobRecord


def worker_failure_detail(
    factory: sessionmaker[Session],
    job_id: UUID | None,
) -> str:
    if job_id is None:
        return "job_id=none"
    with factory() as session:
        record = session.get(CollectionJobRecord, job_id)
        if record is None:
            return f"job_id={job_id} record=missing"
        return (
            f"job_id={job_id} error_code={record.error_code} "
            f"error_message={record.error_message}"
        )
