from __future__ import annotations

from collections.abc import Iterator
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from cip.main import create_app
from cip.modules.threat_telemetry.domain.models import (
    IndicatorSnapshot,
    IndicatorState,
    IndicatorType,
    SensorScope,
    TelemetryRelation,
    TelemetryRelationType,
    TelemetrySourceKind,
)
from cip.modules.threat_telemetry.infrastructure.models import (
    ThreatIndicatorRecord,
    ThreatIndicatorRelationRecord,
    ThreatIndicatorSnapshotRecord,
)
from cip.modules.threat_telemetry.infrastructure.projections import (
    persist_indicator_snapshots,
)
from cip.shared.config.settings import Settings, get_settings
from cip.shared.persistence.dependencies import get_database_session
from cip.shared.persistence.metadata import get_metadata

CONTROL_TOKEN = "test-control-token-123"
HEADERS = {"X-CIP-Control-Token": CONTROL_TOKEN}
NOW = datetime(2026, 8, 6, 12, 0, tzinfo=UTC)


@pytest.fixture
def client_session_and_id() -> Iterator[tuple[TestClient, Session, UUID]]:
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
    ids = persist_indicator_snapshots(session, _initial_snapshots(), now=NOW)
    persist_indicator_snapshots(session, (_historical_snapshot(),), now=NOW)
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
        current_id = next(
            indicator_id
            for indicator_id in ids
            if session.get(ThreatIndicatorRecord, indicator_id).indicator_value
            == "malicious.example"
        )
        yield client, session, current_id
    session.close()


def test_threat_api_requires_control_plane_authentication(
    client_session_and_id: tuple[TestClient, Session, UUID],
) -> None:
    client, _, _ = client_session_and_id

    response = client.get("/v1/threat-indicators")

    assert response.status_code == 401


def test_list_and_detail_preserve_conflicts_and_relations(
    client_session_and_id: tuple[TestClient, Session, UUID],
) -> None:
    client, _, indicator_id = client_session_and_id

    listed = client.get(
        "/v1/threat-indicators",
        headers=HEADERS,
        params={"has_conflict": "true", "source_kind": "stix_taxii"},
    )

    assert listed.status_code == 200
    payload = listed.json()
    assert payload["total"] == 1
    summary = payload["items"][0]
    assert summary["state"] == "benign"
    assert set(summary["observed_states"]) == {"benign", "malicious"}
    assert summary["source_count"] == 3
    assert summary["independent_source_count"] == 1
    assert summary["has_conflict"] is True

    detail_response = client.get(
        f"/v1/threat-indicators/{indicator_id}",
        headers=HEADERS,
    )
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert len(detail["snapshots"]) == 3
    assert "does not prove" in detail["safety_disclaimer"]
    assert {
        relation["target_key"]
        for snapshot in detail["snapshots"]
        for relation in snapshot["relations"]
    } == {"campaign:example", "CVE-2026-12345"}


def test_replay_is_idempotent_and_reclassification_preserves_history(
    client_session_and_id: tuple[TestClient, Session, UUID],
) -> None:
    client, session, indicator_id = client_session_and_id
    snapshots = _initial_snapshots()

    persist_indicator_snapshots(session, snapshots, now=NOW)
    correction = replace(
        snapshots[0],
        state=IndicatorState.SINKHOLED,
        modified_at=NOW + timedelta(days=1),
        active=False,
        supersedes_record_key=snapshots[0].source_record_key,
    )
    persist_indicator_snapshots(
        session,
        (correction,),
        now=NOW + timedelta(days=1),
    )
    session.commit()

    assert session.scalar(select(func.count(ThreatIndicatorRecord.id))) == 2
    assert (
        session.scalar(select(func.count(ThreatIndicatorSnapshotRecord.id)))
        == 5
    )
    assert (
        session.scalar(select(func.count(ThreatIndicatorRelationRecord.id)))
        == 6
    )
    detail = client.get(
        f"/v1/threat-indicators/{indicator_id}",
        headers=HEADERS,
    ).json()
    assert len(detail["snapshots"]) == 4
    assert "sinkholed" in {
        snapshot["state"] for snapshot in detail["snapshots"]
    }


def test_filters_historical_and_missing_indicator(
    client_session_and_id: tuple[TestClient, Session, UUID],
) -> None:
    client, _, _ = client_session_and_id

    historical = client.get(
        "/v1/threat-indicators",
        headers=HEADERS,
        params={"historical_only": "true", "indicator_type": "ipv4"},
    )
    missing = client.get(
        "/v1/threat-indicators/00000000-0000-0000-0000-000000000000",
        headers=HEADERS,
    )

    assert historical.status_code == 200
    assert historical.json()["total"] == 1
    assert historical.json()["items"][0]["indicator_value"] == "8.8.8.8"
    assert missing.status_code == 404


def _initial_snapshots() -> tuple[IndicatorSnapshot, ...]:
    relation_campaign = TelemetryRelation(
        relation_type=TelemetryRelationType.CAMPAIGN,
        target_key="campaign:example",
        confidence=0.8,
    )
    relation_cve = TelemetryRelation(
        relation_type=TelemetryRelationType.VULNERABILITY,
        target_key="CVE-2026-12345",
        confidence=0.7,
    )
    first = replace(
        _snapshot(
            source_id="cti-a",
            source_kind=TelemetrySourceKind.STIX_TAXII,
            record_key="indicator-a",
        ),
        independence_key="upstream-feed-1",
        relations=(relation_campaign, relation_cve),
    )
    syndicated = replace(
        first,
        source_id="cti-b",
        source_record_key="indicator-b",
        source_url="https://cti-b.example/records/indicator-b",
    )
    benign = replace(
        _snapshot(
            source_id="authoritative",
            source_kind=TelemetrySourceKind.PROVIDER,
            record_key="indicator-c",
        ),
        state=IndicatorState.BENIGN,
        confidence=1.0,
        source_precedence=90,
        modified_at=NOW + timedelta(hours=1),
    )
    return first, syndicated, benign


def _historical_snapshot() -> IndicatorSnapshot:
    return IndicatorSnapshot(
        source_id="historical-feed",
        source_kind=TelemetrySourceKind.PROVIDER,
        source_record_key="historical-ip",
        source_url="https://historical-feed.example/records/historical-ip",
        indicator_type=IndicatorType.IPV4,
        indicator_value="8.8.8.8",
        state=IndicatorState.HISTORICAL,
        published_at=NOW - timedelta(days=365),
        modified_at=NOW - timedelta(days=365),
        first_seen_at=NOW - timedelta(days=400),
        last_seen_at=NOW - timedelta(days=365),
        expires_at=NOW - timedelta(days=300),
        sensor_scope=SensorScope.GLOBAL,
        confidence=0.5,
        active=False,
        historical_only=True,
    )


def _snapshot(
    *,
    source_id: str,
    source_kind: TelemetrySourceKind,
    record_key: str,
) -> IndicatorSnapshot:
    return IndicatorSnapshot(
        source_id=source_id,
        source_kind=source_kind,
        source_record_key=record_key,
        source_url=f"https://{source_id}.example/records/{record_key}",
        indicator_type=IndicatorType.DOMAIN,
        indicator_value="malicious.example",
        state=IndicatorState.MALICIOUS,
        published_at=NOW,
        modified_at=NOW,
        first_seen_at=NOW - timedelta(hours=2),
        last_seen_at=NOW,
        expires_at=NOW + timedelta(days=30),
        sensor_scope=SensorScope.GLOBAL,
        confidence=0.8,
        source_precedence=50,
        metadata_only=True,
    )
