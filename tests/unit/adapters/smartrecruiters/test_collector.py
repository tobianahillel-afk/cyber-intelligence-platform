from __future__ import annotations

import json
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest

from cip.adapters.sources.smartrecruiters.client import SmartRecruitersFetchResult
from cip.adapters.sources.smartrecruiters.collector import (
    SmartRecruitersCheckpoint,
    SmartRecruitersCollectionDeniedError,
    SmartRecruitersSourceSchemaError,
    SmartRecruitersSourceWindowError,
    collect_smartrecruiters_jobs,
)
from cip.adapters.sources.smartrecruiters.mapper import (
    smartrecruiters_posting_to_canonical,
)
from cip.adapters.sources.smartrecruiters.registry import SmartRecruitersCompany
from cip.adapters.sources.smartrecruiters.schemas import (
    SmartRecruitersPostingDetail,
    SmartRecruitersPostingSummary,
)
from cip.modules.source_governance.domain.models import SourceStatus
from cip.modules.source_governance.infrastructure.registry import (
    SourceRegistryEntry,
    load_source_registry,
)

NOW = datetime(2026, 8, 4, 14, 0, tzinfo=UTC)
COMPANY = SmartRecruitersCompany(
    id="example-security",
    company_identifier="example",
    canonical_name="Example Security",
    country_code="FR",
)


class StubSmartRecruitersClient:
    def __init__(
        self,
        pages: dict[int, object],
        details: dict[str, object],
    ) -> None:
        self.pages = pages
        self.details = details
        self.list_calls: list[tuple[str, int, int]] = []
        self.detail_calls: list[tuple[str, str]] = []

    def postings_url(self, company_identifier: str) -> str:
        return f"https://api.smartrecruiters.com/v1/companies/{company_identifier}/postings"

    def posting_url(self, company_identifier: str, posting_id: str) -> str:
        return f"{self.postings_url(company_identifier)}/{posting_id}"

    def fetch_postings(
        self,
        company_identifier: str,
        *,
        offset: int,
        limit: int,
    ) -> SmartRecruitersFetchResult:
        self.list_calls.append((company_identifier, offset, limit))
        return SmartRecruitersFetchResult(
            body=json.dumps(self.pages[offset]).encode(),
            request_url=self.postings_url(company_identifier),
        )

    def fetch_posting(
        self,
        company_identifier: str,
        posting_id: str,
    ) -> SmartRecruitersFetchResult:
        self.detail_calls.append((company_identifier, posting_id))
        return SmartRecruitersFetchResult(
            body=json.dumps(self.details[posting_id]).encode(),
            request_url=self.posting_url(company_identifier, posting_id),
        )


def test_collector_paginates_details_and_emits_changed_relevant_jobs() -> None:
    unchanged_summary = SmartRecruitersPostingSummary.model_validate(
        _summary("job-2", "SIEM Engineer")
    )
    unchanged_detail = SmartRecruitersPostingDetail.model_validate(
        _detail("job-2", "SIEM Engineer")
    )
    fingerprint = smartrecruiters_posting_to_canonical(
        COMPANY,
        unchanged_summary,
        unchanged_detail,
    ).fingerprint()
    previous = SmartRecruitersCheckpoint(
        {"example-security": {"job-2": fingerprint, "removed": "old"}}
    )
    client = StubSmartRecruitersClient(
        {
            0: _page(
                0,
                2,
                3,
                [
                    _summary("job-1", "Senior SOC Analyst"),
                    unchanged_summary.model_dump(mode="json", by_alias=True),
                ],
            ),
            2: _page(2, 2, 3, [_summary("job-3", "Finance Manager")]),
        },
        {
            "job-1": _detail("job-1", "Senior SOC Analyst"),
            "job-2": unchanged_detail.model_dump(mode="json", by_alias=True),
            "job-3": _detail("job-3", "Finance Manager", relevant=False),
        },
    )

    batch = collect_smartrecruiters_jobs(
        client,  # type: ignore[arg-type]
        _entry(),
        (COMPANY,),
        collection_job_id=uuid4(),
        collected_at=NOW,
        retention_until=NOW + timedelta(days=365),
        checkpoint=previous,
        page_size=2,
    )

    assert client.list_calls == [("example", 0, 2), ("example", 2, 2)]
    assert client.detail_calls == [
        ("example", "job-1"),
        ("example", "job-2"),
        ("example", "job-3"),
    ]
    assert batch.not_modified is False
    assert set(batch.checkpoint.fingerprints["example-security"]) == {
        "job-1",
        "job-2",
        "job-3",
    }
    assert {item.source_record_key for item in batch.observations} == {
        "example:job-1"
    }
    assert {item.signal.title for item in batch.projections} == {
        "Senior SOC Analyst",
        "SIEM Engineer",
    }


