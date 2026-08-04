from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from cip.main import create_app
from cip.shared.config.settings import Settings, get_settings
from cip.shared.persistence.dependencies import get_database_session
from cip.shared.persistence.metadata import get_metadata

CONTROL_TOKEN = "test-control-token-123"
HEADERS = {"X-CIP-Control-Token": CONTROL_TOKEN}


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
    settings = Settings(
        environment="test",
        database_url="sqlite+pysqlite://",
        source_portfolio_path=Path("policies/source_portfolio.yml"),
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


def test_control_plane_rejects_anonymous_access(client: TestClient) -> None:
    response = client.get("/v1/source-portfolio/sources")

    assert response.status_code == 401


def test_list_backfill_pause_resume_and_disable(client: TestClient) -> None:
    listed = client.get("/v1/source-portfolio/sources", headers=HEADERS)

    assert listed.status_code == 200
    payload = listed.json()
    assert payload["total"] >= 10
    by_id = {item["source_id"]: item for item in payload["items"]}
    assert by_id["cisa-kev"]["executable"] is True
    assert by_id["osint-framework-import"]["executable"] is False

    candidate = client.post(
        "/v1/source-portfolio/sources/osint-framework-import/backfills",
        headers=HEADERS,
        json={
            "actor": "api-test",
            "partitions": [{"lower_bound": "a", "upper_bound": "b"}],
        },
    )
    assert candidate.status_code == 409

    backfill = client.post(
        "/v1/source-portfolio/sources/reference-synthetic/backfills",
        headers=HEADERS,
        json={
            "actor": "api-test",
            "partitions": [
                {"lower_bound": "2026-01-01", "upper_bound": "2026-02-01"}
            ],
        },
    )
    assert backfill.status_code == 200
    assert len(backfill.json()["partition_ids"]) == 1

    paused = client.post(
        "/v1/source-portfolio/sources/reference-synthetic/pause",
        headers=HEADERS,
        json={"actor": "api-test"},
    )
    assert paused.status_code == 200
    assert paused.json()["status"] == "paused"

    resumed = client.post(
        "/v1/source-portfolio/sources/reference-synthetic/resume",
        headers=HEADERS,
        json={"actor": "api-test"},
    )
    assert resumed.status_code == 200
    assert resumed.json()["status"] == "executable"

    disabled = client.post(
        "/v1/source-portfolio/sources/reference-synthetic/disable",
        headers=HEADERS,
        json={"actor": "api-test"},
    )
    assert disabled.status_code == 200
    assert disabled.json()["status"] == "disabled"
