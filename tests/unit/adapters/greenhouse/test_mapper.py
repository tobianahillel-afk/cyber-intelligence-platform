from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from cip.adapters.sources.greenhouse.mapper import (
    greenhouse_job_fingerprint,
    map_greenhouse_job,
)
from cip.adapters.sources.greenhouse.registry import GreenhouseBoard
from cip.adapters.sources.greenhouse.schemas import GreenhouseJob
from cip.modules.opportunities.domain.entities import SignalType

NOW = datetime(2026, 8, 4, 12, 0, tzinfo=UTC)
BOARD = GreenhouseBoard(
    id="example",
    board_token="example",
    canonical_name="Example Security",
    country_code="FR",
)


def test_mapper_creates_deterministic_evidence_backed_job_signal() -> None:
    job = GreenhouseJob.model_validate(_job())
    retention = NOW + timedelta(days=365)

    first = map_greenhouse_job(
        BOARD,
        job,
        collection_job_id=uuid4(),
        collected_at=NOW,
        retention_until=retention,
    )
    second = map_greenhouse_job(
        BOARD,
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
    assert projection.organization.canonical_name == "Example Security"
    assert projection.organization.country_code == "FR"
    assert projection.signal.signal_type is SignalType.JOB_POSTING
    assert projection.signal.matched_terms == (
        "soc analyst",
        "security operations",
        "microsoft sentinel",
    )
    assert projection.signal.expires_at == NOW + timedelta(days=30)
    assert projection.signal.evidence_id == projection.evidence.id
    assert observation.source_record_key == "example:123"
    assert observation.source_updated_at == datetime(2026, 8, 4, 10, tzinfo=UTC)
    assert observation.payload_hash_sha256 == projection.evidence.content_hash_sha256
    assert "<p>" not in projection.evidence.summary
    assert "candidate@example.test" not in projection.evidence.summary


def test_fingerprint_changes_only_when_selected_public_job_fields_change() -> None:
    baseline = GreenhouseJob.model_validate(_job(metadata={"ignored": "first"}))
    same_selected_fields = GreenhouseJob.model_validate(_job(metadata={"ignored": "second"}))
    changed = GreenhouseJob.model_validate(
        _job(content="<p>SOC analyst using Splunk Enterprise Security.</p>")
    )

    assert greenhouse_job_fingerprint(baseline) == greenhouse_job_fingerprint(
        same_selected_fields
    )
    assert greenhouse_job_fingerprint(baseline) != greenhouse_job_fingerprint(changed)


def test_mapper_drops_non_security_job() -> None:
    job = GreenhouseJob.model_validate(
        _job(
            title="Senior Finance Manager",
            content="<p>Accounting, forecasting and procurement.</p>",
            departments=[{"id": 7, "name": "Finance"}],
        )
    )

    assert (
        map_greenhouse_job(
            BOARD,
            job,
            collection_job_id=uuid4(),
            collected_at=NOW,
            retention_until=NOW + timedelta(days=365),
        )
        is None
    )


def test_mapper_uses_description_and_department_for_detection() -> None:
    job = GreenhouseJob.model_validate(
        _job(
            title="Platform Engineer",
            content="<p>Build detection engineering and threat detection pipelines.</p>",
            departments=[{"id": 8, "name": "Security Operations"}],
        )
    )

    mapped = map_greenhouse_job(
        BOARD,
        job,
        collection_job_id=uuid4(),
        collected_at=NOW,
        retention_until=NOW + timedelta(days=365),
    )

    assert mapped is not None
    assert "security operations" in mapped[1].signal.matched_terms
    assert "detection engineering" in mapped[1].signal.matched_terms


def _job(**changes: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "id": 123,
        "internal_job_id": 456,
        "title": "Senior SOC Analyst",
        "updated_at": "2026-08-04T10:00:00Z",
        "absolute_url": "https://job-boards.greenhouse.io/example/jobs/123",
        "location": {"name": "Paris or remote"},
        "language": "en",
        "content": (
            "<p>Join our security operations team and operate Microsoft Sentinel.</p>"
            "<p>Application contact: candidate@example.test</p>"
        ),
        "departments": [{"id": 1, "name": "Security"}],
        "offices": [{"id": 1, "name": "Paris"}],
        "metadata": None,
    }
    payload.update(changes)
    return payload
