from __future__ import annotations

from collections.abc import Iterator
from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from cip.main import create_app
from cip.modules.incident_intelligence.domain.models import (
    IncidentClaimSnapshot,
    IncidentClaimType,
    IncidentSourceKind,
    IncidentType,
    OrganizationLinkStatus,
)
from cip.modules.incident_intelligence.infrastructure.models import (
    IncidentClaimSnapshotRecord,
    IncidentRecord,
)
from cip.modules.incident_intelligence.infrastructure.projections import (
    persist_incident_claims,
)
from cip.shared.config.settings import Settings, get_settings
from cip.shared.persistence.dependencies import get_database_session
from cip.shared.persistence.metadata import get_metadata

CONTROL_TOKEN = "test-control-token-123"
HEADERS = {"X-CIP-Control-Token": CONTROL_TOKEN}
NOW = datetime(2026, 8, 6, 12, 0, tzinfo=UTC)


@pytest.fixture
def client_and_session() -> Iterator[tuple[TestClient, Session]]:
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    get_metadata().create_all(engine)
    factory = sessionmaker(
        bind=engine,
        expire_on_commit=False,
        autoflush=False,
    )
    session = factory()
    persist_incident_claims(session, _current_claims(), now=NOW)
    persist_incident_claims(session, (_historical_claim(),), now=NOW)
    session.commit()
    settings = Settings(
        environment="test",
        database_url="sqlite+pysqlite://",
        control_plane_token=CONTROL_TOKEN,
    )
    application = create_app()

    def override_session() -> Iterator[Session]:
        yield session

    def override_settings() -> Settings:
        return settings

    application.dependency_overrides[get_database_session] = override_session
    application.dependency_overrides[get_settings] = override_settings
    with TestClient(application) as client:
        yield client, session
    session.close()


def test_incident_api_requires_control_plane_authentication(
    client_and_session: tuple[TestClient, Session],
) -> None:
    client, _ = client_and_session

    response = client.get("/v1/incidents")

    assert response.status_code == 401


def test_list_and_detail_separate_claims_from_confirmation(
    client_and_session: tuple[TestClient, Session],
) -> None:
    client, _ = client_and_session

    listed = client.get(
        "/v1/incidents",
        headers=HEADERS,
        params={"officially_confirmed": "true", "claim_type": "attacker_allegation"},
    )

    assert listed.status_code == 200
    payload = listed.json()
    assert payload["total"] == 1
    summary = payload["items"][0]
    assert summary["incident_key"] == "incident:example:current"
    assert summary["status"] == "confirmed"
    assert summary["claim_count"] == 4
    assert summary["independent_source_count"] == 3
    assert summary["officially_confirmed"] is True
    assert summary["organization_link_status"] == "review_required"

    detail_response = client.get(
        "/v1/incidents/incident:example:current",
        headers=HEADERS,
    )
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert len(detail["claims"]) == 4
    assert detail["claimed_organization_names"] == ["Example SA"]
    assert "An allegation is not an official confirmation" in detail["safety_disclaimer"]
    assert {
        claim["claim_type"] for claim in detail["claims"]
    } == {
        "attacker_allegation",
        "media_report",
        "company_confirmation",
    }


def test_replay_is_idempotent_and_retraction_preserves_history(
    client_and_session: tuple[TestClient, Session],
) -> None:
    client, session = client_and_session
    claims = _current_claims()

    persist_incident_claims(session, claims, now=NOW)
    retraction = replace(
        claims[1],
        claim_type=IncidentClaimType.RETRACTION,
        title="Media report retracted",
        summary="The publisher retracted the earlier report.",
        modified_at=NOW + timedelta(days=1),
        supersedes_record_key=claims[1].source_record_key,
    )
    persist_incident_claims(
        session,
        (retraction,),
        now=NOW + timedelta(days=1),
    )
    session.commit()

    assert session.scalar(select(func.count(IncidentRecord.id))) == 2
    assert (
        session.scalar(select(func.count(IncidentClaimSnapshotRecord.id)))
        == 6
    )
    detail = client.get(
        "/v1/incidents/incident:example:current",
        headers=HEADERS,
    ).json()
    assert detail["incident"]["status"] == "confirmed"
    assert detail["incident"]["has_retraction"] is True
    assert detail["incident"]["claim_count"] == 4
    assert len(detail["claims"]) == 5


def test_filters_historical_incidents_and_missing_keys(
    client_and_session: tuple[TestClient, Session],
) -> None:
    client, _ = client_and_session

    historical = client.get(
        "/v1/incidents",
        headers=HEADERS,
        params={"historical_only": "true", "source_kind": "media"},
    )
    missing = client.get(
        "/v1/incidents/incident:missing",
        headers=HEADERS,
    )

    assert historical.status_code == 200
    assert historical.json()["total"] == 1
    assert historical.json()["items"][0]["incident_key"] == "incident:example:history"
    assert missing.status_code == 404


def _current_claims() -> tuple[IncidentClaimSnapshot, ...]:
    allegation = _claim(
        source_id="ransomware-metadata",
        record_key="listing-1",
        claim_type=IncidentClaimType.ATTACKER_ALLEGATION,
        source_kind=IncidentSourceKind.RANSOMWARE_METADATA,
        confidence=0.35,
    )
    media_a = replace(
        _claim(
            source_id="media-a",
            record_key="report-a",
            claim_type=IncidentClaimType.MEDIA_REPORT,
            source_kind=IncidentSourceKind.MEDIA,
        ),
        independence_key="wire-story-1",
    )
    media_b = replace(
        media_a,
        source_id="media-b",
        source_record_key="report-b",
        source_url="https://media-b.example/incidents/report-b",
    )
    company = replace(
        _claim(
            source_id="company-pressroom",
            record_key="statement-1",
            claim_type=IncidentClaimType.COMPANY_CONFIRMATION,
            source_kind=IncidentSourceKind.COMPANY,
            confidence=1.0,
        ),
        confirmed_at=NOW + timedelta(hours=2),
        modified_at=NOW + timedelta(hours=2),
    )
    return allegation, media_a, media_b, company


def _historical_claim() -> IncidentClaimSnapshot:
    return replace(
        _claim(
            source_id="historical-media",
            record_key="archive-1",
            claim_type=IncidentClaimType.MEDIA_REPORT,
            source_kind=IncidentSourceKind.MEDIA,
        ),
        incident_key="incident:example:history",
        title="Historical public incident report",
        published_at=NOW - timedelta(days=365),
        modified_at=NOW - timedelta(days=365),
        occurrence_start_at=NOW - timedelta(days=366),
        discovered_at=NOW - timedelta(days=365),
        historical_only=True,
    )


def _claim(
    *,
    source_id: str,
    record_key: str,
    claim_type: IncidentClaimType,
    source_kind: IncidentSourceKind,
    confidence: float = 0.7,
) -> IncidentClaimSnapshot:
    return IncidentClaimSnapshot(
        source_id=source_id,
        source_kind=source_kind,
        source_record_key=record_key,
        source_url=f"https://{source_id}.example/incidents/{record_key}",
        incident_key="incident:example:current",
        claim_type=claim_type,
        incident_type=IncidentType.RANSOMWARE,
        title="Example public incident claim",
        summary="Bounded public metadata describing the incident claim.",
        claimed_organization_name="Example SA",
        organization_id=None,
        organization_link_status=OrganizationLinkStatus.REVIEW_REQUIRED,
        published_at=NOW,
        modified_at=NOW,
        occurrence_start_at=NOW - timedelta(hours=1),
        discovered_at=NOW,
        confidence=confidence,
        metadata_only=True,
    )
