from __future__ import annotations

import json
from datetime import datetime
from hashlib import sha256
from uuid import UUID

from cip.adapters.sources.canonical_jobs import (
    CanonicalPublicJob,
    map_canonical_public_job,
)
from cip.adapters.sources.greenhouse.html_text import html_to_text
from cip.adapters.sources.greenhouse.registry import GreenhouseBoard
from cip.adapters.sources.greenhouse.schemas import GreenhouseJob
from cip.modules.collection_orchestration.application.ports import CommercialProjection
from cip.modules.raw_observations.domain.entities import RawObservation

SOURCE_ID = "greenhouse-job-board"
ADAPTER_ID = "greenhouse-job-board-api"
ADAPTER_VERSION = "1.1.0"


def greenhouse_job_fingerprint(job: GreenhouseJob) -> str:
    description = html_to_text(job.content)
    payload = _selected_payload(job, description=description)
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return sha256(encoded).hexdigest()


def greenhouse_job_to_canonical(
    board: GreenhouseBoard,
    job: GreenhouseJob,
) -> CanonicalPublicJob:
    departments = job.department_names()
    return CanonicalPublicJob(
        source_id=SOURCE_ID,
        adapter_id=ADAPTER_ID,
        adapter_version=ADAPTER_VERSION,
        provider_label="Greenhouse",
        schema_fingerprint="greenhouse-job-board-v1-content-1",
        site_id=board.board_token,
        organization_key=board.id,
        organization_name=board.canonical_name,
        country_code=board.country_code,
        source_job_id=str(job.id),
        title=job.title,
        source_url=str(job.absolute_url),
        published_at=job.updated_at,
        description_text=html_to_text(job.content),
        location=job.location.name,
        department=departments[0] if departments else None,
        language=job.language,
    )


def map_greenhouse_job(
    board: GreenhouseBoard,
    job: GreenhouseJob,
    *,
    collection_job_id: UUID,
    collected_at: datetime,
    retention_until: datetime,
) -> tuple[RawObservation, CommercialProjection] | None:
    return map_canonical_public_job(
        greenhouse_job_to_canonical(board, job),
        collection_job_id=collection_job_id,
        collected_at=collected_at,
        retention_until=retention_until,
    )


def _selected_payload(job: GreenhouseJob, *, description: str) -> dict[str, object]:
    return {
        "id": job.id,
        "internal_job_id": job.internal_job_id,
        "title": job.title,
        "updated_at": job.updated_at.isoformat(),
        "absolute_url": str(job.absolute_url),
        "location": job.location.name,
        "language": job.language,
        "departments": job.department_names(),
        "offices": job.office_names(),
        "description": description,
    }