def test_unchanged_job_refreshes_projection_without_observation() -> None:
    summary = SmartRecruitersPostingSummary.model_validate(
        _summary("job-1", "Senior SOC Analyst")
    )
    detail = SmartRecruitersPostingDetail.model_validate(
        _detail("job-1", "Senior SOC Analyst")
    )
    fingerprint = smartrecruiters_posting_to_canonical(
        COMPANY,
        summary,
        detail,
    ).fingerprint()
    client = StubSmartRecruitersClient(
        {0: _page(0, 100, 1, [summary.model_dump(mode="json", by_alias=True)])},
        {"job-1": detail.model_dump(mode="json", by_alias=True)},
    )

    batch = collect_smartrecruiters_jobs(
        client,  # type: ignore[arg-type]
        _entry(),
        (COMPANY,),
        collection_job_id=uuid4(),
        collected_at=NOW,
        retention_until=NOW + timedelta(days=365),
        checkpoint=SmartRecruitersCheckpoint(
            {"example-security": {"job-1": fingerprint}}
        ),
    )

    assert batch.not_modified is True
    assert batch.observations == ()
    assert len(batch.projections) == 1
    assert batch.projections[0].signal.expires_at == NOW + timedelta(days=30)


def test_removed_job_changes_checkpoint_and_stops_projection_refresh() -> None:
    batch = collect_smartrecruiters_jobs(
        StubSmartRecruitersClient(
            {0: _page(0, 100, 0, [])},
            {},
        ),  # type: ignore[arg-type]
        _entry(),
        (COMPANY,),
        collection_job_id=uuid4(),
        collected_at=NOW,
        retention_until=NOW + timedelta(days=365),
        checkpoint=SmartRecruitersCheckpoint(
            {"example-security": {"job-1": "old"}}
        ),
    )

    assert batch.not_modified is False
    assert batch.checkpoint.fingerprints == {"example-security": {}}
    assert batch.observations == ()
    assert batch.projections == ()


def test_collector_rejects_schema_pagination_duplicate_detail_and_window_errors() -> None:
    with pytest.raises(SmartRecruitersSourceSchemaError, match="list schema"):
        collect_smartrecruiters_jobs(
            StubSmartRecruitersClient({0: {"invalid": True}}, {}),  # type: ignore[arg-type]
            _entry(),
            (COMPANY,),
            collection_job_id=uuid4(),
            collected_at=NOW,
            retention_until=NOW + timedelta(days=365),
        )

    with pytest.raises(SmartRecruitersSourceSchemaError, match="unexpected pagination"):
        collect_smartrecruiters_jobs(
            StubSmartRecruitersClient(
                {0: _page(1, 100, 0, [])},
                {},
            ),  # type: ignore[arg-type]
            _entry(),
            (COMPANY,),
            collection_job_id=uuid4(),
            collected_at=NOW,
            retention_until=NOW + timedelta(days=365),
        )

    with pytest.raises(SmartRecruitersSourceSchemaError, match="stopped"):
        collect_smartrecruiters_jobs(
            StubSmartRecruitersClient(
                {0: _page(0, 100, 1, [])},
                {},
            ),  # type: ignore[arg-type]
            _entry(),
            (COMPANY,),
            collection_job_id=uuid4(),
            collected_at=NOW,
            retention_until=NOW + timedelta(days=365),
        )

    duplicate = _summary("job-1", "SOC Analyst")
    with pytest.raises(SmartRecruitersSourceSchemaError, match="duplicate posting id"):
        collect_smartrecruiters_jobs(
            StubSmartRecruitersClient(
                {0: _page(0, 100, 2, [duplicate, duplicate])},
                {"job-1": _detail("job-1", "SOC Analyst")},
            ),  # type: ignore[arg-type]
            _entry(),
            (COMPANY,),
            collection_job_id=uuid4(),
            collected_at=NOW,
            retention_until=NOW + timedelta(days=365),
        )

    with pytest.raises(SmartRecruitersSourceSchemaError, match="detail id"):
        collect_smartrecruiters_jobs(
            StubSmartRecruitersClient(
                {0: _page(0, 100, 1, [_summary("job-1", "SOC Analyst")])},
                {"job-1": _detail("different", "SOC Analyst")},
            ),  # type: ignore[arg-type]
            _entry(),
            (COMPANY,),
            collection_job_id=uuid4(),
            collected_at=NOW,
            retention_until=NOW + timedelta(days=365),
        )

    with pytest.raises(SmartRecruitersSourceWindowError, match="job limit"):
        collect_smartrecruiters_jobs(
            StubSmartRecruitersClient(
                {0: _page(0, 100, 2, [])},
                {},
            ),  # type: ignore[arg-type]
            _entry(),
            (COMPANY,),
            collection_job_id=uuid4(),
            collected_at=NOW,
            retention_until=NOW + timedelta(days=365),
            max_jobs_per_company=1,
        )


