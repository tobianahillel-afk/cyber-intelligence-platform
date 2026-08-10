from __future__ import annotations

import json
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from textwrap import dedent
from uuid import uuid4

import httpx
import pytest
from pydantic import ValidationError

from cip.adapters.sources.recruitee.client import (
    RecruiteeClient,
    RecruiteeFetchResult,
    RecruiteeSourceResponseError,
)
from cip.adapters.sources.recruitee.collector import (
    RecruiteeCheckpoint,
    RecruiteeCollectionDeniedError,
    RecruiteeSourceSchemaError,
    RecruiteeSourceWindowError,
    collect_recruitee_jobs,
)
from cip.adapters.sources.recruitee.mapper import (
    map_recruitee_offer,
    recruitee_offer_to_canonical,
)
from cip.adapters.sources.recruitee.registry import (
    RecruiteeCareerSite,
    load_recruitee_sites,
)
from cip.adapters.sources.recruitee.schemas import (
    RecruiteeOffer,
    RecruiteeOffersResponse,
)
from cip.modules.source_governance.domain.models import SourceStatus
from cip.modules.source_governance.infrastructure.registry import (
    SourceRegistryEntry,
    load_source_registry,
)

NOW = datetime(2026, 8, 11, 0, 25, tzinfo=UTC)
SITE = RecruiteeCareerSite(
    id="example-security",
    subdomain="example-security",
    canonical_name="Example Security",
    country_code="FR",
)


class StubRecruiteeClient:
    def __init__(self, payload: object) -> None:
        self.payload = payload
        self.calls: list[str] = []

    def fetch_offers(self, offers_url: str) -> RecruiteeFetchResult:
        self.calls.append(offers_url)
        return RecruiteeFetchResult(
            body=json.dumps(self.payload).encode(),
            request_url=offers_url,
        )


def test_repository_registry_and_structured_offer_mapping() -> None:
    sites = load_recruitee_sites(Path("policies/recruitee_sites.yml"))
    assert sites[0].subdomain == "peopleforpeople"
    assert sites[0].enabled is True

    offer = RecruiteeOffer.model_validate(_offer())
    assert offer.department_name() == "Security"
    assert offer.display_location() == "Remote — France, Paris; Remote"
    canonical = recruitee_offer_to_canonical(SITE, offer)
    assert canonical.department == "Security"
    assert canonical.location == "Remote — France, Paris; Remote"
    assert canonical.source_url.endswith("/o/senior-soc-analyst")

    mapped = map_recruitee_offer(
        SITE,
        offer,
        collection_job_id=uuid4(),
        collected_at=NOW,
        retention_until=NOW + timedelta(days=365),
    )
    assert mapped is not None
    assert mapped[0].source_id == "recruitee-careers-site"
    assert "microsoft sentinel" in mapped[1].signal.matched_terms


def test_schema_supports_string_department_and_rejects_missing_time() -> None:
    offer = RecruiteeOffer.model_validate(
        _offer(department="Security Operations", locations=[], location="Lyon")
    )
    assert offer.department_name() == "Security Operations"
    assert offer.display_location() == "Remote — Lyon"

    with pytest.raises(ValidationError, match="published_at or created_at"):
        RecruiteeOffer.model_validate(_offer(created_at=None, published_at=None))
    with pytest.raises(ValidationError):
        RecruiteeOffer.model_validate(_offer(created_at="2026-08-11T00:25:00"))


