from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from cip.modules.organizations.infrastructure.models import OrganizationRecord
from cip.modules.public_footprint.domain import (
    ClaimEvidenceBasis,
    ClaimResolutionStatus,
    DiscoveryMethod,
    PublicClaim,
    PublicClaimType,
    PublicFootprintProjection,
    PublicResource,
    PublicResourceKind,
    PublicResourceVersion,
    ResourceRetrievalState,
)
from cip.modules.public_footprint.infrastructure.models import (
    PublicClaimRecord,
    PublicResourceRecord,
    PublicResourceVersionRecord,
)
from cip.modules.public_footprint.infrastructure.projections import (
    persist_public_footprint_projections,
)
from cip.shared.persistence.metadata import get_metadata

NOW = datetime(2026, 8, 5, 21, 0, tzinfo=UTC)
ORGANIZATION_ID = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
HASH_A = "a" * 64
HASH_B = "b" * 64


def test_replay_does_not_duplicate_resource_version_or_claim() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    get_metadata().create_all(engine)
    with Session(engine) as session:
        _add_organization(session)
        first = _projection(content_hash=HASH_A)
        replay = _projection(content_hash=HASH_A)

        persist_public_footprint_projections(session, (first,), now=NOW)
        persist_public_footprint_projections(session, (replay,), now=NOW)
        session.flush()

        assert _count(session, PublicResourceRecord) == 1
        assert _count(session, PublicResourceVersionRecord) == 1
        assert _count(session, PublicClaimRecord) == 1
        persisted_version = session.scalar(select(PublicResourceVersionRecord))
        persisted_claim = session.scalar(select(PublicClaimRecord))
        assert persisted_version is not None
        assert persisted_claim is not None
        assert persisted_claim.resource_version_id == persisted_version.id


def test_new_version_and_claim_state_cannot_be_rolled_back_by_older_projection() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    get_metadata().create_all(engine)
    with Session(engine) as session:
        _add_organization(session)
        current = _projection(
            content_hash=HASH_B,
            fetched_at=NOW + timedelta(days=2),
            retrieval_state=ResourceRetrievalState.CHANGED,
            resolution_status=ClaimResolutionStatus.CONFIRMED,
            confidence=0.95,
        )
        older = _projection(
            content_hash=HASH_A,
            fetched_at=NOW + timedelta(days=1),
            retrieval_state=ResourceRetrievalState.FETCHED,
            resolution_status=ClaimResolutionStatus.CANDIDATE,
            confidence=0.6,
        )

        persist_public_footprint_projections(session, (current, older), now=NOW)
        session.flush()

        resource = session.scalar(select(PublicResourceRecord))
        claim = session.scalar(select(PublicClaimRecord))
        current_version = session.scalar(
            select(PublicResourceVersionRecord).where(
                PublicResourceVersionRecord.content_hash_sha256 == HASH_B
            )
        )
        assert resource is not None
        assert claim is not None
        assert current_version is not None
        assert _count(session, PublicResourceVersionRecord) == 2
        assert resource.retrieval_state == ResourceRetrievalState.CHANGED.value
        assert resource.last_seen_at == NOW + timedelta(days=2)
        assert claim.resolution_status == ClaimResolutionStatus.CONFIRMED.value
        assert claim.confidence == 0.95
        assert claim.resource_version_id == current_version.id


def test_changed_version_requires_existing_predecessor_from_same_resource() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    get_metadata().create_all(engine)
    with Session(engine) as session:
        _add_organization(session)
        first = _projection(content_hash=HASH_A)
        persist_public_footprint_projections(session, (first,), now=NOW)

        changed = _projection(
            content_hash=HASH_B,
            fetched_at=NOW + timedelta(hours=1),
            retrieval_state=ResourceRetrievalState.CHANGED,
            supersedes_version_id=first.version.id,
        )
        persist_public_footprint_projections(session, (changed,), now=NOW)
        session.flush()

        changed_record = session.scalar(
            select(PublicResourceVersionRecord).where(
                PublicResourceVersionRecord.content_hash_sha256 == HASH_B
            )
        )
        assert changed_record is not None
        assert changed_record.supersedes_version_id == first.version.id

        invalid = _projection(
            content_hash="c" * 64,
            fetched_at=NOW + timedelta(hours=2),
            supersedes_version_id=uuid4(),
        )
        with pytest.raises(ValueError, match="does not exist"):
            persist_public_footprint_projections(session, (invalid,), now=NOW)


def _projection(
    *,
    content_hash: str,
    fetched_at: datetime = NOW,
    retrieval_state: ResourceRetrievalState = ResourceRetrievalState.FETCHED,
    resolution_status: ClaimResolutionStatus = ClaimResolutionStatus.CANDIDATE,
    confidence: float = 0.8,
    supersedes_version_id=None,
) -> PublicFootprintProjection:
    resource = PublicResource(
        organization_id=ORGANIZATION_ID,
        source_id="corporate-site",
        source_record_key="security-report",
        canonical_url="https://example.test/security/report",
        source_url="https://example.test/sitemap.xml",
        kind=PublicResourceKind.WEB_PAGE,
        discovery_method=DiscoveryMethod.SITEMAP,
        first_discovered_at=NOW,
        last_seen_at=fetched_at,
        retrieval_state=retrieval_state,
        title="Security report",
    )
    version = PublicResourceVersion(
        resource_key=resource.identity_key,
        source_url=resource.canonical_url,
        content_hash_sha256=content_hash,
        fetched_at=fetched_at,
        mime_type="text/html",
        byte_size=1_200,
        title="Security report",
        extracted_text_hash_sha256="d" * 64,
        excerpt="The organization uses a managed SOC provider.",
        source_locator="main article",
        supersedes_version_id=supersedes_version_id,
    )
    claim = PublicClaim(
        organization_id=ORGANIZATION_ID,
        resource_version_id=version.id,
        claim_type=PublicClaimType.PROVIDER_PARTNER_CUSTOMER,
        statement="The organization uses a managed SOC provider.",
        evidence_basis=ClaimEvidenceBasis.TARGET_CONTENT,
        resolution_status=resolution_status,
        confidence=confidence,
        corroboration_group_key=resource.corroboration_group_key,
        source_locator="main article",
        excerpt="managed SOC provider",
    )
    return PublicFootprintProjection(resource=resource, version=version, claims=(claim,))


def _add_organization(session: Session) -> None:
    session.add(
        OrganizationRecord(
            id=ORGANIZATION_ID,
            canonical_name="Public Footprint Example",
            legal_name="Public Footprint Example SAS",
            country_code="FR",
            website_url="https://example.test",
            registration_ids=[],
            created_at=NOW,
            updated_at=NOW,
        )
    )
    session.flush()


def _count(session: Session, record_type: type[object]) -> int:
    return int(session.scalar(select(func.count()).select_from(record_type)) or 0)
