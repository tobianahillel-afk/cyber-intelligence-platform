from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from cip.main import create_app
from cip.modules.evidence.infrastructure.models import EvidenceRecord
from cip.modules.opportunities.domain.entities import CommercialSignal, SignalType
from cip.modules.opportunities.infrastructure.generation import generate_siem_soc_opportunity
from cip.modules.opportunities.infrastructure.signals import store_commercial_signal
from cip.modules.organizations.infrastructure.models import OrganizationRecord
from cip.shared.persistence.dependencies import get_database_session
from cip.shared.persistence.metadata import get_metadata

NOW = datetime(2026, 8, 4, 0, 0, tzinfo=UTC)


@pytest.fixture
def client_and_session() -> Iterator[tuple[TestClient, Session]]:
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    get_metadata().create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)
    session = factory()
    application = create_app()

    def override_session() -> Iterator[Session]:
        yield session

    application.dependency_overrides[get_database_session] = override_session
    with TestClient(application) as client:
        yield client, session
    session.close()


def test_health_reports_phase_version(client_and_session: tuple[TestClient, Session]) -> None:
    client, _ = client_and_session

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": "0.5.0"}


def test_empty_opportunity_list(client_and_session: tuple[TestClient, Session]) -> None:
    client, _ = client_and_session

    response = client.get("/v1/opportunities")

    assert response.status_code == 200
    assert response.json()["items"] == []
    assert response.json()["total"] == 0


def test_list_detail_review_and_override_contracts(
    client_and_session: tuple[TestClient, Session],
) -> None:
    client, session = client_and_session
    opportunity_id = _seed_opportunity(session)

    list_response = client.get(
        "/v1/opportunities",
        params={"state": "needs_review", "min_score": 50},
    )
    assert list_response.status_code == 200
    item = list_response.json()["items"][0]
    assert item["id"] == str(opportunity_id)
    assert item["organization"] == "API Example"
    assert item["evidence_count"] == 2

    detail_response = client.get(f"/v1/opportunities/{opportunity_id}")
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert len(detail["components"]) == 6
    assert len(detail["evidence"]) == 2
    component_id = detail["components"][0]["id"]

    review_response = client.post(
        f"/v1/opportunities/{opportunity_id}/review",
        json={"action": "qualify", "actor": "api-analyst", "note": "Verified"},
    )
    assert review_response.status_code == 200
    assert review_response.json()["state"] == "qualified"

    override_response = client.patch(
        f"/v1/opportunities/{opportunity_id}/score-components/{component_id}",
        json={"actor": "api-analyst", "value": 0.2, "reason": "Adjusted"},
    )
    assert override_response.status_code == 200
    assert 0 <= override_response.json()["score"] <= 100

    updated = client.get(f"/v1/opportunities/{opportunity_id}").json()
    assert updated["opportunity"]["state"] == "qualified"
    assert updated["reviews"][0]["action"] == "override_score_component"
    assert updated["components"][0]["analyst_overridden"] is True


def test_api_validation_and_not_found_responses(
    client_and_session: tuple[TestClient, Session],
) -> None:
    client, session = client_and_session
    opportunity_id = _seed_opportunity(session)
    detail = client.get(f"/v1/opportunities/{opportunity_id}").json()
    component_id = detail["components"][0]["id"]
    missing = uuid4()

    assert client.get(f"/v1/opportunities/{missing}").status_code == 404
    assert (
        client.post(
            f"/v1/opportunities/{missing}/review",
            json={"action": "qualify", "actor": "analyst"},
        ).status_code
        == 404
    )
    assert (
        client.post(
            f"/v1/opportunities/{opportunity_id}/review",
            json={"action": "reject", "actor": "analyst"},
        ).status_code
        == 422
    )
    assert (
        client.post(
            f"/v1/opportunities/{opportunity_id}/review",
            json={
                "action": "snooze",
                "actor": "analyst",
                "snoozed_until": "2026-08-05T00:00:00",
            },
        ).status_code
        == 422
    )
    assert (
        client.patch(
            f"/v1/opportunities/{opportunity_id}/score-components/{component_id}",
            json={"actor": "analyst"},
        ).status_code
        == 422
    )
    assert (
        client.patch(
            f"/v1/opportunities/{opportunity_id}/score-components/{missing}",
            json={"actor": "analyst", "value": 0.5},
        ).status_code
        == 404
    )


def test_list_query_validation(client_and_session: tuple[TestClient, Session]) -> None:
    client, _ = client_and_session

    assert client.get("/v1/opportunities", params={"min_score": 101}).status_code == 422
    assert client.get("/v1/opportunities", params={"limit": 0}).status_code == 422
    assert client.get("/v1/opportunities", params={"state": "unknown"}).status_code == 422


def _seed_opportunity(session: Session) -> UUID:
    organization_id = uuid4()
    evidence_ids = (uuid4(), uuid4())
    session.add(
        OrganizationRecord(
            id=organization_id,
            canonical_name="API Example",
            legal_name=None,
            country_code="FR",
            website_url="https://api-example.test",
            registration_ids=[],
            created_at=NOW,
            updated_at=NOW,
        )
    )
    session.add_all(
        EvidenceRecord(
            id=evidence_id,
            source_id=f"api-source-{index}",
            source_record_key=f"api-record-{index}",
            source_url=f"https://source.example/{index}",
            summary="Public buying-intent evidence",
            confidence=0.9,
            collected_at=NOW,
            published_at=NOW - timedelta(minutes=index),
            observed_at=None,
            content_hash_sha256=None,
            raw_storage_uri=None,
            raw_storage_permitted=False,
            retention_until=NOW + timedelta(days=365),
        )
        for index, evidence_id in enumerate(evidence_ids, start=1)
    )
    session.flush()
    store_commercial_signal(
        session,
        _signal(
            organization_id,
            evidence_ids[0],
            SignalType.PUBLIC_TENDER,
            "SIEM public tender",
        ),
    )
    store_commercial_signal(
        session,
        _signal(
            organization_id,
            evidence_ids[1],
            SignalType.JOB_POSTING,
            "Hiring a SOC analyst for Microsoft Sentinel",
        ),
    )
    opportunity_id = generate_siem_soc_opportunity(session, organization_id, now=NOW)
    assert opportunity_id is not None
    return opportunity_id


def _signal(
    organization_id: UUID,
    evidence_id: UUID,
    signal_type: SignalType,
    title: str,
) -> CommercialSignal:
    return CommercialSignal(
        organization_id=organization_id,
        evidence_id=evidence_id,
        signal_type=signal_type,
        title=title,
        summary=title,
        confidence=0.9,
        matched_terms=("siem", "soc"),
        published_at=NOW - timedelta(minutes=10),
        collected_at=NOW,
        expires_at=NOW + timedelta(days=90),
    )
