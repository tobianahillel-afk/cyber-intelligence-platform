from __future__ import annotations

import json
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

import httpx
import pytest
from pydantic import ValidationError

from cip.adapters.sources.brreg_identity.client import (
    BrregEntityRemovedError,
    BrregFetchResult,
    BrregIdentityClient,
    BrregSourceResponseError,
)
from cip.adapters.sources.brreg_identity.collector import (
    BrregCheckpoint,
    BrregCollectionDeniedError,
    collect_brreg_entities,
)
from cip.adapters.sources.brreg_identity.mapper import map_brreg_entity
from cip.adapters.sources.brreg_identity.schemas import BrregEntity
from cip.adapters.sources.organization_identity.registry import OrganizationIdentityTarget
from cip.modules.organizations.domain.identity import MatchMethod
from cip.modules.organizations.domain.identifiers import IdentifierScheme
from cip.modules.source_governance.domain.models import SourceStatus
from cip.modules.source_governance.infrastructure.registry import (
    SourceRegistryEntry,
    load_source_registry,
)

NOW = datetime(2026, 8, 11, 10, 0, tzinfo=UTC)
ENTITIES_URL = "https://data.brreg.no/enhetsregisteret/api/enheter"


class StubBrregClient:
    def __init__(self, payload: dict[str, object]) -> None:
        self.payload = payload
        self.calls: list[str] = []

    def entity_url(self, registration_number: str) -> str:
        return f"{ENTITIES_URL}/{registration_number}"

    def fetch_entity(self, registration_number: str) -> BrregFetchResult:
        self.calls.append(registration_number)
        return BrregFetchResult(
            body=json.dumps(self.payload).encode(),
            request_url=self.entity_url(registration_number),
        )


def test_schema_and_mapper_attach_only_on_exact_norwegian_registration() -> None:
    target = _target()
    entity = BrregEntity.model_validate(_entity())
    observation, projection, fingerprint = map_brreg_entity(
        target,
        entity,
        request_url=f"{ENTITIES_URL}/974760673",
        collection_job_id=uuid4(),
        collected_at=NOW,
        retention_until=NOW + timedelta(days=365),
    )

    assert observation.source_id == "brreg-enhetsregisteret"
    assert projection.identity.country_code == "NO"
    assert projection.identity.identifiers[0].scheme is IdentifierScheme.FOREIGN_REGISTRATION
    assert projection.identity.identifiers[0].value == "974760673"
    assert projection.identity.official_name == "BRØNNØYSUNDREGISTRENE"
    assert projection.identity.activity_code == "84.110"
    assert projection.identity.address == "Havnegata 48, 8900 BRØNNØYSUND"
    assert projection.attached_organization is not None
    assert projection.merge_candidates[0].method is MatchMethod.EXACT_IDENTIFIER
    assert len(fingerprint) == 64


def test_mapper_rejects_wrong_target_registration_even_when_name_matches() -> None:
    target = replace(_target(), foreign_registration="917625026")
    with pytest.raises(ValueError, match="does not match target"):
        map_brreg_entity(
            target,
            BrregEntity.model_validate(_entity()),
            request_url=f"{ENTITIES_URL}/974760673",
            collection_job_id=uuid4(),
            collected_at=NOW,
            retention_until=NOW + timedelta(days=365),
        )


def test_schema_rejects_bad_org_number_blank_name_and_negative_employees() -> None:
    with pytest.raises(ValidationError):
        BrregEntity.model_validate(_entity(organisasjonsnummer="123"))
    with pytest.raises(ValidationError):
        BrregEntity.model_validate(_entity(navn=" "))
    with pytest.raises(ValidationError):
        BrregEntity.model_validate(_entity(antallAnsatte=-1))


def test_collector_is_idempotent_and_governed() -> None:
    client = StubBrregClient(_entity())
    first = collect_brreg_entities(
        client,  # type: ignore[arg-type]
        _entry(),
        (_target(),),
        collection_job_id=uuid4(),
        collected_at=NOW,
        retention_until=NOW + timedelta(days=365),
    )
    assert len(first.observations) == 1
    assert len(first.projections) == 1
    assert first.not_modified is False
    assert client.calls == ["974760673"]

    second = collect_brreg_entities(
        client,  # type: ignore[arg-type]
        _entry(),
        (_target(),),
        collection_job_id=uuid4(),
        collected_at=NOW,
        retention_until=NOW + timedelta(days=365),
        checkpoint=BrregCheckpoint(dict(first.checkpoint.fingerprints)),
    )
    assert second.observations == ()
    assert second.projections == ()
    assert second.not_modified is True

    denied = replace(
        _entry(),
        policy=replace(_entry().policy, status=SourceStatus.QUARANTINED),
    )
    with pytest.raises(BrregCollectionDeniedError, match="source_not_enabled"):
        collect_brreg_entities(
            client,  # type: ignore[arg-type]
            denied,
            (_target(),),
            collection_job_id=uuid4(),
            collected_at=NOW,
            retention_until=NOW + timedelta(days=365),
        )


