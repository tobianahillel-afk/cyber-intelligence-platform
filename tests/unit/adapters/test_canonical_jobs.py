from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from cip.adapters.sources.canonical_jobs import (
    CanonicalPublicJob,
    exact_cross_provider_match,
    map_canonical_public_job,
)
from cip.modules.opportunities.domain.entities import SignalType

NOW = datetime(2026, 8, 4, 14, 0, tzinfo=UTC)


def test_canonical_job_maps_to_deterministic_evidence_backed_signal() -> None:
    job = _job()
    retention = NOW + timedelta(days=365)

    first = map_canonical_public_job(
        job,
        collection_job_id=uuid4(),
        collected_at=NOW,
        retention_until=retention,
    )
    second = map_canonical_public_job(
        job,
        collection_job_id=uuid4(),
        collected_at=NOW,
        retention_until=retention,
    )

    assert first is not None and second is not None
    observation, projection = first
    assert projection.organization.id == second[1].organization.id
    assert projection.evidence.id == second[1].evidence.id
    assert projection.signal.id == second[1].signal.id
    assert projection.signal.signal_type is SignalType.JOB_POSTING
    assert projection.signal.matched_terms == (
        "soc analyst",
        "security operations",
        "microsoft sentinel",
    )
    assert projection.signal.expires_at == NOW + timedelta(days=30)
    assert observation.source_record_key == "example:job-123"
    assert observation.payload_hash_sha256 == projection.evidence.content_hash_sha256
    assert observation.schema_fingerprint == "provider-schema-v1"
    assert "Department: Security" in projection.evidence.summary
    assert "Employment: Full-time" in projection.evidence.summary


def test_canonical_job_drops_irrelevant_posting() -> None:
    job = replace(
        _job(),
        title="Finance Manager",
        description_text="Accounting and forecasting.",
        department="Finance",
    )

    assert (
        map_canonical_public_job(
            job,
            collection_job_id=uuid4(),
            collected_at=NOW,
            retention_until=NOW + timedelta(days=365),
        )
        is None
    )


def test_fingerprint_and_cross_provider_match_are_explicit() -> None:
    lever = _job(source_id="lever-job-board", adapter_id="lever-postings-api")
    same = replace(
        lever,
        source_id="smartrecruiters-job-board",
        adapter_id="smartrecruiters-posting-api",
        site_id="smart-example",
        source_job_id="different-provider-id",
    )
    ambiguous = replace(same, location="Lyon")
    changed = replace(lever, description_text="SOC analyst using Splunk ES.")

    assert lever.fingerprint() != changed.fingerprint()
    assert exact_cross_provider_match(lever, same) is True
    assert exact_cross_provider_match(lever, ambiguous) is False
    assert exact_cross_provider_match(lever, lever) is False


def test_canonical_job_validates_required_fields_url_country_time_and_confidence() -> None:
    with pytest.raises(ValueError, match="title is required"):
        replace(_job(), title=" ")
    with pytest.raises(ValueError, match="absolute HTTPS"):
        replace(_job(), source_url="http://example.test/job")
    with pytest.raises(ValueError, match="country_code"):
        replace(_job(), country_code="FRA")
    with pytest.raises(ValueError, match="timezone-aware"):
        replace(_job(), published_at=datetime(2026, 8, 4, 12, 0))
    with pytest.raises(ValueError, match="confidence"):
        replace(_job(), confidence=1.1)


def test_optional_summary_fields_can_be_absent() -> None:
    job = replace(
        _job(),
        country_code=None,
        department=None,
        employment_type=None,
        seniority=None,
        language=None,
    )

    mapped = map_canonical_public_job(
        job,
        collection_job_id=uuid4(),
        collected_at=NOW,
        retention_until=NOW + timedelta(days=365),
    )

    assert mapped is not None
    assert mapped[1].organization.country_code is None
    assert "Department:" not in mapped[1].evidence.summary
    assert "Employment:" not in mapped[1].evidence.summary


def _job(**changes: object) -> CanonicalPublicJob:
    values: dict[str, object] = {
        "source_id": "lever-job-board",
        "adapter_id": "lever-postings-api",
        "adapter_version": "1.0.0",
        "provider_label": "Lever",
        "schema_fingerprint": "provider-schema-v1",
        "site_id": "example",
        "organization_key": "example-security",
        "organization_name": "Example Security",
        "country_code": "FR",
        "source_job_id": "job-123",
        "title": "Senior SOC Analyst",
        "source_url": "https://jobs.example.test/job-123",
        "published_at": datetime(2026, 8, 4, 10, 0, tzinfo=UTC),
        "description_text": (
            "Join our security operations team and operate Microsoft Sentinel."
        ),
        "location": "Paris or remote",
        "department": "Security",
        "employment_type": "Full-time",
        "seniority": "Senior",
        "language": "en",
        "confidence": 0.85,
    }
    values.update(changes)
    return CanonicalPublicJob(**values)  # type: ignore[arg-type]
