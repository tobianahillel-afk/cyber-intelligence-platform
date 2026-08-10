from __future__ import annotations

from datetime import datetime
from uuid import UUID

from cip.adapters.sources.canonical_jobs import CanonicalPublicJob, map_canonical_public_job
from cip.adapters.sources.job_text import html_to_text
from cip.adapters.sources.recruitee.registry import RecruiteeCareerSite
from cip.adapters.sources.recruitee.schemas import RecruiteeOffer
from cip.modules.collection_orchestration.application.ports import CommercialProjection
from cip.modules.raw_observations.domain.entities import RawObservation

SOURCE_ID = "recruitee-careers-site"
ADAPTER_ID = "recruitee-careers-site-api"
ADAPTER_VERSION = "1.0.0"


def recruitee_offer_to_canonical(
    site: RecruiteeCareerSite,
    offer: RecruiteeOffer,
) -> CanonicalPublicJob:
    description = " ".join(
        part
        for part in (
            html_to_text(offer.description),
            html_to_text(offer.requirements),
        )
        if part
    )
    return CanonicalPublicJob(
        source_id=SOURCE_ID,
        adapter_id=ADAPTER_ID,
        adapter_version=ADAPTER_VERSION,
        provider_label="Recruitee",
        schema_fingerprint="recruitee-careers-site-offers-v1",
        site_id=site.subdomain,
        organization_key=site.id,
        organization_name=site.canonical_name,
        country_code=site.country_code,
        source_job_id=offer.source_job_id,
        title=offer.title,
        source_url=site.job_url(offer.slug),
        published_at=offer.effective_published_at,
        description_text=description,
        location=offer.display_location(),
        department=offer.department_name(),
        employment_type=offer.employment_type_code,
        seniority=None,
        language=None,
    )


def map_recruitee_offer(
    site: RecruiteeCareerSite,
    offer: RecruiteeOffer,
    *,
    collection_job_id: UUID,
    collected_at: datetime,
    retention_until: datetime,
) -> tuple[RawObservation, CommercialProjection] | None:
    return map_canonical_public_job(
        recruitee_offer_to_canonical(site, offer),
        collection_job_id=collection_job_id,
        collected_at=collected_at,
        retention_until=retention_until,
    )
