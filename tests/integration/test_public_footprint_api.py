from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from cip.main import create_app
from cip.modules.organizations.infrastructure.models import OrganizationRecord
from cip.modules.public_footprint.infrastructure.models import (
    PublicClaimRecord,
    PublicResourceRecord,
    PublicResourceVersionRecord,
)
from cip.shared.config.settings import Settings, get_settings
from cip.shared.persistence.dependencies import get_database_session
from cip.shared.persistence.metadata import get_metadata

CONTROL_TOKEN = "test-control-token-123"
HEADERS = {"X-CIP-Control-Token": CONTROL_TOKEN}
NOW = datetime(2026, 8, 6, 8, 0, tzinfo=UTC)
ORGANIZATION_ID = UUID("00000000-0000-0000-0000-000000001201")
RESOURCE_ID = UUID("00000000-0000-0000-0000-000000001202")
OLD_VERSION_ID = UUID("00000000-0000-0000-0000-000000001203")
NEW_VERSION_ID = UUID("00000000-0000-0000-0000-000000001204")
CLAIM_ID = UUID("00000000-0000-0000-0000-000000001205")


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
    _seed_public_footprint(database)
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


def test_public_footprint_api_requires_control_plane_authentication(
    client: TestClient,
) -> None:
    response = client.get("/v1/public-footprint/resources")

    assert response.status_code == 401


def test_public_footprint_list_filters_search_and_detail(
    client: TestClient,
) -> None:
    listed = client.get(
        "/v1/public-footprint/resources",
        headers=HEADERS,
        params={
            "organization_id": str(ORGANIZATION_ID),
            "kind": "web_page",
            "retrieval_state": "changed",
            "claim_type": "technology_or_architecture",
            "q": "zero trust",
        },
    )

    assert listed.status_code == 200
    payload = listed.json()
    assert payload["total"] == 1
    item = payload["items"][0]
    assert item["id"] == str(RESOURCE_ID)
    assert item["organization_name"] == "Example Security"
    assert item["latest_version_id"] == str(NEW_VERSION_ID)
    assert item["version_count"] == 2
    assert item["claim_count"] == 1
    assert item["latest_excerpt"] == "Zero trust architecture on Azure."

    detail_response = client.get(
        f"/v1/public-footprint/resources/{RESOURCE_ID}",
        headers=HEADERS,
    )
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert [version["id"] for version in detail["versions"]] == [
        str(NEW_VERSION_ID),
        str(OLD_VERSION_ID),
    ]
    assert detail["versions"][0]["supersedes_version_id"] == str(OLD_VERSION_ID)
    assert detail["claims"][0]["resolution_status"] == "confirmed"
    assert detail["claims"][0]["evidence_basis"] == "target_content"


def test_public_footprint_api_rejects_blank_source_and_missing_resource(
    client: TestClient,
) -> None:
    invalid = client.get(
        "/v1/public-footprint/resources",
        headers=HEADERS,
        params={"source_id": "   "},
    )
    missing = client.get(
        "/v1/public-footprint/resources/00000000-0000-0000-0000-000000001299",
        headers=HEADERS,
    )

    assert invalid.status_code == 422
    assert missing.status_code == 404


def _seed_public_footprint(session: Session) -> None:
    session.add(
        OrganizationRecord(
            id=ORGANIZATION_ID,
            canonical_name="Example Security",
            legal_name="Example Security SAS",
            country_code="FR",
            website_url="https://example.com",
            registration_ids=["SIREN:123456789"],
            created_at=NOW,
            updated_at=NOW,
        )
    )
    session.add(
        PublicResourceRecord(
            id=RESOURCE_ID,
            organization_id=ORGANIZATION_ID,
            source_id="public-web-example",
            source_record_key="https://example.com/security",
            identity_key="a" * 64,
            corroboration_group_key="b" * 64,
            canonical_url="https://example.com/security",
            source_url="https://example.com/security",
            kind="web_page",
            discovery_method="sitemap",
            access_state="public",
            retrieval_state="changed",
            title="Security architecture",
            first_discovered_at=NOW - timedelta(days=2),
            last_seen_at=NOW,
            created_at=NOW - timedelta(days=2),
            updated_at=NOW,
        )
    )
    session.add_all((_old_version(), _new_version()))
    session.add(
        PublicClaimRecord(
            id=CLAIM_ID,
            claim_key="f" * 64,
            organization_id=ORGANIZATION_ID,
            resource_version_id=NEW_VERSION_ID,
            claim_type="technology_or_architecture",
            statement="The organization uses a zero trust architecture on Azure.",
            evidence_basis="target_content",
            resolution_status="confirmed",
            confidence=0.95,
            corroboration_group_key="b" * 64,
            source_locator="body",
            excerpt="Zero trust architecture on Azure.",
            created_at=NOW,
            updated_at=NOW,
        )
    )
    session.commit()


def _old_version() -> PublicResourceVersionRecord:
    return PublicResourceVersionRecord(
        id=OLD_VERSION_ID,
        resource_id=RESOURCE_ID,
        version_key="c" * 64,
        source_url="https://example.com/security",
        content_hash_sha256="d" * 64,
        fetched_at=NOW - timedelta(days=2),
        published_at=None,
        source_updated_at=None,
        mime_type="text/html",
        byte_size=120,
        title="Security architecture",
        language="en",
        extracted_text_hash_sha256="e" * 64,
        excerpt="Security architecture overview.",
        source_locator="body",
        supersedes_version_id=None,
        created_at=NOW - timedelta(days=2),
    )


def _new_version() -> PublicResourceVersionRecord:
    return PublicResourceVersionRecord(
        id=NEW_VERSION_ID,
        resource_id=RESOURCE_ID,
        version_key="1" * 64,
        source_url="https://example.com/security",
        content_hash_sha256="2" * 64,
        fetched_at=NOW,
        published_at=None,
        source_updated_at=NOW - timedelta(hours=1),
        mime_type="text/html",
        byte_size=180,
        title="Security architecture",
        language="en",
        extracted_text_hash_sha256="3" * 64,
        excerpt="Zero trust architecture on Azure.",
        source_locator="body",
        supersedes_version_id=OLD_VERSION_ID,
        created_at=NOW,
    )