def test_client_reads_only_public_offers_endpoint_and_rejects_bad_mime() -> None:
    captured: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["method"] = request.method
        captured["url"] = str(request.url)
        return httpx.Response(
            200,
            headers={"content-type": "application/json"},
            json={"offers": [_offer()]},
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as http_client:
        client = RecruiteeClient(http_client)
        result = client.fetch_offers(SITE.offers_url)
    assert captured == {"method": "GET", "url": SITE.offers_url}
    assert RecruiteeOffersResponse.model_validate_json(result.body).offers

    unsafe = httpx.MockTransport(
        lambda _: httpx.Response(200, headers={"content-type": "text/html"})
    )
    with httpx.Client(transport=unsafe) as http_client:
        with pytest.raises(RecruiteeSourceResponseError, match="content type"):
            RecruiteeClient(http_client).fetch_offers(SITE.offers_url)


def test_collector_refreshes_relevant_projection_without_duplicate_observation() -> None:
    relevant = RecruiteeOffer.model_validate(_offer())
    fingerprint = recruitee_offer_to_canonical(SITE, relevant).fingerprint()
    payload = {
        "offers": [
            relevant.model_dump(mode="json"),
            _offer(
                id=456,
                slug="finance-manager",
                title="Finance Manager",
                department={"id": 2, "name": "Finance"},
                description="Accounting and forecasting.",
                requirements="Financial reporting.",
            ),
        ]
    }
    batch = collect_recruitee_jobs(
        StubRecruiteeClient(payload),  # type: ignore[arg-type]
        _entry(),
        (SITE,),
        collection_job_id=uuid4(),
        collected_at=NOW,
        retention_until=NOW + timedelta(days=365),
        checkpoint=RecruiteeCheckpoint(
            {"example-security": {"123": fingerprint}}
        ),
    )
    assert batch.not_modified is False
    assert batch.observations == ()
    assert {projection.signal.title for projection in batch.projections} == {
        "Senior SOC Analyst"
    }
    assert set(batch.checkpoint.fingerprints["example-security"]) == {"123", "456"}
    assert batch.checkpoint.fingerprints["example-security"]["123"] == fingerprint


def test_collector_rejects_governance_schema_duplicates_and_window() -> None:
    denied = replace(
        _entry(),
        policy=replace(_entry().policy, status=SourceStatus.QUARANTINED),
    )
    with pytest.raises(RecruiteeCollectionDeniedError, match="source_not_enabled"):
        _collect(StubRecruiteeClient({"offers": []}), denied)

    with pytest.raises(RecruiteeSourceSchemaError, match="schema validation"):
        _collect(StubRecruiteeClient({"offers": [{"id": 1}]}))

    duplicate = _offer()
    with pytest.raises(RecruiteeSourceSchemaError, match="duplicate offer id"):
        _collect(StubRecruiteeClient({"offers": [duplicate, duplicate]}))

    with pytest.raises(RecruiteeSourceWindowError, match="job limit"):
        collect_recruitee_jobs(
            StubRecruiteeClient(
                {"offers": [_offer(), _offer(id=2, slug="soc-analyst-2")]}
            ),  # type: ignore[arg-type]
            _entry(),
            (SITE,),
            collection_job_id=uuid4(),
            collected_at=NOW,
            retention_until=NOW + timedelta(days=365),
            max_jobs_per_site=1,
        )

    with pytest.raises(ValueError, match="at least one"):
        collect_recruitee_jobs(
            StubRecruiteeClient({"offers": []}),  # type: ignore[arg-type]
            _entry(),
            (replace(SITE, enabled=False),),
            collection_job_id=uuid4(),
            collected_at=NOW,
            retention_until=NOW + timedelta(days=365),
        )


def test_registry_rejects_duplicate_subdomain_and_bad_country(tmp_path: Path) -> None:
    duplicate = tmp_path / "duplicate.yml"
    duplicate.write_text(
        dedent(
            """
            version: 1
            sites:
              - &site
                id: example
                subdomain: example
                canonical_name: Example
                country_code: FR
                enabled: true
              - id: other
                subdomain: example
                canonical_name: Other
                country_code: FR
                enabled: true
            """
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="duplicate Recruitee subdomain"):
        load_recruitee_sites(duplicate)

    with pytest.raises(ValueError, match="country_code"):
        RecruiteeCareerSite(
            id="example",
            subdomain="example",
            canonical_name="Example",
            country_code="FRA",
        )


def _collect(
    client: StubRecruiteeClient,
    entry: SourceRegistryEntry | None = None,
) -> object:
    return collect_recruitee_jobs(
        client,  # type: ignore[arg-type]
        entry or _entry(),
        (SITE,),
        collection_job_id=uuid4(),
        collected_at=NOW,
        retention_until=NOW + timedelta(days=365),
    )


def _entry() -> SourceRegistryEntry:
    return next(
        entry
        for entry in load_source_registry(Path("policies/sources.ats_expansion.yml"))
        if entry.policy.id == "recruitee-careers-site"
    )


def _offer(**changes: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "id": 123,
        "slug": "senior-soc-analyst",
        "title": "Senior SOC Analyst",
        "status": "published",
        "department": {"id": 1, "name": "Security"},
        "locations": [
            {"id": 1, "full_address": "France, Paris", "country_code": "FR"},
            {"id": 2, "city": "Remote"},
        ],
        "remote": True,
        "description": "<p>Security operations with Microsoft Sentinel.</p>",
        "requirements": "<p>SIEM and incident response.</p>",
        "created_at": "2026-08-11T00:25:00Z",
        "employment_type_code": "full_time",
    }
    payload.update(changes)
    return payload
