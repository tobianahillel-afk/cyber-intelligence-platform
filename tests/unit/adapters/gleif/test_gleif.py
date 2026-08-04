from __future__ import annotations

import json
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

import httpx
import pytest
from pydantic import ValidationError

from cip.adapters.sources.gleif.client import (
    GleifClient,
    GleifFetchResult,
    GleifSourceResponseError,
)
from cip.adapters.sources.gleif.collector import (
    GleifCheckpoint,
    GleifCollectionDeniedError,
    GleifSourceSchemaError,
    collect_gleif_identities,
)
from cip.adapters.sources.gleif.mapper import map_gleif_record, parent_lei
from cip.adapters.sources.gleif.schemas import (
    GleifRecordResponse,
    GleifRelationshipResponse,
)
from cip.adapters.sources.organization_identity.registry import OrganizationIdentityTarget
from cip.modules.organizations.domain.identifiers import IdentifierScheme
from cip.modules.organizations.domain.identity import (
    MatchState,
    RelationshipType,
)
from cip.modules.source_governance.domain.models import SourceStatus
from cip.modules.source_governance.infrastructure.registry import (
    SourceRegistryEntry,
    load_source_registry,
)

NOW = datetime(2026, 8, 4, 16, 0, tzinfo=UTC)
RETENTION = NOW + timedelta(days=1825)
CHILD_LEI = "5493001KJTIIGC8Y1R12"
DIRECT_LEI = "529900T8BM49AURSDO55"
ULTIMATE_LEI = "213800D1EI4B9WTWWD28"
TARGET = OrganizationIdentityTarget(
    id="example-lei",
    organization_id=UUID("86fe6126-5731-5c4d-a206-69a6a736cae5"),
    canonical_name="Example France SAS",
    country_code="FR",
    query="Example France",
    postal_code="75001",
    siren="732829320",
    lei=CHILD_LEI,
    enabled=True,
)


class StubGleifClient:
    def __init__(
        self,
        records: dict[str, object],
        relationships: dict[tuple[str, str], object | None],
    ) -> None:
        self.records = records
        self.relationships = relationships
        self.calls: list[tuple[str, str]] = []

    def record_url(self, lei: str) -> str:
        return f"https://api.gleif.org/api/v1/lei-records/{lei}"

    def relationship_url(self, lei: str, relationship: str) -> str:
        return f"{self.record_url(lei)}/{relationship}-relationship"

    def fetch_record(self, lei: str) -> GleifFetchResult:
        self.calls.append(("record", lei))
        return GleifFetchResult(
            body=json.dumps(self.records[lei]).encode(),
            request_url=self.record_url(lei),
        )

    def fetch_relationship(
        self,
        lei: str,
        relationship: str,
    ) -> GleifFetchResult | None:
        self.calls.append((relationship, lei))
        payload = self.relationships.get((lei, relationship))
        if payload is None:
            return None
        return GleifFetchResult(
            body=json.dumps(payload).encode(),
            request_url=self.relationship_url(lei, relationship),
        )


def test_gleif_schema_and_mapper_use_exact_lei_and_local_registration() -> None:
    response = GleifRecordResponse.model_validate(_record(CHILD_LEI, "Example France SAS"))
    mapped = map_gleif_record(
        response,
        request_url=f"https://api.gleif.org/api/v1/lei-records/{CHILD_LEI}",
        collection_job_id=uuid4(),
        collected_at=NOW,
        retention_until=RETENTION,
        target=TARGET,
    )

    identity = mapped.projection.identity
    assert mapped.projection.attached_organization is not None
    assert mapped.projection.merge_candidates[0].state is MatchState.AUTO_CONFIRMED
    assert identity.country_code == "FR"
    assert {identifier.scheme for identifier in identity.identifiers} == {
        IdentifierScheme.LEI,
        IdentifierScheme.SIREN,
    }
    assert identity.address == "1 Rue Exemple, 75001, Paris, FR"
    assert identity.legal_form == "SAS"
    assert identity.aliases == ("Example",)
    assert mapped.observation.source_updated_at == datetime(
        2026,
        8,
        4,
        10,
        0,
        tzinfo=UTC,
    )


def test_gleif_mapper_keeps_name_only_target_in_review() -> None:
    target = replace(TARGET, siren=None, lei=None)
    mapped = map_gleif_record(
        GleifRecordResponse.model_validate(_record(CHILD_LEI, "Example France SAS")),
        request_url=f"https://api.gleif.org/api/v1/lei-records/{CHILD_LEI}",
        collection_job_id=uuid4(),
        collected_at=NOW,
        retention_until=RETENTION,
        target=target,
    )

    assert mapped.projection.attached_organization is None
    assert mapped.projection.merge_candidates[0].state is MatchState.NEEDS_REVIEW


