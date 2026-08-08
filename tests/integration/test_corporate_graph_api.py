from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from cip.main import create_app
from cip.modules.corporate_graph.domain.models import GraphNodeSnapshot, GraphNodeType
from cip.modules.corporate_graph.infrastructure.models import EntityResolutionBindingRecord
from cip.modules.corporate_graph.infrastructure.projections import persist_graph_nodes
from cip.modules.organizations.infrastructure.models import OrganizationRecord
from cip.shared.config.settings import Settings, get_settings
from cip.shared.persistence.dependencies import get_database_session
from cip.shared.persistence.metadata import get_metadata

CONTROL_TOKEN = "test-control-token-graph"
HEADERS = {"X-CIP-Control-Token": CONTROL_TOKEN}
NOW = datetime(2026, 8, 8, 21, 0, tzinfo=UTC)


@pytest.fixture
def graph_client() -> Iterator[tuple[TestClient, Session, tuple[UUID, UUID]]]:
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    get_metadata().create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)
    session = factory()
    first_id = uuid4()
    second_id = uuid4()
    session.add_all(
        (
            _organization(first_id, "Acme Labs", "https://acme-one.example"),
            _organization(second_id, "ACME LABS", "https://acme-two.example"),
        )
    )
    session.flush()
    persist_graph_nodes(
        session,
        (
            GraphNodeSnapshot(
                node_key="brand:acme-labs",
                node_type=GraphNodeType.BRAND,
                display_name="Acme Labs",
                source_module="public_footprint",
                source_entity_type="brand",
                source_record_key="brand-acme-labs",
                observed_at=NOW,
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
        yield client, session, (first_id, second_id)
    session.close()


def test_graph_api_requires_control_plane_authentication(
    graph_client: tuple[TestClient, Session, tuple[UUID, UUID]],
) -> None:
    client, _, _ = graph_client

    response = client.get("/v1/graph/nodes")

    assert response.status_code == 401


def test_refresh_is_local_and_homonyms_remain_review_candidates(
    graph_client: tuple[TestClient, Session, tuple[UUID, UUID]],
) -> None:
    client, _, _ = graph_client

    refreshed = client.post("/v1/graph/refresh", headers=HEADERS)
    candidates = client.get(
        "/v1/graph/resolution-candidates",
        headers=HEADERS,
        params={"requires_review": "true"},
    )

    assert refreshed.status_code == 200
    assert refreshed.json()["candidate_count"] >= 2
    assert candidates.status_code == 200
    payload = candidates.json()
    acme_candidates = [
        item for item in payload["items"] if item["node_key"] == "brand:acme-labs"
    ]
    assert len(acme_candidates) == 2
    assert all(item["method"] == "probabilistic_context" for item in acme_candidates)
    assert all(item["requires_review"] for item in acme_candidates)


def test_graph_detail_supports_historical_as_of_query(
    graph_client: tuple[TestClient, Session, tuple[UUID, UUID]],
) -> None:
    client, _, _ = graph_client
    client.post("/v1/graph/refresh", headers=HEADERS)

    current = client.get("/v1/graph/nodes/brand:acme-labs", headers=HEADERS)
    historical = client.get(
        "/v1/graph/nodes/brand:acme-labs",
        headers=HEADERS,
        params={"as_of": (NOW + timedelta(minutes=1)).isoformat()},
    )

    assert current.status_code == 200
    assert historical.status_code == 200
    assert historical.json()["as_of"] is not None
    assert "never upgraded" in historical.json()["evidence_disclaimer"]


def test_resolution_merge_checks_target_fingerprint_and_can_be_split(
    graph_client: tuple[TestClient, Session, tuple[UUID, UUID]],
) -> None:
    client, session, organization_ids = graph_client
    client.post("/v1/graph/refresh", headers=HEADERS)
    page = client.get(
        "/v1/graph/resolution-candidates",
        headers=HEADERS,
        params={"requires_review": "true"},
    ).json()
    candidates = [
        item for item in page["items"] if item["node_key"] == "brand:acme-labs"
    ]
    first = next(
        item
        for item in candidates
        if item["candidate_organization_id"] == str(organization_ids[0])
    )
    second = next(
        item
        for item in candidates
        if item["candidate_organization_id"] == str(organization_ids[1])
    )
    detail = client.get(
        f"/v1/graph/resolution-candidates/{first['id']}", headers=HEADERS
    ).json()

    wrong_target = client.post(
        f"/v1/graph/resolution-candidates/{first['id']}/decisions",
        headers=HEADERS,
        json={
            "decision_type": "merge",
            "actor": "analyst@example.test",
            "reason": "intentional target mismatch test",
            "organization_id": second["candidate_organization_id"],
            "blast_radius_fingerprint": detail["blast_radius"]["fingerprint"],
        },
    )
    assert wrong_target.status_code == 409

    merged = client.post(
        f"/v1/graph/resolution-candidates/{first['id']}/decisions",
        headers=HEADERS,
        json={
            "decision_type": "merge",
            "actor": "analyst@example.test",
            "reason": "reviewed external identifier evidence",
            "organization_id": first["candidate_organization_id"],
            "blast_radius_fingerprint": detail["blast_radius"]["fingerprint"],
        },
    )
    assert merged.status_code == 200
    merged_payload = merged.json()
    assert merged_payload["candidate"]["state"] == "confirmed"
    merge_decision = merged_payload["decisions"][-1]

    refreshed_detail = client.get(
        f"/v1/graph/resolution-candidates/{first['id']}", headers=HEADERS
    ).json()
    split = client.post(
        f"/v1/graph/resolution-candidates/{first['id']}/decisions",
        headers=HEADERS,
        json={
            "decision_type": "split",
            "actor": "analyst@example.test",
            "reason": "later evidence disproved the merge",
            "reverses_decision_id": merge_decision["id"],
            "blast_radius_fingerprint": refreshed_detail["blast_radius"]["fingerprint"],
        },
    )

    assert split.status_code == 200
    binding = session.scalar(
        select(EntityResolutionBindingRecord).where(
            EntityResolutionBindingRecord.node_key == "brand:acme-labs"
        )
    )
    assert binding is not None
    assert binding.current is False
    assert len(split.json()["decisions"]) == 2


def _organization(organization_id: UUID, name: str, website_url: str) -> OrganizationRecord:
    return OrganizationRecord(
        id=organization_id,
        canonical_name=name,
        legal_name=name,
        country_code="FR",
        website_url=website_url,
        registration_ids=[],
        created_at=NOW,
        updated_at=NOW,
    )
