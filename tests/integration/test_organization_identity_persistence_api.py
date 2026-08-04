from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from cip.main import create_app
from cip.modules.evidence.domain.entities import Evidence
from cip.modules.organizations.application.identity import IdentityProjection
from cip.modules.organizations.domain.entities import Organization
from cip.modules.organizations.domain.identifiers import IdentifierScheme, OfficialIdentifier
from cip.modules.organizations.domain.identity import (
    IdentityKind,
    IdentityMergeCandidate,
    IdentityStatus,
    MatchMethod,
    MatchState,
    OrganizationIdentity,
)
from cip.modules.organizations.infrastructure.identity_claims import (
    persist_identity_claims,
)
from cip.modules.organizations.infrastructure.identity_models import (
    OrganizationIdentityClaimRecord,
    OrganizationIdentityRecord,
)
from cip.modules.organizations.infrastructure.identity_persistence import (
    IdentityPersistenceConflictError,
    persist_identity_projections,
    review_merge_candidate,
)
from cip.modules.organizations.infrastructure.identity_queries import (
    get_organization_identity,
    list_merge_candidates,
    list_organization_identities,
)
from cip.shared.persistence.dependencies import get_database_session
from cip.shared.persistence.metadata import get_metadata

NOW = datetime(2026, 8, 4, 16, 0, tzinfo=UTC)
RETENTION = NOW + timedelta(days=1825)
ORGANIZATION_ID = UUID("86fe6126-5731-5c4d-a206-69a6a736cae5")


@pytest.fixture
def session_and_client() -> Iterator[tuple[Session, TestClient]]:
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    get_metadata().create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)
    session = factory()
    application = create_app()

    def override_session() -> Iterator[Session]:
        yield session

    application.dependency_overrides[get_database_session] = override_session
    with TestClient(application) as client:
        yield session, client
    session.close()


def test_persistence_queries_and_api_expose_identity_lineage(
    session_and_client: tuple[Session, TestClient],
) -> None:
    session, client = session_and_client
    projection = _projection(
        source_id="recherche-entreprises",
        official_name="EXAMPLE FRANCE SAS",
        status=IdentityStatus.ACTIVE,
        auto_confirm=True,
    )

    persist_identity_projections(session, (projection,), now=NOW)
    persist_identity_claims(session, (projection,))
    session.commit()

    identities = list_organization_identities(session, ORGANIZATION_ID)
    assert len(identities) == 1
    identity = identities[0]
    assert identity.identifiers[0].value == "732829320"
    assert identity.claims[0].source_id == "recherche-entreprises"
    assert identity.conflict_fields == ()
    assert get_organization_identity(session, identity.id).official_name == "EXAMPLE FRANCE SAS"

    response = client.get(f"/v1/organizations/{ORGANIZATION_ID}/identities")
    assert response.status_code == 200
    payload = response.json()[0]
    assert payload["organization_id"] == str(ORGANIZATION_ID)
    assert payload["identifiers"][0]["scheme"] == "siren"
    assert payload["claims"][0]["source_id"] == "recherche-entreprises"
    assert payload["conflict_fields"] == []

    detail = client.get(f"/v1/organizations/identities/{identity.id}")
    assert detail.status_code == 200
    assert detail.json()["official_name"] == "EXAMPLE FRANCE SAS"


def test_claim_reconciliation_preserves_conflicts_and_source_precedence(
    session_and_client: tuple[Session, TestClient],
) -> None:
    session, client = session_and_client
    french = _projection(
        source_id="recherche-entreprises",
        official_name="EXAMPLE FRANCE SAS",
        status=IdentityStatus.ACTIVE,
        auto_confirm=True,
    )
    gleif = _projection(
        source_id="gleif",
        official_name="EXAMPLE FRANCE HOLDING",
        status=IdentityStatus.CEASED,
        auto_confirm=True,
    )

    for projection in (french, gleif):
        persist_identity_projections(session, (projection,), now=NOW)
        persist_identity_claims(session, (projection,))
    session.commit()

    identity = get_organization_identity(session, french.identity.id)
    assert identity.official_name == "EXAMPLE FRANCE SAS"
    assert identity.status is IdentityStatus.ACTIVE
    assert set(identity.conflict_fields) == {"official_name", "status"}
    assert {claim.source_id for claim in identity.claims} == {
        "recherche-entreprises",
        "gleif",
    }
    response = client.get(f"/v1/organizations/identities/{identity.id}")
    assert set(response.json()["conflict_fields"]) == {"official_name", "status"}

    stored_claims = session.scalars(select(OrganizationIdentityClaimRecord)).all()
    assert all(set(claim.conflict_fields) == {"official_name", "status"} for claim in stored_claims)


