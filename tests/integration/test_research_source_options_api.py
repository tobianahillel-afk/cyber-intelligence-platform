from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from cip.modules.research_orchestration.api.router import router
from cip.modules.source_governance.domain.models import (
    AuthorizationStatus,
    DataCategory,
    SourceAuthorization,
    SourcePolicy,
    SourceStatus,
    SourceType,
)
from cip.modules.source_governance.infrastructure.persistence import sync_source_registry
from cip.modules.source_governance.infrastructure.registry import SourceRegistryEntry
from cip.shared.config.settings import Settings, get_settings
from cip.shared.persistence.dependencies import get_database_session
from cip.shared.persistence.metadata import get_metadata

CONTROL_TOKEN = "research-source-options-token"
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
    _persist_manual_search(database)
    settings = Settings(
        environment="test",
        database_url="sqlite+pysqlite://",
        control_plane_token=CONTROL_TOKEN,
    )
    application = FastAPI()
    application.include_router(router)

    def override_session() -> Iterator[Session]:
        yield database

    def override_settings() -> Settings:
        return settings

    application.dependency_overrides[get_database_session] = override_session
    application.dependency_overrides[get_settings] = override_settings
    with TestClient(application) as test_client:
        yield test_client
    database.close()


def test_source_options_require_control_plane_auth(client: TestClient) -> None:
    response = client.get("/v1/research/source-options")

    assert response.status_code == 401


def test_source_options_rank_persisted_before_manual_search(client: TestClient) -> None:
    response = client.get(
        "/v1/research/source-options?purpose=organization-research"
        "&data_category=organization_metadata",
        headers=HEADERS,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["purpose"] == "organization-research"
    assert body["data_category"] == "organization_metadata"
    assert [item["source_id"] for item in body["items"]] == [
        "persisted-evidence",
        "manual-search",
    ]
    assert body["items"][0]["rank"] == 1
    assert body["items"][0]["mode"] == "persisted_search"
    assert body["items"][0]["estimated_cost"] == 0
    assert body["items"][1]["mode"] == "manual_link"
    assert body["items"][1]["manual_link_allowed"] is True
    assert body["items"][1]["authorized"] is False


def test_source_options_apply_exact_data_category_scope(client: TestClient) -> None:
    response = client.get(
        "/v1/research/source-options?purpose=organization-research"
        "&data_category=public_tender",
        headers=HEADERS,
    )

    assert response.status_code == 200
    assert [item["source_id"] for item in response.json()["items"]] == [
        "persisted-evidence"
    ]


def _persist_manual_search(session: Session) -> None:
    policy = SourcePolicy(
        id="manual-search",
        name="Governed manual search",
        base_url="https://search.example.test",
        status=SourceStatus.CONDITIONAL,
        source_type=SourceType.SEARCH_PROVIDER,
        owner="Research team",
        allowed_data_categories=frozenset({DataCategory.ORGANIZATION_METADATA}),
        prohibited_data_categories=frozenset({DataCategory.PRIVATE_PERSONAL_DATA}),
        terms_url="https://search.example.test/terms",
        retention_days=90,
        raw_content_storage=False,
        human_review_required=True,
    )
    authorization = SourceAuthorization(
        status=AuthorizationStatus.PENDING_REVIEW,
        document_reference=None,
        approved_hosts=frozenset(),
        approved_path_prefixes=(),
        approved_purposes=frozenset(),
        automated_collection_allowed=False,
        raw_storage_allowed=False,
    )
    sync_source_registry(session, (SourceRegistryEntry(policy, authorization, {}),))
    session.commit()
