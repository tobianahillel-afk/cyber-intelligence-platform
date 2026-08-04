from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from textwrap import dedent
from uuid import uuid4

import httpx
import pytest
from pydantic import ValidationError

from cip.adapters.sources.lever.client import LeverClient, LeverSourceResponseError
from cip.adapters.sources.lever.mapper import (
    lever_posting_to_canonical,
    map_lever_posting,
)
from cip.adapters.sources.lever.registry import LeverSite, load_lever_sites
from cip.adapters.sources.lever.schemas import LeverPosting, LeverPostingsResponse

NOW = datetime(2026, 8, 4, 14, 0, tzinfo=UTC)
SITE = LeverSite(
    id="example-security",
    site_token="example",
    canonical_name="Example Security",
    country_code="FR",
)


def test_repository_lever_registry_loads() -> None:
    sites = load_lever_sites(Path("policies/lever_sites.yml"))

    assert len(sites) == 1
    assert sites[0].id == "lever-inc"
    assert sites[0].site_token == "lever"
    assert sites[0].enabled is True


def test_lever_registry_rejects_invalid_structures_fields_and_duplicates(
    tmp_path: Path,
) -> None:
    invalid_cases = (
        ("- invalid\n", "root must be a mapping"),
        ("version: 2\nsites: []\n", "unsupported"),
        ("version: 1\nsites: {}\n", "sites must be a list"),
        ("version: 1\nsites: [invalid]\n", "must be a mapping"),
    )
    for index, (content, message) in enumerate(invalid_cases):
        path = tmp_path / f"invalid-{index}.yml"
        path.write_text(content, encoding="utf-8")
        with pytest.raises(ValueError, match=message):
            load_lever_sites(path)

    duplicate = tmp_path / "duplicate.yml"
    duplicate.write_text(
        dedent(
            """
            version: 1
            sites:
              - &site
                id: example
                site_token: example
                canonical_name: Example
                country_code: FR
                enabled: true
              - *site
            """
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="duplicate Lever site id"):
        load_lever_sites(duplicate)

    bad_token = tmp_path / "bad-token.yml"
    bad_token.write_text(
        _registry(site_token="bad/token", country_code="FR"),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="site_token"):
        load_lever_sites(bad_token)

    bad_country = tmp_path / "bad-country.yml"
    bad_country.write_text(
        _registry(site_token="valid", country_code="FRA"),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="country_code"):
        load_lever_sites(bad_country)


def test_lever_schema_normalizes_locations_time_and_description() -> None:
    posting = LeverPosting.model_validate(_posting())

    assert posting.published_at == datetime(2026, 8, 4, 10, 0, tzinfo=UTC)
    assert posting.categories.normalized_location() == "Paris, Remote"
    assert "Security operations" in posting.description_text()
    assert "Microsoft Sentinel" in posting.description_text()
    assert LeverPostingsResponse.model_validate([_posting()]).root[0].id == "job-123"

    fallback = LeverPosting.model_validate(
        _posting(categories={"location": "Lyon", "allLocations": []})
    )
    assert fallback.categories.normalized_location() == "Lyon"
    unspecified = LeverPosting.model_validate(_posting(categories={}))
    assert unspecified.categories.normalized_location() == "Unspecified"

    with pytest.raises(ValidationError):
        LeverPosting.model_validate(_posting(text=" "))


def test_lever_client_paginates_with_json_mode() -> None:
    captured: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        return httpx.Response(
            200,
            headers={"content-type": "application/json"},
            json=[_posting()],
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as http_client:
        client = LeverClient(
            http_client,
            postings_base_url="https://api.lever.co/v0/postings/",
        )
        result = client.fetch_postings("example", skip=100, limit=50)

    assert client.postings_url("example") == "https://api.lever.co/v0/postings/example"
    assert "mode=json" in captured["url"]
    assert "skip=100" in captured["url"]
    assert "limit=50" in captured["url"]
    assert LeverPostingsResponse.model_validate_json(result.body).root[0].id == "job-123"

    with httpx.Client(transport=httpx.MockTransport(handler)) as http_client:
        client = LeverClient(http_client, postings_base_url="https://example.test")
        with pytest.raises(ValueError, match="skip"):
            client.fetch_postings("example", skip=-1, limit=10)
        with pytest.raises(ValueError, match="limit"):
            client.fetch_postings("example", skip=0, limit=101)


def test_lever_client_rejects_unsafe_responses() -> None:
    responses = (
        (httpx.Response(200, headers={"content-type": "text/html"}), "content type"),
        (
            httpx.Response(
                200,
                headers={"content-type": "application/json", "content-length": "bad"},
                content=b"[]",
            ),
            "Content-Length",
        ),
        (
            httpx.Response(
                200,
                headers={
                    "content-type": "application/json",
                    "content-length": str(LeverClient.MAX_RESPONSE_BYTES + 1),
                },
                content=b"[]",
            ),
            "size limit",
        ),
    )
    for response, message in responses:
        client = httpx.Client(transport=_transport_returning(response))
        try:
            with pytest.raises(LeverSourceResponseError, match=message):
                LeverClient(client, postings_base_url="https://example.test").fetch_postings(
                    "example",
                    skip=0,
                    limit=10,
                )
        finally:
            client.close()


def test_lever_mapper_uses_canonical_contract() -> None:
    posting = LeverPosting.model_validate(_posting())
    canonical = lever_posting_to_canonical(SITE, posting)

    assert canonical.organization_key == "example-security"
    assert canonical.department == "Security"
    assert canonical.employment_type == "Full-time"
    assert canonical.location == "Paris, Remote"

    mapped = map_lever_posting(
        SITE,
        posting,
        collection_job_id=uuid4(),
        collected_at=NOW,
        retention_until=NOW + timedelta(days=365),
    )

    assert mapped is not None
    assert mapped[0].source_id == "lever-job-board"
    assert mapped[0].source_record_key == "example:job-123"
    assert mapped[1].organization.canonical_name == "Example Security"
    assert "microsoft sentinel" in mapped[1].signal.matched_terms


def _transport_returning(response: httpx.Response) -> httpx.MockTransport:
    def handler(_: httpx.Request) -> httpx.Response:
        return response

    return httpx.MockTransport(handler)


def _registry(*, site_token: str, country_code: str) -> str:
    return dedent(
        f"""
        version: 1
        sites:
          - id: example
            site_token: {site_token}
            canonical_name: Example
            country_code: {country_code}
            enabled: true
        """
    )


def _posting(**changes: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "id": "job-123",
        "text": "Senior SOC Analyst",
        "categories": {
            "location": "Paris",
            "allLocations": ["Paris", "Remote", "Paris"],
            "commitment": "Full-time",
            "team": "Security Engineering",
            "department": "Security",
        },
        "createdAt": 1_775_290_400_000,
        "descriptionPlain": "Security operations and detection engineering.",
        "additionalPlain": "Operate Microsoft Sentinel.",
        "hostedUrl": "https://jobs.lever.co/example/job-123",
        "workplaceType": "hybrid",
    }
    payload.update(changes)
    return payload
