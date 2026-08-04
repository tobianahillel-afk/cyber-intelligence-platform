from __future__ import annotations

from datetime import datetime
from uuid import UUID

from cip.adapters.sources.canonical_jobs import (
    CanonicalPublicJob,
    map_canonical_public_job,
)
from cip.adapters.sources.job_text import html_to_text
from cip.adapters.sources.smartrecruiters.registry import SmartRecruitersCompany
from cip.adapters.sources.smartrecruiters.schemas import (
    SmartRecruitersPostingDetail,
    SmartRecruitersPostingSummary,
)
from cip.modules.collection_orchestration.application.ports import CommercialProjection
from cip.modules.raw_observations.domain.entities import RawObservation

SOURCE_ID = "smartrecruiters-job-board"
ADAPTER_ID = "smartrecruiters-posting-api"
ADAPTER_VERSION = "1.0.0"


def smartrecruiters_posting_to_canonical(
    company: SmartRecruitersCompany,
    summary: SmartRecruitersPostingSummary,
    detail: SmartRecruitersPostingDetail,
) -> CanonicalPublicJob:
    source_url = str(detail.posting_url or summary.ref)
    description = " ".join(
        part
        for part in (
            html_to_text(html_part)
            for html_part in detail.job_ad.sections.html_parts()
        )
        if part
    )
    department = detail.department or summary.department
    employment = detail.type_of_employment or summary.type_of_employment
    experience = detail.experience_level or summary.experience_level
    return CanonicalPublicJob(
        source_id=SOURCE_ID,
        adapter_id=ADAPTER_ID,
        adapter_version=ADAPTER_VERSION,
        provider_label="SmartRecruiters",
        schema_fingerprint="smartrecruiters-posting-api-v1-detail-1",
        site_id=company.company_identifier,
        organization_key=company.id,
        organization_name=company.canonical_name,
        country_code=company.country_code,
        source_job_id=detail.id,
        title=detail.name,
        source_url=source_url,
        published_at=detail.released_date,
        description_text=description,
        location=detail.location.display_name(),
        department=department.label if department else None,
        employment_type=employment.label if employment else None,
        seniority=experience.label if experience else None,
        language=None,
    )


def map_smartrecruiters_posting(
    company: SmartRecruitersCompany,
    summary: SmartRecruitersPostingSummary,
    detail: SmartRecruitersPostingDetail,
    *,
    collection_job_id: UUID,
    collected_at: datetime,
    retention_until: datetime,
) -> tuple[RawObservation, CommercialProjection] | None:
    return map_canonical_public_job(
        smartrecruiters_posting_to_canonical(company, summary, detail),
        collection_job_id=collection_job_id,
        collected_at=collected_at,
        retention_until=retention_until,
    )
