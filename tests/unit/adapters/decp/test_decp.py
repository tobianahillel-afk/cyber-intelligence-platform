from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from urllib.parse import parse_qs
from uuid import uuid4

import httpx
import pytest

from cip.adapters.sources.decp.client import DecpClient, DecpSourceResponseError
from cip.adapters.sources.decp.mapper import map_decp_contract
from cip.adapters.sources.decp.schemas import DecpContract, DecpResponse
from cip.modules.procurement_history.domain.models import (
    ContractStatus,
    DateBasis,
    PartyResolutionStatus,
    ProcurementPublicationKind,
)
from cip.modules.service_taxonomy.domain.models import CyberServiceFamily

NOW = datetime(2026, 8, 5, 10, 0, tzinfo=UTC)


def test_client_requests_only_selected_bounded_fields() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["method"] = request.method
        captured["query"] = parse_qs(request.url.query.decode())
        return httpx.Response(
            200,
            request=request,
            headers={"content-type": "application/json"},
            json={"total_count": 0, "results": []},
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as http_client:
        result = DecpClient(
            http_client,
            records_url=(
                "https://data.economie.gouv.fr/api/explore/v2.1/catalog/datasets/"
                "decp-2022-marches-valides/records"
            ),
        ).fetch_page(offset=0)

    query = captured["query"]
    assert captured["method"] == "GET"
    assert query["limit"] == ["100"]
    assert query["offset"] == ["0"]
    assert "acheteur_id" in query["select"][0]
    assert "titulaire_denominationsociale_1" in query["select"][0]
    assert "titulairesmodification" in query["select"][0]
    assert DecpResponse.model_validate_json(result.body).results == []


def test_client_rejects_invalid_offset_and_unsafe_response() -> None:
    with httpx.Client(transport=httpx.MockTransport(lambda _: httpx.Response(200))) as client:
        decp = DecpClient(client, records_url="https://example.test/records")
        with pytest.raises(ValueError, match="page boundary"):
            decp.fetch_page(offset=1)

    def wrong_type(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            request=request,
            headers={"content-type": "text/html"},
            text="no",
        )

    with (
        httpx.Client(transport=httpx.MockTransport(wrong_type)) as client,
        pytest.raises(DecpSourceResponseError, match="content type"),
    ):
        DecpClient(client, records_url="https://example.test/records").fetch_page(offset=0)


def test_schema_prefers_published_modification_values_and_titulars() -> None:
    contract = DecpContract.model_validate(
        _record(
            booleanmodification=True,
            objetmodification="Avenant audit ISO 27001 et PAM",
            datenotificationmodification="2026-09-15",
            dureemoismodification="18",
            montantmodification="320000,50",
            titulairesmodification=[
                {
                    "denominationSociale": "Provider Modified SAS",
                    "id": "12345678901234",
                    "typeIdentifiant": "SIRET",
                }
            ],
        )
    )

    assert contract.is_modification() is True
    assert contract.effective_title() == "Avenant audit ISO 27001 et PAM"
    assert contract.notification_timestamp() == datetime(2026, 9, 15)
    assert contract.duration_months() == 18
    assert contract.amount_value() == Decimal("320000.50")
    assert contract.titulars() == (
        ("Provider Modified SAS", "12345678901234", "SIRET"),
    )


def test_mapper_creates_published_contract_and_derived_renewal() -> None:
    mapped = map_decp_contract(
        DecpContract.model_validate(_record()),
        collection_job_id=uuid4(),
        collected_at=NOW,
        retention_until=NOW + timedelta(days=3650),
    )

    assert mapped is not None
    publication = mapped.procurement.publication
    contract = mapped.procurement.contract
    assert publication.kind is ProcurementPublicationKind.AWARD
    assert publication.buyer_organization_id == mapped.buyer.id
    assert mapped.buyer.registration_ids == ("SIRET:11111111111111",)
    assert contract is not None
    assert contract.status is ContractStatus.AWARDED
    assert contract.notification_date == date(2026, 8, 31)
    assert contract.notification_date_basis is DateBasis.PUBLISHED
    assert contract.end_date == date(2027, 2, 28)
    assert contract.end_date_basis is DateBasis.DERIVED
    assert contract.renewal_date == date(2027, 2, 28)
    assert contract.renewal_date_basis is DateBasis.ESTIMATED
    assert contract.amount is not None
    assert contract.amount.value == Decimal("250000")
    assert contract.amount.currency == "EUR"
    assert contract.parties[0].published_name == "Provider SAS"
    assert contract.parties[0].official_identifier == "22222222222222"
    assert contract.parties[0].resolution_status is PartyResolutionStatus.UNRESOLVED
    assert {match.family for match in contract.service_families} == {
        CyberServiceFamily.AUDIT_RISK_ASSESSMENT,
        CyberServiceFamily.GRC_COMPLIANCE,
        CyberServiceFamily.IAM_IGA_PAM_ZERO_TRUST,
    }


def test_mapper_updates_same_contract_with_immutable_modification_publication() -> None:
    initial = map_decp_contract(
        DecpContract.model_validate(_record()),
        collection_job_id=uuid4(),
        collected_at=NOW,
        retention_until=NOW + timedelta(days=3650),
    )
    modification = map_decp_contract(
        DecpContract.model_validate(
            _record(
                booleanmodification=True,
                idmodification="MOD-1",
                objetmodification="Avenant audit ISO 27001 et PAM",
                datepublicationdonneesmodification="2026-09-20",
                datenotificationmodification="2026-09-15",
                dureemoismodification=18,
                montantmodification=320000,
            )
        ),
        collection_job_id=uuid4(),
        collected_at=NOW,
        retention_until=NOW + timedelta(days=3650),
    )

    assert initial is not None and modification is not None
    assert initial.procurement.contract is not None
    assert modification.procurement.contract is not None
    assert modification.procurement.publication.kind is ProcurementPublicationKind.AMENDMENT
    assert (
        modification.procurement.publication.revision_key
        != initial.procurement.publication.revision_key
    )
    assert (
        modification.procurement.contract.contract_key
        == initial.procurement.contract.contract_key
    )
    assert modification.procurement.contract.status is ContractStatus.ACTIVE


def test_mapper_drops_unrelated_contract() -> None:
    assert (
        map_decp_contract(
            DecpContract.model_validate(
                _record(
                    objet="Fourniture de mobilier de bureau",
                    codecpv="39100000",
                    procedure="Appel d'offres mobilier",
                )
            ),
            collection_job_id=uuid4(),
            collected_at=NOW,
            retention_until=NOW + timedelta(days=3650),
        )
        is None
    )


def _record(**changes: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "id": "MARCHE-001",
        "nature": "Marché",
        "objet": "Audit ISO 27001 et solution PAM",
        "codecpv": "72000000",
        "procedure": "Appel d'offres ouvert",
        "acheteur_id": "11111111111111",
        "acheteur_nom": "Métropole Exemple",
        "dureemois": 6,
        "datenotification": "2026-08-31",
        "datepublicationdonnees": "2026-09-02",
        "montant": 250000,
        "titulaire_denominationsociale_1": "Provider SAS",
        "titulaire_id_1": "22222222222222",
        "titulaire_typeidentifiant_1": "SIRET",
        "booleanmodification": False,
        "idmodification": None,
        "objetmodification": None,
        "datenotificationmodification": None,
        "dureemoismodification": None,
        "datepublicationdonneesmodification": None,
        "montantmodification": None,
        "titulairesmodification": None,
        "source": "DECP",
        "updated_at": "2026-09-02T12:00:00Z",
    }
    payload.update(changes)
    return payload
