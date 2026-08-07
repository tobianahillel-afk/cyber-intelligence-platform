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
from cip.modules.relationship_intelligence.domain.models import (
    RelationshipClaimType,
    RelationshipContext,
    RelationshipEvidenceClass,
    RelationshipEvidenceSnapshot,
    RelationshipOrganizationLinkStatus,
    RelationshipRole,
    RelationshipSourceKind,
)
from cip.modules.relationship_intelligence.infrastructure.models import (
    BusinessRelationshipRecord,
    RelationshipContextRecord,
    RelationshipEvidenceSnapshotRecord,
)
from cip.modules.relationship_intelligence.infrastructure.projections import (
    persist_relationship_contexts,
    persist_relationship_evidence,
)
from cip.shared.config.settings import Settings, get_settings
from cip.shared.persistence.dependencies import get_database_session
from cip.shared.persistence.metadata import get_metadata

CONTROL_TOKEN = "test-control-token-123"
HEADERS = {"X-CIP-Control-Token": CONTROL_TOKEN}
NOW = datetime(2026, 8, 7, 19, 0, tzinfo=UTC)
RELATIONSHIP_KEY = "provider-a:customer-b:provider"


@pytest.fixture
def relationship_client() -> Iterator[tuple[TestClient, Session, UUID]]:
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    get_metadata().create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)
    session = factory()
    provider_id = uuid4()
    customer_id = uuid4()
    session.add_all(
        (
            _organization(provider_id, "Provider A"),
            _organization(customer_id, "Customer B"),
        )
    )
    relationship_id = persist_relationship_evidence(
        session,
        (_contract_evidence(provider_id, customer_id),),
        now=NOW,
    )[0]
    persist_relationship_contexts(
        session,
        relationship_id,
        (
            RelationshipContext(
                relationship_key=RELATIONSHIP_KEY,
                context_type="service",
                value="soc_mdr",
                reference="https://procurement.example.org/contract-42",
                confidence=0.9,
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
        yield client, session, relationship_id
    session.close()


def test_relationship_api_requires_control_plane_authentication(
    relationship_client: tuple[TestClient, Session, UUID],
) -> None:
    client, _, _ = relationship_client

    response = client.get("/v1/relationships")

    assert response.status_code == 401


def test_list_and_detail_keep_context_separate_from_evidence(
    relationship_client: tuple[TestClient, Session, UUID],
) -> None:
    client, _, _ = relationship_client

    listed = client.get(
        "/v1/relationships",
        headers=HEADERS,
        params={
            "status": "active",
            "role": "provider",
            "evidence_class": "contracted",
            "contract_backed_current": "true",
        },
    )

    assert listed.status_code == 200
    payload = listed.json()
    assert payload["total"] == 1
    assert payload["items"][0]["contract_backed_current"] is True
    assert payload["items"][0]["strongest_evidence_class"] == "contracted"

    detailed = client.get(f"/v1/relationships/{RELATIONSHIP_KEY}", headers=HEADERS)

    assert detailed.status_code == 200
    detail = detailed.json()
    assert len(detail["evidence"]) == 1
    assert detail["evidence"][0]["contract_reference"] == "contract-42"
    assert detail["contexts"][0]["context_type"] == "service"
    assert detail["contexts"][0]["value"] == "soc_mdr"
    assert "not contract evidence" in detail["evidence_disclaimer"]


def test_replay_is_idempotent_and_retraction_preserves_history(
    relationship_client: tuple[TestClient, Session, UUID],
) -> None:
    _, session, relationship_id = relationship_client
    provider_id, customer_id = _relationship_organization_ids(session, relationship_id)
    original = _contract_evidence(provider_id, customer_id)
    original_count = session.scalar(select(func.count(RelationshipEvidenceSnapshotRecord.id)))

    persist_relationship_evidence(session, (original,), now=NOW)
    retraction = replace(
        original,
        source_record_key="contract-r2",
        claim_type=RelationshipClaimType.RETRACTION,
        title="Published contract cancellation",
        excerpt="The published contract record was cancelled.",
        modified_at=NOW + timedelta(hours=2),
        supersedes_record_key=original.source_record_key,
    )
    persist_relationship_evidence(session, (retraction,), now=NOW + timedelta(hours=2))
    session.commit()

    relationship = session.get(BusinessRelationshipRecord, relationship_id)
    assert relationship is not None
    assert relationship.status == "retracted"
    assert relationship.contract_backed_current is False
    assert session.scalar(select(func.count(BusinessRelationshipRecord.id))) == 1
    assert session.scalar(
        select(func.count(RelationshipEvidenceSnapshotRecord.id))
    ) == original_count + 1


def test_context_update_does_not_mutate_immutable_evidence(
    relationship_client: tuple[TestClient, Session, UUID],
) -> None:
    _, session, relationship_id = relationship_client
    evidence_count = session.scalar(select(func.count(RelationshipEvidenceSnapshotRecord.id)))

    persist_relationship_contexts(
        session,
        relationship_id,
        (
            RelationshipContext(
                relationship_key=RELATIONSHIP_KEY,
                context_type="service",
                value="soc_mdr",
                reference="https://procurement.example.org/updated",
                confidence=0.95,
            ),
        ),
        now=NOW + timedelta(minutes=5),
    )
    session.commit()

    context = session.scalar(select(RelationshipContextRecord))
    assert context is not None
    assert context.confidence == 0.95
    assert session.scalar(
        select(func.count(RelationshipEvidenceSnapshotRecord.id))
    ) == evidence_count


def test_missing_relationship_returns_not_found(
    relationship_client: tuple[TestClient, Session, UUID],
) -> None:
    client, _, _ = relationship_client

    response = client.get("/v1/relationships/does-not-exist", headers=HEADERS)

    assert response.status_code == 404


def _organization(organization_id: UUID, name: str) -> OrganizationRecord:
    return OrganizationRecord(
        id=organization_id,
        canonical_name=name,
        legal_name=f"{name} SAS",
        country_code="FR",
        website_url=f"https://{name.lower().replace(' ', '-')}.example.org",
        registration_ids=[],
        created_at=NOW,
        updated_at=NOW,
    )


def _contract_evidence(
    provider_id: UUID,
    customer_id: UUID,
) -> RelationshipEvidenceSnapshot:
    return RelationshipEvidenceSnapshot(
        source_id="procurement-contracts",
        source_kind=RelationshipSourceKind.PROCUREMENT,
        source_record_key="contract-r1",
        source_url="https://procurement.example.org/contract-42",
        relationship_key=RELATIONSHIP_KEY,
        claim_type=RelationshipClaimType.ASSERTION,
        role=RelationshipRole.PROVIDER,
        evidence_class=RelationshipEvidenceClass.CONTRACTED,
        title="Provider A awarded security services contract",
        excerpt="Published procurement contract between Provider A and Customer B.",
        claimed_source_organization_name="Provider A",
        claimed_target_organization_name="Customer B",
        source_organization_id=provider_id,
        target_organization_id=customer_id,
        source_link_status=RelationshipOrganizationLinkStatus.EXACT,
        target_link_status=RelationshipOrganizationLinkStatus.EXACT,
        published_at=NOW - timedelta(days=10),
        modified_at=NOW - timedelta(days=9),
        observed_at=NOW - timedelta(days=8),
        valid_from=NOW - timedelta(days=30),
        valid_until=NOW + timedelta(days=335),
        contract_reference="contract-42",
        renewal_at=NOW + timedelta(days=300),
        confidence=0.95,
    )


def _relationship_organization_ids(
    session: Session,
    relationship_id: UUID,
) -> tuple[UUID, UUID]:
    record = session.get(BusinessRelationshipRecord, relationship_id)
    assert record is not None
    assert record.source_organization_id is not None
    assert record.target_organization_id is not None
    return record.source_organization_id, record.target_organization_id