def test_gleif_schema_helpers_and_validation() -> None:
    response = GleifRecordResponse.model_validate(_record(CHILD_LEI, "Example"))
    entity = response.data.attributes.entity
    assert entity.legalAddress is not None
    assert entity.legalAddress.formatted() == "1 Rue Exemple, 75001, Paris, FR"
    assert entity.legalForm is not None and entity.legalForm.label() == "SAS"
    with pytest.raises(ValidationError):
        GleifRecordResponse.model_validate({"data": {"id": CHILD_LEI}})


def test_parent_lei_handles_both_directions_and_missing_data() -> None:
    forward = GleifRelationshipResponse.model_validate(
        _relationship(CHILD_LEI, DIRECT_LEI)
    )
    reverse = GleifRelationshipResponse.model_validate(
        _relationship(DIRECT_LEI, CHILD_LEI)
    )

    assert parent_lei(forward, child_lei=CHILD_LEI) == DIRECT_LEI
    assert parent_lei(reverse, child_lei=CHILD_LEI) == DIRECT_LEI
    assert parent_lei(None, child_lei=CHILD_LEI) is None
    assert (
        parent_lei(
            GleifRelationshipResponse.model_validate({"data": None}),
            child_lei=CHILD_LEI,
        )
        is None
    )


def test_http_client_builds_exact_record_and_relationship_urls() -> None:
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(str(request.url))
        if str(request.url).endswith("direct-parent-relationship"):
            return httpx.Response(404, headers={"content-type": "application/json"})
        return httpx.Response(
            200,
            headers={"content-type": "application/vnd.api+json"},
            json=_record(CHILD_LEI, "Example"),
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as http_client:
        client = GleifClient(http_client, api_base_url="https://api.gleif.org/api/v1")
        fetched = client.fetch_record(CHILD_LEI)
        missing = client.fetch_relationship(CHILD_LEI, "direct-parent")

    assert fetched.request_url.endswith(CHILD_LEI)
    assert missing is None
    assert calls[1].endswith("direct-parent-relationship")
    with httpx.Client(transport=httpx.MockTransport(handler)) as http_client:
        with pytest.raises(ValueError, match="unsupported"):
            GleifClient(
                http_client,
                api_base_url="https://api.gleif.org/api/v1",
            ).relationship_url(CHILD_LEI, "invalid")


def test_http_client_rejects_unsafe_responses() -> None:
    responses = (
        httpx.Response(200, headers={"content-type": "text/html"}),
        httpx.Response(
            200,
            headers={
                "content-type": "application/json",
                "content-length": "invalid",
            },
            content=b"{}",
        ),
        httpx.Response(
            200,
            headers={
                "content-type": "application/json",
                "content-length": str(GleifClient.MAX_RESPONSE_BYTES + 1),
            },
            content=b"{}",
        ),
    )
    for response in responses:
        with httpx.Client(
            transport=httpx.MockTransport(lambda _, response=response: response)
        ) as http_client:
            client = GleifClient(
                http_client,
                api_base_url="https://api.gleif.org/api/v1",
            )
            with pytest.raises(GleifSourceResponseError):
                client.fetch_record(CHILD_LEI)


def test_collector_builds_direct_and_ultimate_parent_graph() -> None:
    client = StubGleifClient(
        {
            CHILD_LEI: _record(CHILD_LEI, "Example France SAS"),
            DIRECT_LEI: _record(DIRECT_LEI, "Direct Parent AG", country="DE"),
            ULTIMATE_LEI: _record(ULTIMATE_LEI, "Ultimate Parent PLC", country="GB"),
        },
        {
            (CHILD_LEI, "direct-parent"): _relationship(CHILD_LEI, DIRECT_LEI),
            (CHILD_LEI, "ultimate-parent"): _relationship(CHILD_LEI, ULTIMATE_LEI),
        },
    )
    batch = collect_gleif_identities(
        client,  # type: ignore[arg-type]
        _entry(),
        (TARGET,),
        collection_job_id=uuid4(),
        collected_at=NOW,
        retention_until=RETENTION,
    )

    assert len(batch.projections) == 3
    assert len(batch.observations) == 3
    child = batch.projections[0]
    assert {relationship.relationship_type for relationship in child.relationships} == {
        RelationshipType.DIRECT_PARENT,
        RelationshipType.ULTIMATE_PARENT,
    }
    assert set(batch.checkpoint.fingerprints[TARGET.id]) == {
        f"lei:{CHILD_LEI}",
        f"lei:{DIRECT_LEI}",
        f"lei:{ULTIMATE_LEI}",
        "relationship:direct-parent",
        "relationship:ultimate-parent",
    }


def test_collector_replay_refreshes_projections_without_observations() -> None:
    client = StubGleifClient(
        {CHILD_LEI: _record(CHILD_LEI, "Example France SAS")},
        {},
    )
    first = collect_gleif_identities(
        client,  # type: ignore[arg-type]
        _entry(),
        (TARGET,),
        collection_job_id=uuid4(),
        collected_at=NOW,
        retention_until=RETENTION,
    )
    second = collect_gleif_identities(
        client,  # type: ignore[arg-type]
        _entry(),
        (TARGET,),
        collection_job_id=uuid4(),
        collected_at=NOW + timedelta(days=1),
        retention_until=RETENTION + timedelta(days=1),
        checkpoint=first.checkpoint,
    )

    assert first.not_modified is False
    assert second.not_modified is True
    assert second.observations == ()
    assert len(second.projections) == 1


def test_collector_rejects_schema_policy_and_missing_enabled_lei() -> None:
    with pytest.raises(GleifSourceSchemaError, match="record schema"):
        collect_gleif_identities(
            StubGleifClient({CHILD_LEI: {"bad": True}}, {}),  # type: ignore[arg-type]
            _entry(),
            (TARGET,),
            collection_job_id=uuid4(),
            collected_at=NOW,
            retention_until=RETENTION,
        )

    denied = replace(
        _entry(),
        policy=replace(_entry().policy, status=SourceStatus.QUARANTINED),
    )
    with pytest.raises(GleifCollectionDeniedError):
        collect_gleif_identities(
            StubGleifClient({CHILD_LEI: _record(CHILD_LEI, "Example")}, {}),  # type: ignore[arg-type]
            denied,
            (TARGET,),
            collection_job_id=uuid4(),
            collected_at=NOW,
            retention_until=RETENTION,
        )

    with pytest.raises(ValueError, match="at least one"):
        collect_gleif_identities(
            StubGleifClient({}, {}),  # type: ignore[arg-type]
            _entry(),
            (replace(TARGET, lei=None),),
            collection_job_id=uuid4(),
            collected_at=NOW,
            retention_until=RETENTION,
        )


def _entry() -> SourceRegistryEntry:
    return next(
        entry
        for entry in load_source_registry(Path("policies/identity_sources.yml"))
        if entry.policy.id == "gleif"
    )


def _record(lei: str, name: str, *, country: str = "FR") -> dict[str, object]:
    local_registration = "732829320" if country == "FR" else "HRB-12345"
    return {
        "data": {
            "type": "lei-records",
            "id": lei,
            "attributes": {
                "lei": lei,
                "entity": {
                    "legalName": {"name": name, "language": "en"},
                    "otherNames": [{"name": "Example", "language": "en"}],
                    "legalAddress": {
                        "addressLines": ["1 Rue Exemple"],
                        "city": "Paris",
                        "country": country,
                        "postalCode": "75001",
                    },
                    "headquartersAddress": {
                        "addressLines": ["1 Rue Exemple"],
                        "city": "Paris",
                        "country": country,
                        "postalCode": "75001",
                    },
                    "registeredAt": {"id": "RA000189"},
                    "registeredAs": local_registration,
                    "jurisdiction": f"{country}-75",
                    "category": "GENERAL",
                    "legalForm": {"id": "8888", "other": "SAS"},
                    "status": "ACTIVE",
                    "creationDate": "2020-01-01",
                },
                "registration": {
                    "initialRegistrationDate": "2020-01-01T00:00:00Z",
                    "lastUpdateDate": "2026-08-04T10:00:00Z",
                    "status": "ISSUED",
                    "nextRenewalDate": "2027-01-01T00:00:00Z",
                    "managingLou": "5299000J2N45DDNE4Y28",
                    "corroborationLevel": "FULLY_CORROBORATED",
                },
            },
        }
    }


def _relationship(child: str, parent: str) -> dict[str, object]:
    return {
        "data": {
            "type": "rr-records",
            "id": f"{child}-{parent}",
            "attributes": {
                "relationship": {
                    "startNode": {"nodeID": child, "nodeType": "LEI"},
                    "endNode": {"nodeID": parent, "nodeType": "LEI"},
                    "relationshipType": "IS_DIRECTLY_CONSOLIDATED_BY",
                    "relationshipStatus": "ACTIVE",
                },
                "periods": [
                    {
                        "startDate": "2020-01-01T00:00:00Z",
                        "periodType": "RELATIONSHIP_PERIOD",
                    }
                ],
            },
        }
    }