def test_collector_ignores_disabled_or_non_norwegian_targets() -> None:
    client = StubBrregClient(_entity())
    batch = collect_brreg_entities(
        client,  # type: ignore[arg-type]
        _entry(),
        (
            replace(_target(), enabled=False),
            replace(
                _target(),
                id="fr",
                organization_id=UUID("86fe6126-5731-5c4d-a206-69a6a736cae5"),
                country_code="FR",
                foreign_registration="974760673",
            ),
        ),
        collection_job_id=uuid4(),
        collected_at=NOW,
        retention_until=NOW + timedelta(days=365),
    )
    assert batch.not_modified is True
    assert client.calls == []


def test_client_handles_public_media_type_size_and_legal_removal() -> None:
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200,
            headers={"content-type": BrregIdentityClient.ACCEPT},
            json=_entity(),
            request=request,
        )
    )
    with httpx.Client(transport=transport) as http_client:
        result = BrregIdentityClient(http_client, entities_url=ENTITIES_URL).fetch_entity(
            "974 760 673"
        )
    assert result.request_url.endswith("/974760673")

    removed = httpx.MockTransport(lambda request: httpx.Response(410, request=request))
    with httpx.Client(transport=removed) as http_client:
        with pytest.raises(BrregEntityRemovedError, match="removed"):
            BrregIdentityClient(http_client, entities_url=ENTITIES_URL).fetch_entity(
                "974760673"
            )

    non_json = httpx.MockTransport(
        lambda request: httpx.Response(
            200,
            headers={"content-type": "text/html"},
            text="bad",
            request=request,
        )
    )
    with httpx.Client(transport=non_json) as http_client:
        with pytest.raises(BrregSourceResponseError, match="content type"):
            BrregIdentityClient(http_client, entities_url=ENTITIES_URL).fetch_entity(
                "974760673"
            )


def _target() -> OrganizationIdentityTarget:
    return OrganizationIdentityTarget(
        id="brreg-validation",
        organization_id=UUID("7f3ea686-13c2-5c32-9a20-d3ed5c6fab2c"),
        canonical_name="Brønnøysundregistrene",
        country_code="NO",
        query="Brønnøysundregistrene",
        postal_code="8900",
        foreign_registration="974760673",
        enabled=True,
    )


def _entry() -> SourceRegistryEntry:
    return next(
        entry
        for entry in load_source_registry(Path("policies/sources.company_identity_expansion.yml"))
        if entry.policy.id == "brreg-enhetsregisteret"
    )


def _entity(**changes: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "respons_klasse": "Enhet",
        "organisasjonsnummer": "974760673",
        "navn": "BRØNNØYSUNDREGISTRENE",
        "organisasjonsform": {"kode": "ORGL", "beskrivelse": "Organisasjonsledd"},
        "historiskeNavn": [{"navn": "BRØNNØYSUNDREGISTRENE", "fraDato": "1998-01-16 19:22:18"}],
        "forretningsadresse": {
            "land": "Norge",
            "landkode": "NO",
            "postnummer": "8900",
            "poststed": "BRØNNØYSUND",
            "adresse": ["Havnegata 48"],
            "kommune": "BRØNNØY",
            "kommunenummer": "1813",
        },
        "registreringsdatoEnhetsregisteret": "1995-03-12",
        "registrertIForetaksregisteret": False,
        "konkurs": False,
        "underAvvikling": False,
        "underTvangsavviklingEllerTvangsopplosning": False,
        "naeringskode1": {"kode": "84.110", "beskrivelse": "Generell offentlig administrasjon"},
        "antallAnsatte": 590,
        "_links": {"self": {"href": f"{ENTITIES_URL}/974760673"}},
    }
    payload.update(changes)
    return payload
