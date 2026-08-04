from __future__ import annotations

import json
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

import httpx
import pytest

from cip.adapters.sources.bodacc_identity.client import (
    BodaccIdentityClient,
    BodaccIdentityFetchResult,
    BodaccIdentitySourceResponseError,
)
from cip.adapters.sources.bodacc_identity.collector import (
    BodaccIdentityCollectionDeniedError,
    BodaccIdentitySourceSchemaError,
    BodaccIdentitySourceWindowError,
    collect_bodacc_identities,
)
from cip.adapters.sources.bodacc_identity.mapper import map_bodacc_identity
from cip.adapters.sources.bodacc_identity.schemas import BodaccIdentityAnnouncement
from cip.adapters.sources.organization_identity.registry import OrganizationIdentityTarget
from cip.modules.organizations.domain.identity import IdentityStatus, MatchState
from cip.modules.source_governance.domain.models import SourceStatus
from cip.modules.source_governance.infrastructure.registry import (
    SourceRegistryEntry,
    load_source_registry,
)

NOW = datetime(2026, 8, 4, 16, 0, tzinfo=UTC)
RETENTION = NOW + timedelta(days=1825)
TARGET = OrganizationIdentityTarget(
    id="synthetic-fr",
    organization_id=UUID("86fe6126-5731-5c4d-a206-69a6a736cae5"),
    canonical_name="Synthetic Company SAS",
    country_code="FR",
    query="Synthetic Company",
    postal_code="75001",
    siren="732829320",
    enabled=True,
)


class StubBodaccClient:
    records_url = "https://bodacc.example.test/api/records"

    def __init__(self, payload: object) -> None:
        self.payload = payload
        self.calls: list[tuple[str, int]] = []

    def fetch_announcements(
        self,
        siren: str,
        *,
        limit: int = 100,
    ) -> BodaccIdentityFetchResult:
        self.calls.append((siren, limit))
        return BodaccIdentityFetchResult(
            body=json.dumps(self.payload).encode(),
            request_url=f"{self.records_url}?company={siren}",
        )


def test_mapper_creates_exact_siren_claim() -> None:
    announcement = BodaccIdentityAnnouncement.model_validate(
        _event("event-1", "2026-07-01", "creation")
    )
    mapped = map_bodacc_identity(
        TARGET,
        (announcement,),
        request_url="https://bodacc.example.test/api/records?company=732829320",
        collection_job_id=uuid4(),
        collected_at=NOW,
        retention_until=RETENTION,
    )

    assert mapped.projection.identity.status is IdentityStatus.ACTIVE
    assert mapped.projection.attached_organization is not None
    assert mapped.projection.merge_candidates[0].state is MatchState.AUTO_CONFIRMED
    assert mapped.observation.source_record_key == "legal-unit:732829320"


def test_mapper_supports_empty_history_and_rejects_mismatched_company() -> None:
    empty = map_bodacc_identity(
        TARGET,
        (),
        request_url="https://bodacc.example.test/api/records?company=732829320",
        collection_job_id=uuid4(),
        collected_at=NOW,
        retention_until=RETENTION,
    )
    assert empty.projection.identity.status is IdentityStatus.UNKNOWN

    other = BodaccIdentityAnnouncement.model_validate(
        _event("event-2", "2026-07-02", "creation", siren="552100554")
    )
    with pytest.raises(ValueError, match="requested SIREN"):
        map_bodacc_identity(
            TARGET,
            (other,),
            request_url="https://bodacc.example.test/api/records?company=732829320",
            collection_job_id=uuid4(),
            collected_at=NOW,
            retention_until=RETENTION,
        )


