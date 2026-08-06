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
from cip.modules.organizations.infrastructure.models import OrganizationRecord
from cip.modules.passive_exposure.domain.models import (
    OrganizationLink,
    OrganizationLinkMethod,
    OrganizationLinkStatus,
    PassiveAsset,
    PassiveAssetKind,
    PassiveObservationKind,
    PassiveObservationSnapshot,
    PassiveObservationState,
    TechnologyEvidenceLevel,
    TechnologyObservation,
)
from cip.modules.passive_exposure.infrastructure.models import (
    PassiveAssetRecord,
    PassiveObservationSnapshotRecord,
    PassiveTechnologyRecord,
)
from cip.modules.passive_exposure.infrastructure.projections import (
    persist_passive_snapshots,
)
from cip.shared.config.settings import Settings, get_settings
from cip.shared.persistence.dependencies import get_database_session
from cip.shared.persistence.metadata import get_metadata

CONTROL_TOKEN = "test-control-token-123"
HEADERS = {"X-CIP-Control-Token": CONTROL_TOKEN}
NOW = datetime(2026, 8, 6, 12, tzinfo=UTC)


@pytest.fixture
def passive_client() -> Iterator[tuple[TestClient, Session, UUID, tuple[UUID, UUID]]]:
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
    organization_ids = (uuid4(), uuid4())
    session.add_all(
        (
            _organization(organization_ids[0], "Example Alpha"),
            _organization(organization_ids[1], "Example Beta"),
        )
    )
    asset_ids = persist_passive_snapshots(
        session,
        _current_snapshots(organization_ids),
        now=NOW,
    )
    persist_passive_snapshots(session, (_historical_snapshot(),), now=NOW)
    session.commit()
    current_id = next(
        asset_id
        for asset_id in asset_ids
        if session.get(PassiveAssetRecord, asset_id).asset_value
        == "service.example.com"
    )
    application = create_app()
    settings = Settings(
        environment="test",
        database_url="sqlite+pysqlite://",
        control_plane_token=CONTROL_TOKEN,
    )

    def override_session() -> Iterator[Session]:
        yield session

    def override_settings() -> Settings:
        return settings

    application.dependency_overrides[get_database_session] = override_session
    application.dependency_overrides[get_settings] = override_settings
    with TestClient(application) as client:
        yield client, session, current_id, organization_ids
    session.close()


def test_passive_api_requires_control_plane_authentication(
    passive_client: tuple[TestClient, Session, UUID, tuple[UUID, UUID]],
) -> None:
    client, _, _, _ = passive_client

    response = client.get("/v1/passive-assets")

    assert response.status_code == 401


def test_list_and_detail_preserve_ambiguous_attribution_and_history(
    passive_client: tuple[TestClient, Session, UUID, tuple[UUID, UUID]],
) -> None:
    client, _, asset_id, organization_ids = passive_client

    listed = client.get(
        "/v1/passive-assets",
        headers=HEADERS,
        params={
            "organization_link_status": "review_required",
            "asset_kind": "hostname",
        },
    )

    assert listed.status_code == 200
    payload = listed.json()
    assert payload["total"] == 1
    summary = payload["items"][0]
    assert summary["asset_value"] == "service.example.com"
    assert summary["organization_link_status"] == "review_required"
    assert set(summary["candidate_organization_ids"]) == {
        str(organization_ids[0]),
        str(organization_ids[1]),
    }
    assert summary["exact_organization_id"] is None
    assert summary["exposure_assessment"] == "not_assessed"
    assert summary["source_count"] == 2
    assert summary["independent_source_count"] == 2

    detail_response = client.get(f"/v1/passive-assets/{asset_id}", headers=HEADERS)
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert len(detail["observations"]) == 2
    assert "does not prove" in detail["safety_disclaimer"]
    assert {
        observation["technology"]["product_version"]
        for observation in detail["observations"]
        if observation["technology"] is not None
    } == {"4.2.1"}
    assert {
        (observation["port"], observation["protocol"])
        for observation in detail["observations"]
        if observation["port"] is not None
    } == {(443, "https")}


def test_filters_by_candidate_organization_and_historical_state(
    passive_client: tuple[TestClient, Session, UUID, tuple[UUID, UUID]],
) -> None:
    client, _, _, organization_ids = passive_client

    candidate = client.get(
        "/v1/passive-assets",
        headers=HEADERS,
        params={"organization_id": str(organization_ids[1])},
    )
    historical = client.get(
        "/v1/passive-assets",
        headers=HEADERS,
        params={"historical_only": "true", "asset_kind": "ipv4"},
    )

    assert candidate.status_code == 200
    assert candidate.json()["total"] == 1
    assert historical.status_code == 200
    assert historical.json()["total"] == 1
    assert historical.json()["items"][0]["asset_value"] == "8.8.8.8"


def test_replay_is_idempotent_and_correction_preserves_history(
    passive_client: tuple[TestClient, Session, UUID, tuple[UUID, UUID]],
) -> None:
    client, session, asset_id, organization_ids = passive_client
    snapshots = _current_snapshots(organization_ids)

    persist_passive_snapshots(session, snapshots, now=NOW)
    correction = replace(
        snapshots[0],
        source_record_key="record-a-correction",
        source_url="https://passive-provider-a.example/records/record-a-correction",
        state=PassiveObservationState.CORRECTED,
        modified_at=NOW + timedelta(days=1),
        active=False,
        historical_only=True,
        supersedes_record_key=snapshots[0].source_record_key,
    )
    persist_passive_snapshots(
        session,
        (correction,),
        now=NOW + timedelta(days=1),
    )
    session.commit()

    assert session.scalar(select(func.count(PassiveAssetRecord.id))) == 2
    assert (
        session.scalar(select(func.count(PassiveObservationSnapshotRecord.id)))
        == 4
    )
    assert session.scalar(select(func.count(PassiveTechnologyRecord.id))) == 3
    detail = client.get(f"/v1/passive-assets/{asset_id}", headers=HEADERS).json()
    assert len(detail["observations"]) == 3
    assert "corrected" in {
        observation["state"] for observation in detail["observations"]
    }
    projected = detail["asset"]
    assert projected["state"] == "current"
    assert projected["organization_link_status"] == "exact"
    assert projected["exact_organization_id"] == str(organization_ids[1])
    assert projected["candidate_organization_ids"] == []
    assert projected["independent_source_count"] == 1
    assert projected["has_conflict"] is True
    assert projected["exposure_assessment"] == "not_assessed"


