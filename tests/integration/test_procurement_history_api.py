from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from cip.main import create_app
from cip.modules.organizations.infrastructure.models import OrganizationRecord
from cip.modules.procurement_history.infrastructure.models import (
    ProcurementContractPartyRecord,
    ProcurementContractRecord,
    ProcurementProcedureRecord,
    ProcurementPublicationRecord,
    ProcurementServiceClassificationRecord,
)
from cip.shared.config.settings import Settings, get_settings
from cip.shared.persistence.dependencies import get_database_session
from cip.shared.persistence.metadata import get_metadata

CONTROL_TOKEN = "test-control-token-123"
HEADERS = {"X-CIP-Control-Token": CONTROL_TOKEN}
NOW = datetime(2026, 8, 5, 12, 0, tzinfo=UTC)
BUYER_ID = UUID("00000000-0000-0000-0000-000000000101")
PROCEDURE_ID = UUID("00000000-0000-0000-0000-000000000102")
AWARD_ID = UUID("00000000-0000-0000-0000-000000000103")
AMENDMENT_ID = UUID("00000000-0000-0000-0000-000000000104")
CONTRACT_ID = UUID("00000000-0000-0000-0000-000000000105")


@pytest.fixture
def client() -> Iterator[TestClient]:
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    get_metadata().create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)
    database = factory()
    _seed_contract(database)
    settings = Settings(
        environment="test",
        database_url="sqlite+pysqlite://",
        control_plane_token=CONTROL_TOKEN,
    )
    application = create_app()

    def override_session() -> Iterator[Session]:
        yield database

    def override_settings() -> Settings:
        return settings

    application.dependency_overrides[get_database_session] = override_session
    application.dependency_overrides[get_settings] = override_settings
    with TestClient(application) as test_client:
        yield test_client
    database.close()


def test_contract_api_requires_control_plane_authentication(client: TestClient) -> None:
    response = client.get("/v1/procurement-history/contracts")

    assert response.status_code == 401


def test_contract_list_filters_and_detail_preserve_chronology(client: TestClient) -> None:
    listed = client.get(
        "/v1/procurement-history/contracts",
        headers=HEADERS,
        params={
            "status": "active",
            "family": "iam_iga_pam_zero_trust",
            "renewal_from": "2027-01-01",
            "renewal_to": "2028-01-01",
        },
    )

    assert listed.status_code == 200
    payload = listed.json()
    assert payload["total"] == 1
    contract = payload["items"][0]
    assert contract["id"] == str(CONTRACT_ID)
    assert contract["buyer_name"] == "Métropole Exemple"
    assert contract["provider_names"] == ["Provider SAS"]
    assert contract["renewal_date"] == "2027-08-31"
    assert contract["renewal_date_basis"] == "estimated"
    assert set(contract["source_ids"]) == {"boamp", "decp"}

    detail_response = client.get(
        f"/v1/procurement-history/contracts/{CONTRACT_ID}",
        headers=HEADERS,
    )
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail["procedure_key"] == "decp:procedure:MARCHE-001"
    assert detail["parties"][0]["resolution_status"] == "unresolved"
    assert detail["parties"][0]["official_identifier"] == "22222222222222"
    assert [item["kind"] for item in detail["publications"]] == [
        "award",
        "amendment",
    ]
    assert detail["publications"][0]["source_id"] == "decp"
    assert detail["publications"][1]["source_id"] == "boamp"


def test_contract_api_rejects_invalid_window_and_missing_contract(
    client: TestClient,
) -> None:
    invalid = client.get(
        "/v1/procurement-history/contracts",
        headers=HEADERS,
        params={"renewal_from": "2028-01-01", "renewal_to": "2027-01-01"},
    )
    missing = client.get(
        "/v1/procurement-history/contracts/00000000-0000-0000-0000-000000000999",
        headers=HEADERS,
    )

    assert invalid.status_code == 422
    assert missing.status_code == 404


def _seed_contract(session: Session) -> None:
    session.add(
        OrganizationRecord(
            id=BUYER_ID,
            canonical_name="Métropole Exemple",
            legal_name="Métropole Exemple",
            country_code="FR",
            website_url=None,
            registration_ids=["SIRET:11111111111111"],
            created_at=NOW,
            updated_at=NOW,
        )
    )
    session.add(
        ProcurementProcedureRecord(
            id=PROCEDURE_ID,
            canonical_key="decp:procedure:MARCHE-001",
            buyer_organization_id=BUYER_ID,
            title="Audit ISO 27001 et solution PAM",
            status="awarded",
            first_published_at=NOW,
            latest_published_at=NOW.replace(day=20),
            source_ids=["decp", "boamp"],
            created_at=NOW,
            updated_at=NOW,
        )
    )
    session.add_all(
        (
            ProcurementPublicationRecord(
                id=AWARD_ID,
                procedure_id=PROCEDURE_ID,
                evidence_id=None,
                source_id="decp",
                source_record_key="MARCHE-001",
                revision_key="a" * 64,
                kind="award",
                procedure_status="awarded",
                source_url="https://data.economie.gouv.fr/records/MARCHE-001",
                content_hash_sha256="1" * 64,
                title="Audit ISO 27001 et solution PAM",
                published_at=NOW,
                collected_at=NOW,
                details={"duration_months": 12},
            ),
            ProcurementPublicationRecord(
                id=AMENDMENT_ID,
                procedure_id=PROCEDURE_ID,
                evidence_id=None,
                source_id="boamp",
                source_record_key="26-AMENDMENT",
                revision_key="b" * 64,
                kind="amendment",
                procedure_status="awarded",
                source_url="https://www.boamp.fr/avis/detail/26-AMENDMENT",
                content_hash_sha256="2" * 64,
                title="Avenant audit ISO 27001 et PAM",
                published_at=NOW.replace(day=20),
                collected_at=NOW.replace(day=20),
                details={"amendment": True},
            ),
        )
    )
    session.add(
        ProcurementContractRecord(
            id=CONTRACT_ID,
            contract_key="decp:contract:MARCHE-001",
            procedure_id=PROCEDURE_ID,
            buyer_organization_id=BUYER_ID,
            latest_publication_id=AMENDMENT_ID,
            title="Audit ISO 27001 et solution PAM",
            status="active",
            amount_value=Decimal("320000.00"),
            amount_upper_value=None,
            currency="EUR",
            amount_type="exact",
            award_date=date(2026, 8, 31),
            conclusion_date=None,
            conclusion_date_basis="unknown",
            notification_date=date(2026, 8, 31),
            notification_date_basis="published",
            start_date=None,
            start_date_basis="unknown",
            end_date=date(2027, 8, 31),
            end_date_basis="derived",
            renewal_date=date(2027, 8, 31),
            renewal_date_basis="estimated",
            confidence=0.95,
            created_at=NOW,
            updated_at=NOW.replace(day=20),
        )
    )
    session.add(
        ProcurementContractPartyRecord(
            contract_id=CONTRACT_ID,
            party_key="party-1",
            role="awardee",
            organization_id=None,
            published_name="Provider SAS",
            resolution_status="unresolved",
            confidence=0.9,
            official_identifier="22222222222222",
        )
    )
    session.add(
        ProcurementServiceClassificationRecord(
            contract_id=CONTRACT_ID,
            family="iam_iga_pam_zero_trust",
            matched_terms=["pam"],
            confidence=1.0,
        )
    )
    session.commit()