def test_http_client_builds_selected_company_query() -> None:
    captured: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        return httpx.Response(
            200,
            headers={"content-type": "application/json"},
            json=_response(),
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as http_client:
        client = BodaccIdentityClient(
            http_client,
            records_url="https://bodacc.example.test/api/records",
        )
        fetched = client.fetch_announcements("732829320")

    assert "732829320" in captured["url"]
    assert "select=id%2Cdateparution" in captured["url"]
    assert fetched.body


def test_http_client_rejects_inputs_and_unsafe_responses() -> None:
    with httpx.Client(transport=httpx.MockTransport(lambda _: httpx.Response(200))) as client:
        source = BodaccIdentityClient(client, records_url="https://bodacc.example.test/api")
        with pytest.raises(ValueError):
            source.fetch_announcements("invalid")
        with pytest.raises(ValueError):
            source.fetch_announcements("732829320", limit=0)

    responses = (
        httpx.Response(200, headers={"content-type": "text/plain"}),
        httpx.Response(
            200,
            headers={"content-type": "application/json", "content-length": "bad"},
            content=b"{}",
        ),
    )
    for response in responses:
        with httpx.Client(
            transport=httpx.MockTransport(lambda _, response=response: response)
        ) as client:
            source = BodaccIdentityClient(
                client,
                records_url="https://bodacc.example.test/api",
            )
            with pytest.raises(BodaccIdentitySourceResponseError):
                source.fetch_announcements("732829320")


def test_collector_is_idempotent_and_detects_changed_history() -> None:
    client = StubBodaccClient(_response())
    first = collect_bodacc_identities(
        client,  # type: ignore[arg-type]
        _entry(),
        (TARGET,),
        collection_job_id=uuid4(),
        collected_at=NOW,
        retention_until=RETENTION,
    )
    second = collect_bodacc_identities(
        client,  # type: ignore[arg-type]
        _entry(),
        (TARGET,),
        collection_job_id=uuid4(),
        collected_at=NOW + timedelta(days=1),
        retention_until=RETENTION + timedelta(days=1),
        checkpoint=first.checkpoint,
    )
    changed = collect_bodacc_identities(
        StubBodaccClient({"total_count": 0, "results": []}),  # type: ignore[arg-type]
        _entry(),
        (TARGET,),
        collection_job_id=uuid4(),
        collected_at=NOW + timedelta(days=2),
        retention_until=RETENTION + timedelta(days=2),
        checkpoint=first.checkpoint,
    )

    assert first.not_modified is False
    assert second.not_modified is True and second.observations == ()
    assert changed.not_modified is False
    assert client.calls == [("732829320", 100), ("732829320", 100)]


def test_collector_rejects_window_schema_policy_and_configuration() -> None:
    with pytest.raises(BodaccIdentitySourceWindowError):
        collect_bodacc_identities(
            StubBodaccClient(_response(total_count=101)),  # type: ignore[arg-type]
            _entry(),
            (TARGET,),
            collection_job_id=uuid4(),
            collected_at=NOW,
            retention_until=RETENTION,
        )
    with pytest.raises(BodaccIdentitySourceSchemaError):
        collect_bodacc_identities(
            StubBodaccClient({"invalid": True}),  # type: ignore[arg-type]
            _entry(),
            (TARGET,),
            collection_job_id=uuid4(),
            collected_at=NOW,
            retention_until=RETENTION,
        )
    denied_entry = _entry()
    denied = replace(
        denied_entry,
        policy=replace(denied_entry.policy, status=SourceStatus.QUARANTINED),
    )
    with pytest.raises(BodaccIdentityCollectionDeniedError):
        collect_bodacc_identities(
            StubBodaccClient(_response()),  # type: ignore[arg-type]
            denied,
            (TARGET,),
            collection_job_id=uuid4(),
            collected_at=NOW,
            retention_until=RETENTION,
        )
    with pytest.raises(ValueError, match="at least one"):
        collect_bodacc_identities(
            StubBodaccClient(_response()),  # type: ignore[arg-type]
            _entry(),
            (replace(TARGET, siren=None),),
            collection_job_id=uuid4(),
            collected_at=NOW,
            retention_until=RETENTION,
        )


def _entry() -> SourceRegistryEntry:
    return next(
        entry
        for entry in load_source_registry(Path("policies/identity_sources.yml"))
        if entry.policy.id == "bodacc-identity"
    )


def _response(*, total_count: int = 1) -> dict[str, object]:
    return {
        "total_count": total_count,
        "results": [_event("event-1", "2026-07-01", "creation")],
    }


def _event(
    identifier: str,
    published: str,
    family: str,
    *,
    siren: str = "732829320",
) -> dict[str, object]:
    return {
        "id": identifier,
        "dateparution": published,
        "typeavis": "A",
        "typeavis_lib": "Company event",
        "familleavis": family,
        "familleavis_lib": family,
        "commercant": "SYNTHETIC COMPANY SAS",
        "ville": "PARIS",
        "registre": f"{siren} RCS PARIS",
        "cp": "75001",
        "url_complete": "https://bodacc.example.test/events/event-1",
    }