def test_name_candidate_requires_explicit_api_review(
    session_and_client: tuple[Session, TestClient],
) -> None:
    session, client = session_and_client
    projection = _projection(
        source_id="recherche-entreprises",
        official_name="EXAMPLE FRANCE SAS",
        status=IdentityStatus.ACTIVE,
        auto_confirm=False,
    )
    persist_identity_projections(session, (projection,), now=NOW)
    persist_identity_claims(session, (projection,))
    session.commit()

    page = list_merge_candidates(
        session,
        states=(MatchState.NEEDS_REVIEW,),
        limit=10,
        offset=0,
    )
    assert page.total == 1
    candidate_id = page.items[0].id
    assert get_organization_identity(session, projection.identity.id).organization_id is None

    api_page = client.get(
        "/v1/organizations/identity-merge-candidates",
        params={"state": "needs_review"},
    )
    assert api_page.status_code == 200
    assert api_page.json()["total"] == 1

    response = client.post(
        f"/v1/organizations/identity-merge-candidates/{candidate_id}/review",
        json={
            "action": "confirm",
            "actor": "identity-analyst",
            "note": "Official name and business address reviewed",
        },
    )
    assert response.status_code == 200
    assert response.json()["state"] == "confirmed"
    reviewed_identity = get_organization_identity(session, projection.identity.id)
    assert reviewed_identity.organization_id == ORGANIZATION_ID

    second = client.post(
        f"/v1/organizations/identity-merge-candidates/{candidate_id}/review",
        json={"action": "reject", "actor": "identity-analyst"},
    )
    assert second.status_code == 422


def test_candidate_rejection_does_not_attach_identity(
    session_and_client: tuple[Session, TestClient],
) -> None:
    session, client = session_and_client
    projection = _projection(
        source_id="recherche-entreprises",
        official_name="EXAMPLE FRANCE SAS",
        status=IdentityStatus.ACTIVE,
        auto_confirm=False,
    )
    persist_identity_projections(session, (projection,), now=NOW)
    session.commit()
    candidate_id = projection.merge_candidates[0].id

    response = client.post(
        f"/v1/organizations/identity-merge-candidates/{candidate_id}/review",
        json={"action": "reject", "actor": "identity-analyst"},
    )

    assert response.status_code == 200
    assert response.json()["state"] == "rejected"
    assert session.get(OrganizationIdentityRecord, projection.identity.id).organization_id is None


def test_review_refuses_conflicting_identifier_attachment(
    session_and_client: tuple[Session, TestClient],
) -> None:
    session, client = session_and_client
    attached = _projection(
        source_id="recherche-entreprises",
        official_name="EXAMPLE FRANCE SAS",
        status=IdentityStatus.ACTIVE,
        auto_confirm=True,
        siren="732829320",
    )
    conflicting = _projection(
        source_id="recherche-entreprises",
        official_name="EXAMPLE FRANCE SAS",
        status=IdentityStatus.ACTIVE,
        auto_confirm=False,
        siren="552100554",
    )
    persist_identity_projections(session, (attached, conflicting), now=NOW)
    session.commit()

    response = client.post(
        (
            "/v1/organizations/identity-merge-candidates/"
            f"{conflicting.merge_candidates[0].id}/review"
        ),
        json={"action": "confirm", "actor": "identity-analyst"},
    )

    assert response.status_code == 409
    assert "conflicting siren" in response.json()["detail"]


def test_exact_identifier_cannot_be_linked_to_two_identities(
    session_and_client: tuple[Session, TestClient],
) -> None:
    session, _ = session_and_client
    first = _projection(
        source_id="recherche-entreprises",
        official_name="FIRST",
        status=IdentityStatus.ACTIVE,
        auto_confirm=True,
    )
    persist_identity_projections(session, (first,), now=NOW)
    session.flush()
    second = _projection(
        source_id="gleif",
        official_name="SECOND",
        status=IdentityStatus.ACTIVE,
        auto_confirm=True,
        identity_id=uuid4(),
    )

    with pytest.raises(IdentityPersistenceConflictError, match="already linked"):
        persist_identity_projections(session, (second,), now=NOW)


