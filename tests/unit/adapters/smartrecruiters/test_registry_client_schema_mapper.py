from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from textwrap import dedent
from uuid import uuid4

import httpx
import pytest
from pydantic import ValidationError

from cip.adapters.sources.smartrecruiters.client import (
    SmartRecruitersClient,
    SmartRecruitersSourceResponseError,
)
from cip.adapters.sources.smartrecruiters.mapper import (
    map_smartrecruiters_posting,
    smartrecruiters_posting_to_canonical,
)
from cip.adapters.sources.smartrecruiters.registry import (
    SmartRecruitersCompany,
    load_smartrecruiters_companies,
)
from cip.adapters.sources.smartrecruiters.schemas import (
    SmartRecruitersPostingDetail,
    SmartRecruitersPostingList,
    SmartRecruitersPostingSummary,
)

NOW = datetime(2026, 8, 4, 14, 0, tzinfo=UTC)
COMPANY = SmartRecruitersCompany(
    id="example-security",
    company_identifier="example",
    canonical_name="Example Security",
    country_code="FR",
)


def test_repository_smartrecruiters_registry_loads() -> None:
    companies = load_smartrecruiters_companies(
        Path("policies/smartrecruiters_companies.yml")
    )

    assert len(companies) == 1
    assert companies[0].id == "smartrecruiters-inc"
    assert companies[0].company_identifier == "smartrecruiters"
    assert companies[0].enabled is True


