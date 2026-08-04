from __future__ import annotations

import json
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

import httpx
import pytest
from pydantic import ValidationError

from cip.adapters.sources.organization_identity.registry import OrganizationIdentityTarget
from cip.adapters.sources.recherche_entreprises.client import (
    RechercheEntreprisesClient,
    RechercheEntreprisesFetchResult,
    RechercheEntreprisesSourceResponseError,
)
from cip.adapters.sources.recherche_entreprises.collector import (
    RechercheEntreprisesCheckpoint,
    RechercheEntreprisesCollectionDeniedError,
    RechercheEntreprisesSourceSchemaError,
    RechercheEntreprisesSourceWindowError,
    collect_recherche_entreprises,
)
from cip.adapters.sources.recherche_entreprises.mapper import map_recherche_entreprise
from cip.adapters.sources.recherche_entreprises.schemas import (
    RechercheEntrepriseResult,
    RechercheEntreprisesResponse,
)
from cip.modules.organizations.domain.identity import (
    IdentityKind,
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
TARGET = OrganizationIdentityTarget(
    id="example-fr",
    organization_id=UUID("86fe6126-5731-5c4d-a206-69a6a736cae5"),
    canonical_name="Example France SAS",
    country_code="FR",
    query="Example France",
    postal_code="75001",
    siren="732829320",
    siret="73282932000074",
    enabled=True,
)


class StubRechercheClient:
    search_url = "https://recherche-entreprises.api.gouv.fr/search"

    def __init__(self, payload: object) -> None:
        self.payload = payload
        self.calls: list[tuple[str, int, int]] = []

    def search(
        self,
        query: str,
        *,
        page: int = 1,
        per_page: int = 25,
    ) -> RechercheEntreprisesFetchResult:
        self.calls.append((query, page, per_page))
        return RechercheEntreprisesFetchResult(
            body=json.dumps(self.payload).encode(),
            request_url=(
                "https://recherche-entreprises.api.gouv.fr/search"
                "?q=Example+France&page=1&per_page=25"
            ),
        )


def test_recherche_schema_and_mapper_distinguish_legal_unit_and_establishment() -> None:
    result = RechercheEntrepriseResult.model_validate(_company())
    mapped = map_recherche_entreprise(
        TARGET,
        result,
        request_url="https://recherche-entreprises.api.gouv.fr/search?q=Example",
        collection_job_id=uuid4(),
        collected_at=NOW,
        retention_until=RETENTION,
    )

    assert mapped is not None
    assert len(mapped.projections) == 2
    legal, establishment = mapped.projections
    assert legal.identity.kind is IdentityKind.LEGAL_UNIT
    assert legal.attached_organization is not None
    assert legal.merge_candidates[0].state is MatchState.AUTO_CONFIRMED
    assert establishment.identity.kind is IdentityKind.ESTABLISHMENT
    assert establishment.identity.is_headquarters is True
    assert {
        relation.relationship_type for relation in establishment.relationships
    } == {RelationshipType.ESTABLISHMENT_OF, RelationshipType.HEADQUARTERS_OF}
    assert establishment.identity.organization_id == TARGET.organization_id
    assert len(mapped.observations) == 2


def test_mapper_keeps_name_only_match_in_review() -> None:
    target = replace(TARGET, siren=None, siret=None)
    mapped = map_recherche_entreprise(
        target,
        RechercheEntrepriseResult.model_validate(_company()),
        request_url="https://recherche-entreprises.api.gouv.fr/search?q=Example",
        collection_job_id=uuid4(),
        collected_at=NOW,
        retention_until=RETENTION,
    )

    assert mapped is not None
    legal = mapped.projections[0]
    assert legal.attached_organization is None
    assert legal.candidate_organizations[0].id == TARGET.organization_id
    assert legal.merge_candidates[0].state is MatchState.NEEDS_REVIEW


def test_mapper_rejects_non_diffusible_legal_unit_and_establishment() -> None:
    hidden_company = RechercheEntrepriseResult.model_validate(
        _company(statut_diffusion="N")
    )
    assert (
        map_recherche_entreprise(
            TARGET,
            hidden_company,
            request_url="https://recherche-entreprises.api.gouv.fr/search?q=Example",
            collection_job_id=uuid4(),
            collected_at=NOW,
            retention_until=RETENTION,
        )
        is None
    )

    company = _company()
    company["siege"]["statut_diffusion_etablissement"] = "N"  # type: ignore[index]
    mapped = map_recherche_entreprise(
        TARGET,
        RechercheEntrepriseResult.model_validate(company),
        request_url="https://recherche-entreprises.api.gouv.fr/search?q=Example",
        collection_job_id=uuid4(),
        collected_at=NOW,
        retention_until=RETENTION,
    )
    assert mapped is not None
    assert len(mapped.projections) == 1


def test_schema_normalizes_names_and_rejects_missing_required_fields() -> None:
    result = RechercheEntrepriseResult.model_validate(
        _company(nom_raison_sociale=None, sigle=" EXAMPLE ")
    )
    assert result.official_name() == "EXAMPLE FRANCE SAS"
    assert result.public_aliases() == ("EXAMPLE FRANCE SAS", "EXAMPLE")
    assert RechercheEntreprisesResponse.model_validate(_response()).total_results == 1
    with pytest.raises(ValidationError):
        RechercheEntrepriseResult.model_validate({"siren": "732829320"})


def test_http_client_builds_bounded_minimal_query() -> None:
    captured: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["user_agent"] = request.headers["user-agent"]
        return httpx.Response(
            200,
            headers={"content-type": "application/json"},
            json=_response(),
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as http_client:
        client = RechercheEntreprisesClient(
            http_client,
            search_url="https://recherche-entreprises.api.gouv.fr/search",
        )
        fetched = client.search("Example France", page=1, per_page=25)

    assert "minimal=true" in captured["url"]
    assert "include=siege%2Cmatching_etablissements" in captured["url"]
    assert "CyberIntelligencePlatform" in captured["user_agent"]
    assert RechercheEntreprisesResponse.model_validate_json(fetched.body).total_results == 1


@pytest.mark.parametrize(
    ("query", "page", "per_page"),
    (("", 1, 25), ("x", 0, 25), ("x", 1, 0), ("x", 1, 26)),
)
def test_http_client_rejects_invalid_query_window(
    query: str,
    page: int,
    per_page: int,
) -> None:
    with httpx.Client(transport=httpx.MockTransport(lambda _: httpx.Response(200))) as http_client:
        client = RechercheEntreprisesClient(
            http_client,
            search_url="https://recherche-entreprises.api.gouv.fr/search",
        )
        with pytest.raises(ValueError):
            client.search(query, page=page, per_page=per_page)


def test_http_client_rejects_unsafe_responses() -> None:
    responses = (
        httpx.Response(200, headers={"content-type": "text/html"}),
        httpx.Response(
            200,
            headers={"content-type": "application/json", "content-length": "bad"},
            content=b"{}",
        ),
        httpx.Response(
            200,
            headers={
                "content-type": "application/json",
                "content-length": str(RechercheEntreprisesClient.MAX_RESPONSE_BYTES + 1),
            },
            content=b"{}",
        ),
    )
    for response in responses:
        with httpx.Client(
            transport=httpx.MockTransport(lambda _, response=response: response)
        ) as http_client:
            client = RechercheEntreprisesClient(
                http_client,
                search_url="https://recherche-entreprises.api.gouv.fr/search",
            )
            with pytest.raises(RechercheEntreprisesSourceResponseError):
                client.search("Example")


def test_collector_is_idempotent_and_refreshes_projection() -> None:
    client = StubRechercheClient(_response())
    first = collect_recherche_entreprises(
        client,  # type: ignore[arg-type]
        _entry(),
        (TARGET,),
        collection_job_id=uuid4(),
        collected_at=NOW,
        retention_until=RETENTION,
    )
    second = collect_recherche_entreprises(
        client,  # type: ignore[arg-type]
        _entry(),
        (TARGET,),
        collection_job_id=uuid4(),
        collected_at=NOW + timedelta(days=1),
        retention_until=RETENTION + timedelta(days=1),
        checkpoint=first.checkpoint,
    )

    assert client.calls == [
        ("Example France", 1, 25),
        ("Example France", 1, 25),
    ]
    assert first.not_modified is False
    assert len(first.observations) == 2
    assert second.not_modified is True
    assert second.observations == ()
    assert len(second.projections) == 2


def test_collector_detects_changes_removals_duplicates_and_ambiguous_windows() -> None:
    previous = RechercheEntreprisesCheckpoint(
        {TARGET.id: {"732829320": "old", "552100554": "removed"}}
    )
    changed = collect_recherche_entreprises(
        StubRechercheClient(_response()),  # type: ignore[arg-type]
        _entry(),
        (TARGET,),
        collection_job_id=uuid4(),
        collected_at=NOW,
        retention_until=RETENTION,
        checkpoint=previous,
    )
    assert changed.not_modified is False
    assert set(changed.checkpoint.fingerprints[TARGET.id]) == {"732829320"}

    duplicate_payload = _response()
    duplicate_payload["results"].append(_company())  # type: ignore[index,union-attr]
    duplicate_payload["total_results"] = 2
    with pytest.raises(RechercheEntreprisesSourceSchemaError, match="duplicate SIREN"):
        collect_recherche_entreprises(
            StubRechercheClient(duplicate_payload),  # type: ignore[arg-type]
            _entry(),
            (TARGET,),
            collection_job_id=uuid4(),
            collected_at=NOW,
            retention_until=RETENTION,
        )

    with pytest.raises(RechercheEntreprisesSourceWindowError, match="ambiguous"):
        collect_recherche_entreprises(
            StubRechercheClient(_response(total_results=26, total_pages=2)),  # type: ignore[arg-type]
            _entry(),
            (TARGET,),
            collection_job_id=uuid4(),
            collected_at=NOW,
            retention_until=RETENTION,
        )


def test_collector_rejects_schema_policy_and_disabled_targets() -> None:
    with pytest.raises(RechercheEntreprisesSourceSchemaError, match="schema"):
        collect_recherche_entreprises(
            StubRechercheClient({"invalid": True}),  # type: ignore[arg-type]
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
    with pytest.raises(RechercheEntreprisesCollectionDeniedError):
        collect_recherche_entreprises(
            StubRechercheClient(_response()),  # type: ignore[arg-type]
            denied,
            (TARGET,),
            collection_job_id=uuid4(),
            collected_at=NOW,
            retention_until=RETENTION,
        )

    with pytest.raises(ValueError, match="at least one"):
        collect_recherche_entreprises(
            StubRechercheClient(_response()),  # type: ignore[arg-type]
            _entry(),
            (replace(TARGET, enabled=False),),
            collection_job_id=uuid4(),
            collected_at=NOW,
            retention_until=RETENTION,
        )


def _entry() -> SourceRegistryEntry:
    return next(
        entry
        for entry in load_source_registry(Path("policies/identity_sources.yml"))
        if entry.policy.id == "recherche-entreprises"
    )


def _response(
    *,
    total_results: int = 1,
    total_pages: int = 1,
) -> dict[str, object]:
    return {
        "results": [_company()],
        "total_results": total_results,
        "page": 1,
        "per_page": 25,
        "total_pages": total_pages,
    }


def _company(**changes: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "siren": "732829320",
        "nom_complet": "EXAMPLE FRANCE SAS",
        "nom_raison_sociale": "EXAMPLE FRANCE SAS",
        "sigle": "EXAMPLE",
        "etat_administratif": "A",
        "nature_juridique": "SAS",
        "activite_principale": "62.02A",
        "date_creation": "2020-01-01",
        "date_mise_a_jour": "2026-08-04T10:00:00Z",
        "statut_diffusion": "O",
        "siege": {
            "siret": "73282932000074",
            "etat_administratif": "A",
            "statut_diffusion_etablissement": "O",
            "est_siege": True,
            "adresse": "1 RUE EXEMPLE",
            "code_postal": "75001",
            "libelle_commune": "PARIS",
            "activite_principale": "62.02A",
            "date_creation": "2020-01-01",
            "date_mise_a_jour": "2026-08-04T10:00:00Z",
            "nom_commercial": "Example France",
            "liste_enseignes": ["EXAMPLE"],
        },
        "matching_etablissements": [],
    }
    payload.update(changes)
    return payload
