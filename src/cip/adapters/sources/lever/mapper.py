from __future__ import annotations

from datetime import datetime
from uuid import UUID

from cip.adapters.sources.canonical_jobs import (
    CanonicalPublicJob,
    map_canonical_public_job,
)
from cip.adapters.sources.lever.registry import LeverSite
from cip.adapters.sources.lever.schemas import LeverPosting
from cip.modules.collection_orchestration.application.ports import CommercialProjection
from cip.modules.raw_observations.domain.entities import RawObservation

SOURCE_ID = "lever-job-board"
ADAPTER_ID = "lever-postings-api"
ADAPTER_VERSION = "1.0.0"


def lever_posting_to_canonical(
    site: LeverSite,
    posting: LeverPosting,
) -> CanonicalPublicJob:
    department = posting.categories.department or posting.categories.team
    return CanonicalPublicJob(
        source_id=SOURCE_ID,
        adapter_id=ADAPTER_ID,
        adapter_version=ADAPTER_VERSION,
        provider_label="Lever",
        schema_fingerprint="lever-postings-v0-json-1",
        site_id=site.site_token,
        organization_key=site.id,
        organization_name=site.canonical_name,
        country_code=site.country_code,
        source_job_id=posting.id,
        title=posting.text,
        source_url=str(posting.hosted_url),
        published_at=posting.published_at,
        description_text=posting.description_text(),
        location=posting.categories.normalized_location(),
        department=department,
        employment_type=posting.categories.commitment,
        seniority=None,
        language=None,
    )


def map_lever_posting(
    site: LeverSite,
    posting: LeverPosting,
    *,
    collection_job_id: UUID,
    collected_at: datetime,
    retention_until: datetime,
) -> tuple[RawObservation, CommercialProjection] | None:
    return map_canonical_public_job(
        lever_posting_to_canonical(site, posting),
        collection_job_id=collection_job_id,
        collected_at=collected_at,
        retention_until=retention_until,
    )
