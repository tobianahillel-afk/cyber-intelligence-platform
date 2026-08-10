from __future__ import annotations

from datetime import datetime
from uuid import UUID

from cip.adapters.sources.canonical_jobs import CanonicalPublicJob, map_canonical_public_job
from cip.adapters.sources.job_text import html_to_text
from cip.adapters.sources.teamtailor.registry import TeamtailorAccount
from cip.adapters.sources.teamtailor.schemas import TeamtailorJobResource
from cip.modules.collection_orchestration.application.ports import CommercialProjection
from cip.modules.raw_observations.domain.entities import RawObservation

SOURCE_ID = "teamtailor-public-jobs"
ADAPTER_ID = "teamtailor-public-read-jobs-api"
ADAPTER_VERSION = "1.0.0"


def teamtailor_job_to_canonical(
    account: TeamtailorAccount,
    job: TeamtailorJobResource,
) -> CanonicalPublicJob:
    description = " ".join(
        part
        for part in (
            html_to_text(job.attributes.pitch),
            html_to_text(job.attributes.body),
        )
        if part
    )
    source_url = (
        str(job.links.self_url)
        if job.links.self_url is not None
        else f"{account.jobs_url}/{job.id}"
    )
    remote = (job.attributes.remote_status or "").strip()
    location = remote if remote else "Unspecified"
    return CanonicalPublicJob(
        source_id=SOURCE_ID,
        adapter_id=ADAPTER_ID,
        adapter_version=ADAPTER_VERSION,
        provider_label="Teamtailor",
        schema_fingerprint="teamtailor-jsonapi-public-jobs-v1",
        site_id=account.id,
        organization_key=account.id,
        organization_name=account.canonical_name,
        country_code=account.country_code,
        source_job_id=job.id,
        title=job.attributes.title,
        source_url=source_url,
        published_at=job.attributes.created_at,
        description_text=description,
        location=location,
        department=None,
        employment_type=job.attributes.employment_type,
        seniority=None,
        language=None,
    )


def map_teamtailor_job(
    account: TeamtailorAccount,
    job: TeamtailorJobResource,
    *,
    collection_job_id: UUID,
    collected_at: datetime,
    retention_until: datetime,
) -> tuple[RawObservation, CommercialProjection] | None:
    return map_canonical_public_job(
        teamtailor_job_to_canonical(account, job),
        collection_job_id=collection_job_id,
        collected_at=collected_at,
        retention_until=retention_until,
    )