def test_collector_validates_configuration_governance_and_detail_schema() -> None:
    client = StubSmartRecruitersClient({}, {})
    disabled = replace(COMPANY, enabled=False)

    with pytest.raises(ValueError, match="at least one"):
        collect_smartrecruiters_jobs(
            client,  # type: ignore[arg-type]
            _entry(),
            (disabled,),
            collection_job_id=uuid4(),
            collected_at=NOW,
            retention_until=NOW + timedelta(days=365),
        )
    with pytest.raises(ValueError, match="page_size"):
        collect_smartrecruiters_jobs(
            client,  # type: ignore[arg-type]
            _entry(),
            (COMPANY,),
            collection_job_id=uuid4(),
            collected_at=NOW,
            retention_until=NOW + timedelta(days=365),
            page_size=0,
        )
    with pytest.raises(ValueError, match="max_jobs_per_company"):
        collect_smartrecruiters_jobs(
            client,  # type: ignore[arg-type]
            _entry(),
            (COMPANY,),
            collection_job_id=uuid4(),
            collected_at=NOW,
            retention_until=NOW + timedelta(days=365),
            max_jobs_per_company=0,
        )

    entry = _entry()
    denied = replace(entry, policy=replace(entry.policy, status=SourceStatus.QUARANTINED))
    with pytest.raises(SmartRecruitersCollectionDeniedError, match="source_not_enabled"):
        collect_smartrecruiters_jobs(
            client,  # type: ignore[arg-type]
            denied,
            (COMPANY,),
            collection_job_id=uuid4(),
            collected_at=NOW,
            retention_until=NOW + timedelta(days=365),
        )

    with pytest.raises(SmartRecruitersSourceSchemaError, match="detail schema"):
        collect_smartrecruiters_jobs(
            StubSmartRecruitersClient(
                {0: _page(0, 100, 1, [_summary("job-1", "SOC Analyst")])},
                {"job-1": {"id": "job-1"}},
            ),  # type: ignore[arg-type]
            _entry(),
            (COMPANY,),
            collection_job_id=uuid4(),
            collected_at=NOW,
            retention_until=NOW + timedelta(days=365),
        )


def _entry() -> SourceRegistryEntry:
    return next(
        entry
        for entry in load_source_registry(Path("policies/sources.example.yml"))
        if entry.policy.id == "smartrecruiters-job-board"
    )


def _page(
    offset: int,
    limit: int,
    total: int,
    content: list[dict[str, object]],
) -> dict[str, object]:
    return {
        "offset": offset,
        "limit": limit,
        "totalFound": total,
        "content": content,
    }


def _summary(identifier: str, title: str) -> dict[str, object]:
    return {
        "id": identifier,
        "uuid": f"uuid-{identifier}",
        "name": title,
        "releasedDate": "2026-08-04T10:00:00Z",
        "location": {"city": "Paris", "country": "FR", "remote": True},
        "department": {
            "label": "Security" if title != "Finance Manager" else "Finance"
        },
        "typeOfEmployment": {"label": "Full-time"},
        "experienceLevel": {"label": "Senior"},
        "ref": (
            "https://api.smartrecruiters.com/v1/companies/example/postings/"
            f"{identifier}"
        ),
    }


def _detail(
    identifier: str,
    title: str,
    *,
    relevant: bool = True,
) -> dict[str, object]:
    description = (
        "<p>Security operations and Microsoft Sentinel.</p>"
        if relevant
        else "<p>Accounting and forecasting.</p>"
    )
    return {
        "id": identifier,
        "name": title,
        "releasedDate": "2026-08-04T10:00:00Z",
        "location": {"city": "Paris", "country": "FR", "remote": True},
        "department": {"label": "Security" if relevant else "Finance"},
        "typeOfEmployment": {"label": "Full-time"},
        "experienceLevel": {"label": "Senior"},
        "postingUrl": f"https://jobs.smartrecruiters.com/example/{identifier}",
        "jobAd": {
            "sections": {
                "jobDescription": {"text": description},
                "qualifications": {"text": "<p>Detection engineering.</p>"},
            }
        },
    }
