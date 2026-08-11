from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from hashlib import sha256
from urllib.parse import urlsplit
from uuid import NAMESPACE_URL, UUID, uuid5

from cip.adapters.sources.job_signals import matched_job_terms
from cip.modules.collection_orchestration.application.ports import CommercialProjection
from cip.modules.evidence.domain.entities import Evidence
from cip.modules.opportunities.domain.entities import CommercialSignal, SignalType
from cip.modules.organizations.domain.entities import Organization
from cip.modules.raw_observations.domain.entities import RawObservation
from cip.modules.source_governance.domain.models import DataCategory
from cip.shared.kernel.time import require_aware_utc

_SIGNAL_TTL_DAYS = 30
_SPACE_PATTERN = re.compile(r"\s+")


@dataclass(frozen=True, slots=True)
class CanonicalPublicJob:
    source_id: str
    adapter_id: str
    adapter_version: str
    provider_label: str
    schema_fingerprint: str
    site_id: str
    organization_key: str
    organization_name: str
    country_code: str | None
    source_job_id: str
    title: str
    source_url: str
    published_at: datetime
    description_text: str
    location: str
    department: str | None = None
    employment_type: str | None = None
    seniority: str | None = None
    language: str | None = None
    confidence: float = 0.85

    def __post_init__(self) -> None:
        required = (
            "source_id",
            "adapter_id",
            "adapter_version",
            "provider_label",
            "schema_fingerprint",
            "site_id",
            "organization_key",
            "organization_name",
            "source_job_id",
            "title",
            "source_url",
            "location",
        )
        for field_name in required:
            value = getattr(self, field_name)
            normalized = value.strip()
            if not normalized:
                raise ValueError(f"{field_name} is required")
            object.__setattr__(self, field_name, normalized)
        parsed_url = urlsplit(self.source_url)
        if parsed_url.scheme != "https" or not parsed_url.hostname:
            raise ValueError("source_url must be an absolute HTTPS URL")
        published = require_aware_utc(self.published_at, field_name="published_at")
        object.__setattr__(self, "published_at", published)
        if self.country_code is not None:
            country = self.country_code.strip().upper()
            if len(country) != 2 or not country.isalpha():
                raise ValueError("country_code must be an ISO alpha-2 code")
            object.__setattr__(self, "country_code", country)
        if not 0 <= self.confidence <= 1:
            raise ValueError("confidence must be between 0 and 1")

    @property
    def source_record_key(self) -> str:
        return f"{self.site_id}:{self.source_job_id}"

    @property
    def organization_id(self) -> UUID:
        return uuid5(NAMESPACE_URL, f"organization:{self.organization_key.casefold()}")

    @property
    def exact_match_candidate_key(self) -> str:
        components = (
            self.organization_key,
            self.title,
            self.location,
            self.department or "",
            self.employment_type or "",
        )
        normalized = "|".join(_normalize_component(value) for value in components)
        return sha256(normalized.encode()).hexdigest()

    def fingerprint(self) -> str:
        encoded = json.dumps(
            self.selected_payload(),
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
        return sha256(encoded).hexdigest()

    def selected_payload(self) -> dict[str, object]:
        return {
            "provider": self.source_id,
            "site_id": self.site_id,
            "source_job_id": self.source_job_id,
            "title": self.title,
            "source_url": self.source_url,
            "published_at": self.published_at.isoformat(),
            "description_text": self.description_text,
            "location": self.location,
            "department": self.department,
            "employment_type": self.employment_type,
            "seniority": self.seniority,
            "language": self.language,
        }


def canonical_public_job_observation(
    job: CanonicalPublicJob,
    *,
    collection_job_id: UUID,
    collected_at: datetime,
    retention_until: datetime,
) -> RawObservation:
    collected = require_aware_utc(collected_at, field_name="collected_at")
    return RawObservation(
        source_id=job.source_id,
        adapter_id=job.adapter_id,
        adapter_version=job.adapter_version,
        collection_job_id=collection_job_id,
        source_record_type="public_job_posting",
        source_record_key=job.source_record_key,
        source_url=job.source_url,
        payload_hash_sha256=job.fingerprint(),
        data_categories=frozenset({DataCategory.PUBLIC_JOB_POSTING}),
        collected_at=collected,
        published_at=job.published_at,
        source_updated_at=job.published_at,
        schema_fingerprint=job.schema_fingerprint,
        content_language=job.language,
        classification="internal",
        retention_until=retention_until,
    )


def map_canonical_public_job(
    job: CanonicalPublicJob,
    *,
    collection_job_id: UUID,
    collected_at: datetime,
    retention_until: datetime,
) -> tuple[RawObservation, CommercialProjection] | None:
    collected = require_aware_utc(collected_at, field_name="collected_at")
    matched_terms = matched_job_terms(
        job.title,
        job.description_text,
        job.department or "",
        job.seniority or "",
    )
    if not matched_terms:
        return None
    payload_hash = job.fingerprint()
    evidence_id = uuid5(
        NAMESPACE_URL,
        f"{job.source_id}:job:{job.source_record_key}",
    )
    summary = _summary(job, matched_terms)
    organization = Organization(
        id=job.organization_id,
        canonical_name=job.organization_name,
        legal_name=job.organization_name,
        country_code=job.country_code,
        created_at=collected,
        updated_at=collected,
    )
    evidence = Evidence(
        id=evidence_id,
        source_id=job.source_id,
        source_record_key=job.source_record_key,
        source_url=job.source_url,
        summary=summary,
        confidence=job.confidence,
        collected_at=collected,
        published_at=job.published_at,
        content_hash_sha256=payload_hash,
        raw_storage_permitted=False,
        retention_until=retention_until,
    )
    signal = CommercialSignal(
        id=uuid5(
            NAMESPACE_URL,
            f"{job.source_id}:signal:{job.source_record_key}",
        ),
        organization_id=job.organization_id,
        evidence_id=evidence_id,
        signal_type=SignalType.JOB_POSTING,
        title=job.title,
        summary=summary,
        confidence=job.confidence,
        matched_terms=matched_terms,
        published_at=job.published_at,
        collected_at=collected,
        expires_at=collected + timedelta(days=_SIGNAL_TTL_DAYS),
        created_at=collected,
    )
    observation = canonical_public_job_observation(
        job,
        collection_job_id=collection_job_id,
        collected_at=collected,
        retention_until=retention_until,
    )
    return observation, CommercialProjection(organization, evidence, signal)


def exact_cross_provider_match(
    left: CanonicalPublicJob,
    right: CanonicalPublicJob,
) -> bool:
    if left.source_id == right.source_id:
        return False
    return left.exact_match_candidate_key == right.exact_match_candidate_key


def _summary(job: CanonicalPublicJob, matched_terms: tuple[str, ...]) -> str:
    terms = ", ".join(matched_terms[:8])
    details = [f"Location: {job.location}"]
    if job.department:
        details.append(f"Department: {job.department}")
    if job.employment_type:
        details.append(f"Employment: {job.employment_type}")
    return (
        f"{job.provider_label} public job posting from {job.organization_name}: "
        f"{job.title}. {'; '.join(details)}. "
        f"Matched security-operations terms: {terms}."
    )


def _normalize_component(value: str) -> str:
    return _SPACE_PATTERN.sub(" ", value.strip().casefold())