def test_source_record_cannot_move_between_assets(
    passive_client: tuple[TestClient, Session, UUID, tuple[UUID, UUID]],
) -> None:
    _, session, _, organization_ids = passive_client
    original = _current_snapshots(organization_ids)[0]
    moved = replace(
        original,
        asset=PassiveAsset(PassiveAssetKind.HOSTNAME, "other.example.com"),
        modified_at=NOW + timedelta(minutes=1),
    )

    with pytest.raises(ValueError, match="ownership conflicts"):
        persist_passive_snapshots(session, (moved,), now=NOW + timedelta(minutes=1))

    session.rollback()


def test_batch_supersession_target_must_stay_on_same_asset(
    passive_client: tuple[TestClient, Session, UUID, tuple[UUID, UUID]],
) -> None:
    _, session, _, organization_ids = passive_client
    template = _current_snapshots(organization_ids)[0]
    original = replace(
        template,
        source_id="batch-provider",
        source_record_key="batch-original",
        source_url="https://batch-provider.example/records/original",
    )
    correction = replace(
        original,
        source_record_key="batch-correction",
        source_url="https://batch-provider.example/records/correction",
        asset=PassiveAsset(PassiveAssetKind.HOSTNAME, "other.example.com"),
        state=PassiveObservationState.CORRECTED,
        modified_at=NOW + timedelta(minutes=1),
        active=False,
        historical_only=True,
        supersedes_record_key="batch-original",
    )

    with pytest.raises(ValueError, match="supersession target"):
        persist_passive_snapshots(
            session,
            (correction, original),
            now=NOW + timedelta(minutes=1),
        )

    session.rollback()


def test_missing_passive_asset_returns_not_found(
    passive_client: tuple[TestClient, Session, UUID, tuple[UUID, UUID]],
) -> None:
    client, _, _, _ = passive_client

    response = client.get(
        "/v1/passive-assets/00000000-0000-0000-0000-000000000000",
        headers=HEADERS,
    )

    assert response.status_code == 404


def _organization(organization_id: UUID, name: str) -> OrganizationRecord:
    return OrganizationRecord(
        id=organization_id,
        canonical_name=name,
        legal_name=name,
        country_code="FR",
        website_url="https://example.com",
        registration_ids=[],
        created_at=NOW,
        updated_at=NOW,
    )


def _current_snapshots(
    organization_ids: tuple[UUID, UUID],
) -> tuple[PassiveObservationSnapshot, ...]:
    technology = TechnologyObservation(
        evidence_level=TechnologyEvidenceLevel.OBSERVED_VERSION,
        product_name="Example Server",
        product_version="4.2.1",
    )
    first = _snapshot(
        source_id="passive-provider-a",
        source_record_key="record-a",
        organization_id=organization_ids[0],
        technology=technology,
    )
    second = _snapshot(
        source_id="passive-provider-b",
        source_record_key="record-b",
        organization_id=organization_ids[1],
        technology=technology,
    )
    return first, second


def _historical_snapshot() -> PassiveObservationSnapshot:
    return PassiveObservationSnapshot(
        source_id="historical-passive-provider",
        source_record_key="historical-ip",
        source_url="https://historical-passive-provider.example/records/historical-ip",
        asset=PassiveAsset(PassiveAssetKind.IPV4, "8.8.8.8"),
        observation_kind=PassiveObservationKind.PASSIVE_DNS,
        state=PassiveObservationState.HISTORICAL,
        observed_at=NOW - timedelta(days=365),
        published_at=NOW - timedelta(days=364),
        modified_at=NOW - timedelta(days=364),
        expires_at=NOW - timedelta(days=300),
        confidence=0.5,
        organization_link=OrganizationLink(
            status=OrganizationLinkStatus.UNRESOLVED,
            method=OrganizationLinkMethod.NONE,
            confidence=0.0,
        ),
        active=False,
        historical_only=True,
    )


def _snapshot(
    *,
    source_id: str,
    source_record_key: str,
    organization_id: UUID,
    technology: TechnologyObservation,
) -> PassiveObservationSnapshot:
    return PassiveObservationSnapshot(
        source_id=source_id,
        source_record_key=source_record_key,
        source_url=f"https://{source_id}.example/records/{source_record_key}",
        asset=PassiveAsset(PassiveAssetKind.HOSTNAME, "service.example.com"),
        observation_kind=PassiveObservationKind.VERSION,
        state=PassiveObservationState.CURRENT,
        observed_at=NOW - timedelta(hours=2),
        published_at=NOW - timedelta(hours=1),
        modified_at=NOW,
        expires_at=NOW + timedelta(days=30),
        confidence=0.8,
        organization_link=OrganizationLink(
            status=OrganizationLinkStatus.EXACT,
            method=OrganizationLinkMethod.EXACT_OFFICIAL_DOMAIN,
            confidence=1.0,
            organization_id=organization_id,
            reasons=("Official domain ownership",),
        ),
        technology=technology,
        port=443,
        protocol="https",
    )