def test_registry_rejects_invalid_structures_fields_and_duplicates(tmp_path: Path) -> None:
    invalid_cases = (
        ("- invalid\n", "root must be a mapping"),
        ("version: 2\ncompanies: []\n", "unsupported"),
        ("version: 1\ncompanies: {}\n", "companies must be a list"),
        ("version: 1\ncompanies: [invalid]\n", "must be a mapping"),
    )
    for index, (content, message) in enumerate(invalid_cases):
        path = tmp_path / f"invalid-{index}.yml"
        path.write_text(content, encoding="utf-8")
        with pytest.raises(ValueError, match=message):
            load_smartrecruiters_companies(path)

    duplicate = tmp_path / "duplicate.yml"
    duplicate.write_text(
        dedent(
            """
            version: 1
            companies:
              - &company
                id: example
                company_identifier: example
                canonical_name: Example
                country_code: FR
                enabled: true
              - *company
            """
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="duplicate SmartRecruiters company id"):
        load_smartrecruiters_companies(duplicate)

    bad_identifier = tmp_path / "bad-identifier.yml"
    bad_identifier.write_text(
        _registry(company_identifier="bad/value", country_code="FR"),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="company_identifier"):
        load_smartrecruiters_companies(bad_identifier)

    bad_country = tmp_path / "bad-country.yml"
    bad_country.write_text(
        _registry(company_identifier="valid", country_code="FRA"),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="country_code"):
        load_smartrecruiters_companies(bad_country)


def test_schemas_normalize_locations_sections_and_timestamps() -> None:
    summary = SmartRecruitersPostingSummary.model_validate(_summary())
    detail = SmartRecruitersPostingDetail.model_validate(_detail())
    page = SmartRecruitersPostingList.model_validate(
        {"offset": 0, "limit": 100, "totalFound": 1, "content": [_summary()]}
    )

    assert summary.location.display_name() == "Remote — Paris, IDF, FR"
    assert detail.location.display_name() == "Paris, IDF, FR"
    assert page.content[0].id == "job-123"
    assert detail.job_ad.sections.html_parts() == (
        "<p>Security operations and detection engineering.</p>",
        "<p>Microsoft Sentinel experience.</p>",
        "<p>Full-time role.</p>",
    )

    assert SmartRecruitersPostingSummary.model_validate(
        _summary(location={"remote": True})
    ).location.display_name() == "Remote"
    assert SmartRecruitersPostingSummary.model_validate(
        _summary(location={})
    ).location.display_name() == "Unspecified"

    with pytest.raises(ValidationError, match="timezone-aware"):
        SmartRecruitersPostingSummary.model_validate(
            _summary(releasedDate="2026-08-04T10:00:00")
        )
    with pytest.raises(ValidationError):
        SmartRecruitersPostingDetail.model_validate(_detail(name=" "))


def test_client_fetches_public_list_and_detail() -> None:
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(str(request.url))
        if request.url.path.endswith("/job-123"):
            payload: object = _detail()
        else:
            payload = {
                "offset": 0,
                "limit": 50,
                "totalFound": 1,
                "content": [_summary()],
            }
        return httpx.Response(
            200,
            headers={"content-type": "application/json"},
            json=payload,
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as http_client:
        client = SmartRecruitersClient(
            http_client,
            companies_base_url="https://api.smartrecruiters.com/v1/companies/",
        )
        list_result = client.fetch_postings("example", offset=0, limit=50)
        detail_result = client.fetch_posting("example", "job-123")

    assert "destination=PUBLIC" in calls[0]
    assert "offset=0" in calls[0]
    assert "limit=50" in calls[0]
    assert calls[1].endswith("/example/postings/job-123")
    assert SmartRecruitersPostingList.model_validate_json(list_result.body).total_found == 1
    assert SmartRecruitersPostingDetail.model_validate_json(detail_result.body).id == "job-123"

    with httpx.Client(transport=httpx.MockTransport(handler)) as http_client:
        client = SmartRecruitersClient(http_client, companies_base_url="https://example.test")
        with pytest.raises(ValueError, match="offset"):
            client.fetch_postings("example", offset=-1, limit=10)
        with pytest.raises(ValueError, match="limit"):
            client.fetch_postings("example", offset=0, limit=101)


def test_client_rejects_unsafe_responses() -> None:
    responses = (
        (httpx.Response(200, headers={"content-type": "text/html"}), "content type"),
        (
            httpx.Response(
                200,
                headers={"content-type": "application/json", "content-length": "bad"},
                content=b"{}",
            ),
            "Content-Length",
        ),
        (
            httpx.Response(
                200,
                headers={
                    "content-type": "application/json",
                    "content-length": str(
                        SmartRecruitersClient.MAX_RESPONSE_BYTES + 1
                    ),
                },
                content=b"{}",
            ),
            "size limit",
        ),
    )
    for response, message in responses:
        client = httpx.Client(transport=_transport_returning(response))
        try:
            with pytest.raises(SmartRecruitersSourceResponseError, match=message):
                SmartRecruitersClient(
                    client,
                    companies_base_url="https://example.test",
                ).fetch_posting("example", "job-123")
        finally:
            client.close()


def test_mapper_converts_bounded_html_to_canonical_signal() -> None:
    summary = SmartRecruitersPostingSummary.model_validate(_summary())
    detail = SmartRecruitersPostingDetail.model_validate(_detail())
    canonical = smartrecruiters_posting_to_canonical(COMPANY, summary, detail)

    assert canonical.organization_key == "example-security"
    assert canonical.department == "Security"
    assert canonical.employment_type == "Full-time"
    assert canonical.seniority == "Senior"
    assert "<p>" not in canonical.description_text

    mapped = map_smartrecruiters_posting(
        COMPANY,
        summary,
        detail,
        collection_job_id=uuid4(),
        collected_at=NOW,
        retention_until=NOW + timedelta(days=365),
    )

    assert mapped is not None
    assert mapped[0].source_id == "smartrecruiters-job-board"
    assert mapped[0].source_record_key == "example:job-123"
    assert mapped[1].organization.canonical_name == "Example Security"
    assert "microsoft sentinel" in mapped[1].signal.matched_terms


def _transport_returning(response: httpx.Response) -> httpx.MockTransport:
    def handler(_: httpx.Request) -> httpx.Response:
        return response

    return httpx.MockTransport(handler)


def _registry(*, company_identifier: str, country_code: str) -> str:
    return dedent(
        f"""
        version: 1
        companies:
          - id: example
            company_identifier: {company_identifier}
            canonical_name: Example
            country_code: {country_code}
            enabled: true
        """
    )


def _summary(**changes: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "id": "job-123",
        "uuid": "uuid-123",
        "name": "Senior SOC Analyst",
        "releasedDate": "2026-08-04T10:00:00Z",
        "location": {
            "city": "Paris",
            "region": "IDF",
            "country": "FR",
            "remote": True,
        },
        "department": {"label": "Security"},
        "typeOfEmployment": {"label": "Full-time"},
        "experienceLevel": {"label": "Senior"},
        "ref": "https://api.smartrecruiters.com/v1/companies/example/postings/job-123",
    }
    payload.update(changes)
    return payload


def _detail(**changes: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "id": "job-123",
        "name": "Senior SOC Analyst",
        "releasedDate": "2026-08-04T10:00:00Z",
        "location": {"city": "Paris", "region": "IDF", "country": "FR"},
        "department": {"label": "Security"},
        "typeOfEmployment": {"label": "Full-time"},
        "experienceLevel": {"label": "Senior"},
        "postingUrl": "https://jobs.smartrecruiters.com/example/job-123",
        "jobAd": {
            "sections": {
                "companyDescription": {"text": "<p>Company biography.</p>"},
                "jobDescription": {
                    "text": "<p>Security operations and detection engineering.</p>"
                },
                "qualifications": {
                    "text": "<p>Microsoft Sentinel experience.</p>"
                },
                "additionalInformation": {"text": "<p>Full-time role.</p>"},
            }
        },
    }
    payload.update(changes)
    return payload