def test_direct_review_function_validates_not_found_actor_and_conflict(
    session_and_client: tuple[Session, TestClient],
) -> None:
    session, _ = session_and_client
    with pytest.raises(LookupError):
        review_merge_candidate(
            session,
            uuid4(),
            confirm=True,
            actor="analyst",
            reviewed_at=NOW,
        )

    projection = _projection(
        source_id="recherche-entreprises",
        official_name="EXAMPLE FRANCE SAS",
        status=IdentityStatus.ACTIVE,
        auto_confirm=False,
    )
    persist_identity_projections(session, (projection,), now=NOW)
    session.flush()
    with pytest.raises(ValueError, match="actor"):
        review_merge_candidate(
            session,
            projection.merge_candidates[0].id,
            confirm=True,
            actor=" ",
            reviewed_at=NOW,
        )

    session.delete(session.get(OrganizationIdentityRecord, projection.identity.id))
    session.flush()
    with pytest.raises(LookupError, match="identity"):
        review_merge_candidate(
            session,
            projection.merge_candidates[0].id,
            confirm=True,
            actor="analyst",
            reviewed_at=NOW,
        )


def test_api_not_found_and_validation_contracts(
    session_and_client: tuple[Session, TestClient],
) -> None:
    _, client = session_and_client
    missing = uuid4()

    assert client.get(f"/v1/organizations/{missing}/identities").status_code == 404
    assert client.get(f"/v1/organizations/identities/{missing}").status_code == 404
    assert (
        client.get(f"/v1/organizations/identity-merge-candidates/{missing}").status_code
        == 404
    )
    assert (
        client.post(
            f"/v1/organizations/identity-merge-candidates/{missing}/review",
            json={"action": "confirm", "actor": "analyst"},
        ).status_code
        == 404
    )
    assert (
        client.get(
            "/v1/organizations/identity-merge-candidates",
            params={"limit": 0},
        ).status_code
        == 422
    )


def _projection(
    *,
    source_id: str,
    official_name: str,
    status: IdentityStatus,
    auto_confirm: bool,
    siren: str = "732829320",
    identity_id: UUID | None = None,
) -> IdentityProjection:
    identifier = OfficialIdentifier(
        IdentifierScheme.SIREN,
        siren,
        source_id,
        NOW,
        "FR",
    )
    key = identifier.exact_key
    identity = OrganizationIdentity(
        id=identity_id or OrganizationIdentity.deterministic_id(key),
        kind=IdentityKind.LEGAL_UNIT,
        official_name=official_name,
        country_code="FR",
        source_id=source_id,
        source_record_key=f"legal-unit:{siren}",
        source_url=f"https://source.example/{source_id}/{siren}",
        confidence=0.9,
        observed_at=NOW,
        status=status,
        identifiers=(identifier,),
        aliases=("Example",),
        postal_code="75001",
        city="Paris",
    )
    organization = Organization(
        id=ORGANIZATION_ID,
        canonical_name="Example France SAS",
        legal_name="Example France SAS",
        country_code="FR",
        registration_ids=("SIREN:732829320",) if auto_confirm else (),
        created_at=NOW,
        updated_at=NOW,
    )
    candidate = IdentityMergeCandidate(
        id=uuid5(
            NAMESPACE_URL,
            f"identity-merge-candidate:{identity.id}:{organization.id}",
        ),
        identity_id=identity.id,
        organization_id=organization.id,
        method=(
            MatchMethod.EXACT_IDENTIFIER
            if auto_confirm
            else MatchMethod.EXACT_NAME_AND_POSTCODE
        ),
        score=1.0 if auto_confirm else 0.92,
        reasons=("Synthetic exact match",),
        state=MatchState.AUTO_CONFIRMED if auto_confirm else MatchState.NEEDS_REVIEW,
        created_at=NOW,
    )
    evidence = Evidence(
        id=uuid5(NAMESPACE_URL, f"evidence:{source_id}:{siren}"),
        source_id=source_id,
        source_record_key=f"legal-unit:{siren}",
        source_url=f"https://source.example/{source_id}/{siren}",
        summary=f"Synthetic official company identity from {source_id}",
        confidence=0.9,
        collected_at=NOW,
        observed_at=NOW,
        content_hash_sha256="a" * 64,
        raw_storage_permitted=False,
        retention_until=RETENTION,
    )
    return IdentityProjection(
        identity=identity,
        evidence=evidence,
        attached_organization=organization if auto_confirm else None,
        candidate_organizations=() if auto_confirm else (organization,),
        merge_candidates=(candidate,),
    )
