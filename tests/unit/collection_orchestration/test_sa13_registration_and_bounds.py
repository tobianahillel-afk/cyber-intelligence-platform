from __future__ import annotations

from pathlib import Path

import httpx
import pytest

from cip.adapters.sources.ashby.client import AshbyClient, AshbySourceResponseError
from cip.adapters.sources.ashby.registry import AshbyBoard
from cip.adapters.sources.recruitee.client import (
    RecruiteeClient,
    RecruiteeSourceResponseError,
)
from cip.adapters.sources.recruitee.registry import RecruiteeCareerSite
from cip.adapters.sources.teamtailor.client import (
    TeamtailorClient,
    TeamtailorSourceResponseError,
)
from cip.adapters.sources.teamtailor.registry import TeamtailorAccount
from cip.modules.collection_orchestration.application.ats_registration import (
    register_extended_ats_adapters,
)
from cip.modules.collection_orchestration.application.ports import CollectionAdapter
from cip.modules.source_governance.infrastructure.registry import (
    SourceRegistryEntry,
    load_source_registry,
)


def test_ats_registration_registers_all_available_provider_adapters() -> None:
    entries = _entries()
    adapters: dict[tuple[str, str], CollectionAdapter] = {}

    register_extended_ats_adapters(
        adapters,
        entries,
        (AshbyBoard("ashby", "Ashby", "Ashby", enabled=True),),
        (
            RecruiteeCareerSite(
                "people",
                "peopleforpeople",
                "People for People",
                enabled=True,
            ),
        ),
        (TeamtailorAccount("teamtailor", "Teamtailor", enabled=True),),
        teamtailor_token_provider=lambda: "token",
        timeout_seconds=10,
    )

    assert set(adapters) == {
        ("ashby-job-board", "ashby-public-job-postings-api"),
        ("recruitee-careers-site", "recruitee-careers-site-api"),
        ("teamtailor-public-jobs", "teamtailor-public-read-jobs-api"),
    }


def test_ats_registration_skips_missing_or_disabled_sources() -> None:
    adapters: dict[tuple[str, str], CollectionAdapter] = {}
    register_extended_ats_adapters(
        adapters,
        {},
        (AshbyBoard("ashby", "Ashby", "Ashby", enabled=False),),
        (
            RecruiteeCareerSite(
                "people",
                "peopleforpeople",
                "People for People",
                enabled=False,
            ),
        ),
        (TeamtailorAccount("teamtailor", "Teamtailor", enabled=False),),
        teamtailor_token_provider=lambda: None,
        timeout_seconds=10,
    )
    assert adapters == {}


def test_ats_registration_rejects_multiple_teamtailor_accounts() -> None:
    entries = _entries()
    with pytest.raises(ValueError, match="exactly one enabled account"):
        register_extended_ats_adapters(
            {},
            entries,
            (),
            (),
            (
                TeamtailorAccount("one", "One", enabled=True),
                TeamtailorAccount("two", "Two", enabled=True),
            ),
            teamtailor_token_provider=lambda: "token",
            timeout_seconds=10,
        )


def test_ats_registration_rejects_duplicate_runtime_identity() -> None:
    entries = _entries()
    adapters: dict[tuple[str, str], CollectionAdapter] = {}
    board = AshbyBoard("ashby", "Ashby", "Ashby", enabled=True)
    register_extended_ats_adapters(
        adapters,
        entries,
        (board,),
        (),
        (),
        teamtailor_token_provider=lambda: None,
        timeout_seconds=10,
    )
    with pytest.raises(ValueError, match="duplicate runtime adapter"):
        register_extended_ats_adapters(
            adapters,
            entries,
            (board,),
            (),
            (),
            teamtailor_token_provider=lambda: None,
            timeout_seconds=10,
        )


@pytest.mark.parametrize("declared", ["invalid", "10"])
def test_ashby_client_rejects_invalid_or_oversized_content_length(declared: str) -> None:
    transport = httpx.MockTransport(
        lambda _: httpx.Response(
            200,
            headers={"content-type": "application/json", "content-length": declared},
            content=b"{}",
        )
    )
    with httpx.Client(transport=transport) as http_client:
        client = AshbyClient(http_client, postings_base_url="https://example.test")
        client.MAX_RESPONSE_BYTES = 2
        with pytest.raises(AshbySourceResponseError):
            client.fetch_jobs("Example")


def test_ashby_client_rejects_oversized_body_without_declared_length() -> None:
    transport = httpx.MockTransport(
        lambda _: httpx.Response(
            200,
            headers={"content-type": "application/json"},
            content=b"123",
        )
    )
    with httpx.Client(transport=transport) as http_client:
        client = AshbyClient(http_client, postings_base_url="https://example.test")
        client.MAX_RESPONSE_BYTES = 2
        with pytest.raises(AshbySourceResponseError, match="body exceeds"):
            client.fetch_jobs("Example")


@pytest.mark.parametrize("declared", ["invalid", "10"])
def test_recruitee_client_rejects_invalid_or_oversized_content_length(
    declared: str,
) -> None:
    transport = httpx.MockTransport(
        lambda _: httpx.Response(
            200,
            headers={"content-type": "application/json", "content-length": declared},
            content=b"{}",
        )
    )
    with httpx.Client(transport=transport) as http_client:
        client = RecruiteeClient(http_client)
        client.MAX_RESPONSE_BYTES = 2
        with pytest.raises(RecruiteeSourceResponseError):
            client.fetch_offers("https://example.recruitee.com/api/offers/")


def test_recruitee_client_rejects_oversized_body_without_declared_length() -> None:
    transport = httpx.MockTransport(
        lambda _: httpx.Response(
            200,
            headers={"content-type": "application/json"},
            content=b"123",
        )
    )
    with httpx.Client(transport=transport) as http_client:
        client = RecruiteeClient(http_client)
        client.MAX_RESPONSE_BYTES = 2
        with pytest.raises(RecruiteeSourceResponseError, match="body exceeds"):
            client.fetch_offers("https://example.recruitee.com/api/offers/")


@pytest.mark.parametrize("declared", ["invalid", "10"])
def test_teamtailor_client_rejects_invalid_or_oversized_content_length(
    declared: str,
) -> None:
    transport = httpx.MockTransport(
        lambda _: httpx.Response(
            200,
            headers={
                "content-type": "application/vnd.api+json",
                "content-length": declared,
            },
            content=b"{}",
        )
    )
    with httpx.Client(transport=transport) as http_client:
        client = TeamtailorClient(http_client)
        client.MAX_RESPONSE_BYTES = 2
        with pytest.raises(TeamtailorSourceResponseError):
            client.fetch_jobs_page(
                "https://api.teamtailor.com/v1/jobs",
                api_token="token",
                api_version="20240404",
            )


def test_teamtailor_client_rejects_oversized_body_without_declared_length() -> None:
    transport = httpx.MockTransport(
        lambda _: httpx.Response(
            200,
            headers={"content-type": "application/vnd.api+json"},
            content=b"123",
        )
    )
    with httpx.Client(transport=transport) as http_client:
        client = TeamtailorClient(http_client)
        client.MAX_RESPONSE_BYTES = 2
        with pytest.raises(TeamtailorSourceResponseError, match="body exceeds"):
            client.fetch_jobs_page(
                "https://api.teamtailor.com/v1/jobs",
                api_token="token",
                api_version="20240404",
            )


def _entries() -> dict[str, SourceRegistryEntry]:
    return {
        entry.policy.id: entry
        for entry in load_source_registry(Path("policies/sources.ats_expansion.yml"))
    }
