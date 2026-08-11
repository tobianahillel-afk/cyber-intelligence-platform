from __future__ import annotations

from datetime import datetime
from uuid import UUID

from cip.adapters.sources.ashby.registry import AshbyBoard
from cip.adapters.sources.ashby.schemas import AshbyJobPosting
from cip.adapters.sources.canonical_jobs import CanonicalPublicJob, map_canonical_public_job
from cip.modules.collection_orchestration.application.ports import CommercialProjection
from cip.modules.raw_observations.domain.entities import RawObservation

SOURCE_ID = "ashby-job-board"
ADAPTER_ID = "ashby-public-job-postings-api"
ADAPTER_VERSION = "1.0.0"


def ashby_job_to_canonical(
    board: AshbyBoard,
    job: AshbyJobPosting,
) -> CanonicalPublicJob:
    department = job.department or job.team
    seniority = job.team if job.department and job.team else None
    return CanonicalPublicJob(
        source_id=SOURCE_ID,
        adapter_id=ADAPTER_ID,
        adapter_version=ADAPTER_VERSION,
        provider_label="Ashby",
        schema_fingerprint="ashby-public-job-posting-v1",
        site_id=board.board_name,
        organization_key=board.id,
        organization_name=board.canonical_name,
        country_code=board.country_code,
        source_job_id=job.source_job_id,
        title=job.title,
        source_url=str(job.job_url),
        published_at=job.published_at,
        description_text=job.description_plain,
        location=job.display_location(),
        department=department,
        employment_type=job.employment_type,
        seniority=seniority,
        language=None,
    )


def map_ashby_job(
    board: AshbyBoard,
    job: AshbyJobPosting,
    *,
    collection_job_id: UUID,
    collected_at: datetime,
    retention_until: datetime,
) -> tuple[RawObservation, CommercialProjection] | None:
    return map_canonical_public_job(
        ashby_job_to_canonical(board, job),
        collection_job_id=collection_job_id,
        collected_at=collected_at,
        retention_until=retention_until,
    )
