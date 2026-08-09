from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from cip.modules.organizations.infrastructure.models import OrganizationRecord
from cip.modules.professional_context.api.router import router
from cip.modules.professional_context.domain import (
    ContactChannelType,
    ContactEvidenceScope,
    LawfulBasis,
    OrganizationLinkStatus,
    ProfessionalContactEvidence,
    ProfessionalPersonReference,
    ProfessionalProcessingContext,
    ProfessionalReviewState,
    ProfessionalRoleClaim,
    source_person_key,
)
from cip.modules.professional_context.infrastructure.contact_persistence import (
    persist_professional_contacts,
)
from cip.modules.professional_context.infrastructure.person_persistence import (
    persist_professional_people,
)
from cip.modules.professional_context.infrastructure.role_persistence import (
    persist_professional_roles,
)
from cip.shared.config.settings import Settings, get_settings
from cip.shared.persistence.dependencies import get_database_session
from cip.shared.persistence.metadata import get_metadata

NOW = datetime(2026, 8, 9, 0, 0, tzinfo=UTC)
CONTROL_TOKEN = "lot21-control-token"
HEADERS = {"X-CIP-Control-Token": CONTROL_TOKEN}


@pytest.fixture
def professional_client() -> Iterator[tuple[TestClient, UUID, str]]:
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    get_metadata().create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)
    session = factory()
    organization_id = uuid4()
    session.add(
        OrganizationRecord(
            id=organization_id,
            canonical_name="Example Corp",
            legal_name="Example Corp SAS",
            country_code="FR",
            website_url="https://example.org",
            registration_ids=[],
            created_at=NOW,
            updated_at=NOW,
        )
    )
    session.flush()
    processing = ProfessionalProcessingContext(
        lawful_basis=LawfulBasis.LEGITIMATE_INTERESTS,
        lawful_basis_reference="privacy-review:lot21-api",
        purpose="professional research",
        reviewed_at=NOW - timedelta(days=1),
        retention_until=NOW + timedelta(days=1095),
    )
    source_id = "approved-directory"
    source_record_key = "alice-42"
    person_key = source_person_key(source_id, source_record_key)
    persist_professional_people(
        session,
        (
            ProfessionalPersonReference(
                person_key=person_key,
                display_name="Alice Martin",
                source_id=source_id,
                source_kind="authorized_directory",
                source_record_key=source_record_key,
                source_url="https://directory.example/alice-42",
                observed_at=NOW,
                confidence=0.9,
                processing=processing,
                review_state=ProfessionalReviewState.CONFIRMED,
            ),
        ),
        now=NOW,
    )
    persist_professional_roles(
        session,
        (
            ProfessionalRoleClaim(
                claim_key="role:alice:example-security",
                person_key=person_key,
                source_id="organization-site",
                source_record_key="team-page:alice",
                role_title="Chief Information Security Officer",
                team_name="Security",
                observed_at=NOW,
                confidence=0.9,
                processing=processing,
                organization_id=organization_id,
                claimed_organization_name="Example Corp",
                organization_link_status=OrganizationLinkStatus.EXACT,
                review_state=ProfessionalReviewState.CONFIRMED,
            ),
        ),
        now=NOW,
    )
    persist_professional_contacts(
        session,
        (
            ProfessionalContactEvidence(
                contact_key="contact:example:switchboard",
                channel_type=ContactChannelType.SWITCHBOARD,
                evidence_scope=ContactEvidenceScope.ORGANIZATION_PUBLISHED,
                value="+33 1 23 45 67 89",
                source_id="organization-site",
                source_record_key="contact-page",
                source_url="https://example.org/contact",
                observed_at=NOW,
                confidence=1.0,
                processing=processing,
                organization_id=organization_id,
                review_state=ProfessionalReviewState.CONFIRMED,
            ),
        ),
        now=NOW,
    )
    session.commit()

    application = FastAPI()
    application.include_router(router)
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
        yield client, organization_id, person_key
    session.close()


def test_professional_context_api_requires_control_plane_authentication(
    professional_client: tuple[TestClient, UUID, str],
) -> None:
    client, _, _ = professional_client

    response = client.get("/v1/professional-context/people")

    assert response.status_code == 401


def test_professional_context_reads_persisted_people_and_detail(
    professional_client: tuple[TestClient, UUID, str],
) -> None:
    client, organization_id, person_key = professional_client

    page = client.get(
        "/v1/professional-context/people",
        headers=HEADERS,
        params={"organization_id": str(organization_id)},
    )
    detail = client.get(
        f"/v1/professional-context/people/{person_key}",
        headers=HEADERS,
    )

    assert page.status_code == 200
    assert page.json()["total"] == 1
    assert page.json()["items"][0]["display_name"] == "Alice Martin"
    assert detail.status_code == 200
    assert detail.json()["roles"][0]["role_title"] == "Chief Information Security Officer"
    assert "not outreach authorization" in detail.json()["evidence_disclaimer"]


def test_organization_map_contains_only_explicit_persisted_context(
    professional_client: tuple[TestClient, UUID, str],
) -> None:
    client, organization_id, _ = professional_client

    response = client.get(
        f"/v1/professional-context/organizations/{organization_id}/map",
        headers=HEADERS,
    )

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["people"]) == 1
    assert payload["reporting_lines"] == []
    assert payload["organization_contacts"][0]["channel_type"] == "switchboard"
    assert "not inferred transitively" in payload["privacy_disclaimer"]
