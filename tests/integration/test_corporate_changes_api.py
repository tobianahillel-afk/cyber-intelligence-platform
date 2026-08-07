from __future__ import annotations

from collections.abc import Iterator
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from cip.main import create_app
from cip.modules.corporate_changes.domain.models import (
    ChangeClaimSnapshot,
    ChangeClaimType,
    ChangeEventType,
    ChangeServiceMapping,
    ChangeSourceKind,
    OrganizationLinkStatus,
)
from cip.modules.corporate_changes.infrastructure.models import (
    CorporateChangeClaimSnapshotRecord,
    CorporateChangeEventRecord,
    CorporateChangeServiceMappingRecord,
)
from cip.modules.corporate_changes.infrastructure.projections import (
    persist_change_claims,
    persist_service_mappings,
)
from cip.modules.organizations.infrastructure.models import OrganizationRecord
from cip.shared.config.settings import Settings, get_settings
from cip.shared.persistence.dependencies import get_database_session
from cip.shared.persistence.metadata import get_metadata

CONTROL_TOKEN = "test-control-token-123"
HEADERS = {"X-CIP-Control-Token": CONTROL_TOKEN}
NOW = datetime(2026, 8, 7, 12, 0, tzinfo=UTC)


@pytest.fixture
def corporate_changes_client() -> Iterator[tuple[TestClient, Session, UUID, str]]:
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    get_metadata().create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)
    session = factory()
    organization_id = uuid4()
    session.add(_organization(organization_id))
    event_key = "example-company:cloud-program:2026"
    event_id = persist_change_claims(
        session,
        (_official_claim(organization_id, event_key),),
        now=NOW,
    )[0]
    persist_service_mappings(
        session,
        event_id,
        (
            ChangeServiceMapping(
                event_key=event_key,
                service_family="cloud_security",
                rationale="Public cloud transformation may require cloud security review.",
                confidence=0.7,
            ),
        ),
        now=NOW,
    )
    session.commit()
    application = create_app()
    settings = Settings(
        environment="test",
        database_url="sqlite+pysqlite://",
        control_plane_token=CONTROL_TOKEN,
        _env_file=None,
    )

    def override_session() -> Iterator[Session]:
        yield session

    def override_settings() -> Settings:
        return settings

    application.dependency_overrides[get_database_session] = override_session
    application.dependency_overrides[get_settings] = override_settings
    with TestClient(application) as client:
        yield client, session, event_id, event_key
    session.close()


def test_corporate_change_api_requires_control_plane_authentication(
    corporate_changes_client: tuple[TestClient, Session, UUID, str],
) -> None:
    client, _, _, _ = corporate_changes_client

    response = client.get("/v1/corporate-changes")

    assert response.status_code == 401


def test_list_and_detail_keep_evidence_and_service_mapping_separate(
    corporate_changes_client: tuple[TestClient, Session, UUID, str],
) -> None:
    client, _, _, event_key = corporate_changes_client

    listed = client.get(
        "/v1/corporate-changes",
        headers=HEADERS,
        params={"status": "confirmed", "event_type": "cloud_digital_program"},
    )

    assert listed.status_code == 200
    payload = listed.json()
    assert payload["total"] == 1
    assert payload["items"][0]["status"] == "confirmed"
    assert payload["items"][0]["officially_confirmed"] is True

    detailed = client.get(
        f"/v1/corporate-changes/{event_key}",
        headers=HEADERS,
    )

    assert detailed.status_code == 200
    detail = detailed.json()
    assert len(detail["claims"]) == 1
    assert detail["claims"][0]["source_kind"] == "company"
    assert detail["service_mappings"] == [
        {
            "id": detail["service_mappings"][0]["id"],
            "service_family": "cloud_security",
            "rationale": "Public cloud transformation may require cloud security review.",
            "confidence": 0.7,
            "created_at": detail["service_mappings"][0]["created_at"],
        }
    ]
    assert "not official confirmation" in detail["evidence_disclaimer"]


