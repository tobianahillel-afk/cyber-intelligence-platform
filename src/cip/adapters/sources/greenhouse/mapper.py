from __future__ import annotations

import json
from datetime import datetime, timedelta
from hashlib import sha256
from uuid import NAMESPACE_URL, UUID, uuid5

from cip.adapters.sources.greenhouse.html_text import html_to_text
from cip.adapters.sources.greenhouse.registry import GreenhouseBoard
from cip.adapters.sources.greenhouse.schemas import GreenhouseJob
from cip.adapters.sources.job_signals import matched_job_terms
from cip.modules.collection_orchestration.application.ports import CommercialProjection
from cip.modules.evidence.domain.entities import Evidence
from cip.modules.opportunities.domain.entities import CommercialSignal, SignalType
from cip.modules.organizations.domain.entities import Organization
from cip.modules.raw_observations.domain.entities import RawObservation
from cip.modules.source_governance.domain.models import DataCategory
from cip.shared.kernel.time import require_aware_utc

SOURCE_ID = "greenhouse-job-board"
ADAPTER_ID = "greenhouse-job-board-api"
ADAPTER_VERSION = "1.0.0"
SIGNAL_TTL_DAYS = 30


def greenhouse_job_fingerprint(job: GreenhouseJob) -> str:
    description = html_to_text(job.content)
    payload = _selected_payload(job, description=description)
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return sha256(encoded).hexdigest()


def map_greenhouse_job(
    board: GreenhouseBoard,
    job: GreenhouseJob,
    *,
    collection_job_id: UUID,
    collected_at: datetime,
    retention_until: datetime,
) -> tuple[RawObservation, CommercialProjection] | None:
    collected = require_aware_utc(collected_at, field_name="collected_at")
    description = html_to_text(job.content)
    departments = job.department_names()
    matched_terms = matched_job_terms(job.title, description, *departments)
    if not matched_terms:
        return None
    payload_hash = greenhouse_job_fingerprint(job)
    source_updated_at = require_aware_utc(job.updated_at, field_name="updated_at")
    source_record_key = f"{board.board_token}:{job.id}"
    organization_id = uuid5(NAMESPACE_URL, f"greenhouse:board:{board.board_token}")
    evidence_id = uuid5(NAMESPACE_URL, f"greenhouse:job:{source_record_key}")
    summary = _summary(board, job, matched_terms=matched_terms)
    organization = Organization(
        id=organization_id,
        canonical_name=board.canonical_name,
        legal_name=board.canonical_name,
        country_code=board.country_code,
        created_at=collected,
        updated_at=collected,
    )
    evidence = Evidence(
        id=evidence_id,
        source_id=SOURCE_ID,
        source_record_key=source_record_key,
        source_url=str(job.absolute_url),
        summary=summary,
        confidence=0.85,
        collected_at=collected,
        published_at=source_updated_at,
        content_hash_sha256=payload_hash,
        raw_storage_permitted=False,
        retention_until=retention_until,
    )
    signal = CommercialSignal(
        id=uuid5(NAMESPACE_URL, f"greenhouse:signal:{source_record_key}"),
        organization_id=organization_id,
        evidence_id=evidence_id,
        signal_type=SignalType.JOB_POSTING,
        title=job.title,
        summary=summary,
        confidence=0.85,
        matched_terms=matched_terms,
        published_at=source_updated_at,
        collected_at=collected,
        expires_at=collected + timedelta(days=SIGNAL_TTL_DAYS),
        created_at=collected,
    )
    observation = RawObservation(
        source_id=SOURCE_ID,
        adapter_id=ADAPTER_ID,
        adapter_version=ADAPTER_VERSION,
        collection_job_id=collection_job_id,
        source_record_type="public_job_posting",
        source_record_key=source_record_key,
        source_url=str(job.absolute_url),
        payload_hash_sha256=payload_hash,
        data_categories=frozenset({DataCategory.PUBLIC_JOB_POSTING}),
        collected_at=collected,
        published_at=source_updated_at,
        source_updated_at=source_updated_at,
        schema_fingerprint="greenhouse-job-board-v1-content-1",
        content_language=job.language,
        classification="internal",
        retention_until=retention_until,
    )
    return observation, CommercialProjection(organization, evidence, signal)


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


def _summary(
    board: GreenhouseBoard,
    job: GreenhouseJob,
    *,
    matched_terms: tuple[str, ...],
) -> str:
    location = job.location.name.strip()
    terms = ", ".join(matched_terms[:8])
    return (
        f"Greenhouse public job posting from {board.canonical_name}: {job.title}. "
        f"Location: {location}. Matched security-operations terms: {terms}."
    )
