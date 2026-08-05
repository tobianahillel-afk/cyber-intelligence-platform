from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from cip.main import create_app
from cip.modules.source_governance.domain.models import DataCategory
from cip.modules.source_governance.infrastructure.models import SourceRecord
from cip.shared.config.settings import Settings, get_settings
from cip.shared.persistence.dependencies import get_database_session
from cip.shared.persistence.metadata import get_metadata

CONTROL_TOKEN = "test-control-token-123"
HEADERS = {"X-CIP-Control-Token": CONTROL_TOKEN}
NOW = datetime(2026, 8, 5, tzinfo=UTC)


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
    database.add(_source_record())
    database.commit()
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


def test_list_backfill_priority_pause_resume_cancel_and_disable(
    client: TestClient,
) -> None:
    listed = client.get("/v1/source-portfolio/sources", headers=HEADERS)

    assert listed.status_code == 200
    payload = listed.json()
    assert payload["total"] >= 10
    by_id = {item["source_id"]: item for item in payload["items"]}
    assert by_id["cisa-kev"]["executable"] is True
    assert by_id["osint-framework-import"]["executable"] is False
    assert by_id["cisa-kev"]["health"]["circuit_state"] == "closed"

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

    priority = client.post(
        "/v1/source-portfolio/sources/reference-synthetic/priority-refresh",
        headers=HEADERS,
        json={"actor": "api-test"},
    )
    assert priority.status_code == 200
    assert priority.json()["created"] is True

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

    cancelled = client.post(
        "/v1/source-portfolio/sources/reference-synthetic/backfills/cancel",
        headers=HEADERS,
        json={"actor": "api-test"},
    )
    assert cancelled.status_code == 200
    assert cancelled.json()["health"]["current_backfill_state"] == "cancelled"

    disabled = client.post(
        "/v1/source-portfolio/sources/reference-synthetic/disable",
        headers=HEADERS,
        json={"actor": "api-test"},
    )
    assert disabled.status_code == 200
    assert disabled.json()["status"] == "disabled"


def _source_record() -> SourceRecord:
    return SourceRecord(
        id="reference-synthetic",
        name="Synthetic reference adapter",
        base_url="https://example.invalid/source-portfolio-reference",
        status="enabled",
        source_type="api",
        owner="Cyber Intelligence Platform",
        terms_url=None,
        licence=None,
        allowed_data_categories=[DataCategory.PUBLIC_RESULT_METADATA.value],
        prohibited_data_categories=[],
        rate_limit_per_minute=None,
        retention_days=30,
        attribution_required=False,
        raw_content_storage=False,
        human_review_required=False,
        authorization_status="approved",
        authorization_document_reference="TEST-REFERENCE",
        authorization_reviewed_at=NOW,
        authorization_expires_at=NOW + timedelta(days=365),
        approved_hosts=["example.invalid"],
        approved_path_prefixes=["/source-portfolio-reference"],
        approved_purposes=["runtime-contract-validation"],
        automated_collection_allowed=True,
        raw_storage_allowed=False,
    )