def test_replay_is_idempotent_and_retraction_preserves_history(
    corporate_changes_client: tuple[TestClient, Session, UUID, str],
) -> None:
    _, session, event_id, event_key = corporate_changes_client
    organization_id = session.scalar(select(OrganizationRecord.id))
    assert organization_id is not None
    original = _official_claim(organization_id, event_key)
    original_snapshot_count = session.scalar(
        select(func.count(CorporateChangeClaimSnapshotRecord.id))
    )

    persist_change_claims(session, (original,), now=NOW)
    retraction = replace(
        original,
        source_record_key="company-r2",
        article_id="company-r2",
        claim_type=ChangeClaimType.RETRACTION,
        title="Example Company retracts the earlier announcement",
        excerpt="The company retracts its earlier public announcement.",
        modified_at=NOW + timedelta(hours=2),
        supersedes_record_key=original.source_record_key,
    )
    persist_change_claims(session, (retraction,), now=NOW + timedelta(hours=2))
    session.commit()

    event = session.get(CorporateChangeEventRecord, event_id)
    assert event is not None
    assert event.status == "retracted"
    assert event.officially_confirmed is False
    assert session.scalar(select(func.count(CorporateChangeEventRecord.id))) == 1
    assert session.scalar(
        select(func.count(CorporateChangeClaimSnapshotRecord.id))
    ) == original_snapshot_count + 1


def test_service_mapping_updates_without_mutating_raw_evidence(
    corporate_changes_client: tuple[TestClient, Session, UUID, str],
) -> None:
    _, session, event_id, event_key = corporate_changes_client
    claim_count = session.scalar(select(func.count(CorporateChangeClaimSnapshotRecord.id)))

    persist_service_mappings(
        session,
        event_id,
        (
            ChangeServiceMapping(
                event_key=event_key,
                service_family="cloud_security",
                rationale="Updated analyst rationale based on the same public evidence.",
                confidence=0.8,
            ),
        ),
        now=NOW + timedelta(minutes=5),
    )
    session.commit()

    mapping = session.scalar(select(CorporateChangeServiceMappingRecord))
    assert mapping is not None
    assert mapping.confidence == 0.8
    assert session.scalar(
        select(func.count(CorporateChangeClaimSnapshotRecord.id))
    ) == claim_count


def test_missing_change_event_returns_not_found(
    corporate_changes_client: tuple[TestClient, Session, UUID, str],
) -> None:
    client, _, _, _ = corporate_changes_client

    response = client.get(
        "/v1/corporate-changes/does-not-exist",
        headers=HEADERS,
    )

    assert response.status_code == 404


def _organization(organization_id: UUID) -> OrganizationRecord:
    return OrganizationRecord(
        id=organization_id,
        canonical_name="Example Company",
        legal_name="Example Company SAS",
        country_code="FR",
        website_url="https://example.com",
        registration_ids=[],
        created_at=NOW,
        updated_at=NOW,
    )


def _official_claim(organization_id: UUID, event_key: str) -> ChangeClaimSnapshot:
    return ChangeClaimSnapshot(
        source_id="official-corporate-disclosures",
        source_kind=ChangeSourceKind.COMPANY,
        source_record_key="company-r1",
        article_id="company-r1",
        source_url="https://example.com/news/cloud-program",
        event_key=event_key,
        claim_type=ChangeClaimType.CONFIRMATION,
        event_type=ChangeEventType.CLOUD_DIGITAL_PROGRAM,
        title="Example Company announces a cloud transformation program",
        excerpt="The company publicly announces its cloud transformation program.",
        claimed_organization_name="Example Company",
        organization_id=organization_id,
        organization_link_status=OrganizationLinkStatus.EXACT,
        published_at=NOW - timedelta(hours=1),
        modified_at=NOW,
        event_at=NOW - timedelta(days=2),
        independence_key="official-corporate-disclosures",
        confidence=1.0,
    )
