from __future__ import annotations

from datetime import UTC, datetime, timedelta
from hashlib import sha256
from uuid import UUID

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from cip.modules.organizations.infrastructure.models import OrganizationRecord
from cip.modules.public_footprint.domain import (
    DiscoveryMethod,
    PublicFootprintProjection,
    PublicResource,
    PublicResourceKind,
    PublicResourceVersion,
    PublicSurfaceKind,
    PublicSurfaceReference,
    ResourceRetrievalState,
)
from cip.modules.public_footprint.infrastructure.models import (
    PublicResourceVersionRecord,
    PublicSurfaceReferenceRecord,
)
from cip.modules.public_footprint.infrastructure.projections import (
    persist_public_footprint_projections,
)
from cip.modules.public_footprint.infrastructure.surface_persistence import (
    persist_surface_references,
)
from cip.shared.persistence.metadata import get_metadata

NOW = datetime(2026, 8, 14, 12, 0, tzinfo=UTC)
ORGANIZATION_ID = UUID("abababab-abab-abab-abab-abababababab")


def test_replay_reuses_persisted_version_and_does_not_duplicate_surface() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    get_metadata().create_all(engine)
    with Session(engine) as session:
        _add_organization(session)
        first = _projection(content_hash=sha256(b"same").hexdigest())
        replay = _projection(content_hash=sha256(b"same").hexdigest())
        assert first.version.id != replay.version.id

        persist_public_footprint_projections(session, (first,), now=NOW)
        persist_public_footprint_projections(session, (replay,), now=NOW)
        session.flush()

        assert _count(session, PublicResourceVersionRecord) == 1
        assert _count(session, PublicSurfaceReferenceRecord) == 1
        persisted_version = session.scalar(select(PublicResourceVersionRecord))
        persisted_surface = session.scalar(select(PublicSurfaceReferenceRecord))
        assert persisted_version is not None
        assert persisted_surface is not None
        assert persisted_surface.resource_version_id == persisted_version.id


def test_same_surface_on_changed_version_preserves_history() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    get_metadata().create_all(engine)
    with Session(engine) as session:
        _add_organization(session)
        first = _projection(content_hash=sha256(b"first").hexdigest())
        second = _projection(
            content_hash=sha256(b"second").hexdigest(),
            fetched_at=NOW + timedelta(minutes=5),
            retrieval_state=ResourceRetrievalState.CHANGED,
            supersedes_version_id=first.version.id,
        )

        persist_public_footprint_projections(session, (first, second), now=NOW)
        session.flush()

        assert _count(session, PublicResourceVersionRecord) == 2
        assert _count(session, PublicSurfaceReferenceRecord) == 2
        version_ids = set(session.scalars(select(PublicSurfaceReferenceRecord.resource_version_id)))
        assert version_ids == {first.version.id, second.version.id}


def test_surface_identity_collision_fails_closed() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    get_metadata().create_all(engine)
    with Session(engine) as session:
        _add_organization(session)
        projection = _projection(content_hash=sha256(b"collision").hexdigest())
        bare_projection = PublicFootprintProjection(
            resource=projection.resource,
            version=projection.version,
        )
        persist_public_footprint_projections(session, (bare_projection,), now=NOW)
        persisted_version = session.scalar(select(PublicResourceVersionRecord))
        assert persisted_version is not None
        surface = projection.surfaces[0]
        surface_key = surface.identity_key_for_version(persisted_version.id)
        session.add(
            PublicSurfaceReferenceRecord(
                id=surface.id,
                surface_key=surface_key,
                organization_id=surface.organization_id,
                resource_version_id=persisted_version.id,
                kind=surface.kind.value,
                source_locator=surface.source_locator,
                target_url="https://example.test/other.js",
                relation=None,
                http_method=None,
                media_type=None,
                name=None,
                value=None,
                created_at=NOW,
            )
        )
        session.flush()

        with pytest.raises(ValueError, match="identity collision"):
            persist_surface_references(
                session,
                projection.surfaces,
                resource_version_id=persisted_version.id,
                now=NOW,
            )


def _projection(
    *,
    content_hash: str,
    fetched_at: datetime = NOW,
    retrieval_state: ResourceRetrievalState = ResourceRetrievalState.FETCHED,
    supersedes_version_id=None,
) -> PublicFootprintProjection:
    resource = PublicResource(
        organization_id=ORGANIZATION_ID,
        source_id="corporate-site",
        source_record_key="https://example.test/",
        canonical_url="https://example.test/",
        source_url="https://example.test/",
        kind=PublicResourceKind.WEB_PAGE,
        discovery_method=DiscoveryMethod.DIRECT,
        first_discovered_at=NOW,
        last_seen_at=fetched_at,
        retrieval_state=retrieval_state,
    )
    version = PublicResourceVersion(
        resource_key=resource.identity_key,
        source_url=resource.canonical_url,
        content_hash_sha256=content_hash,
        fetched_at=fetched_at,
        mime_type="text/html",
        byte_size=128,
        supersedes_version_id=supersedes_version_id,
    )
    surface = PublicSurfaceReference(
        organization_id=ORGANIZATION_ID,
        resource_version_id=version.id,
        kind=PublicSurfaceKind.SCRIPT,
        source_locator="html:script[src]",
        target_url="https://example.test/app.js",
    )
    return PublicFootprintProjection(
        resource=resource,
        version=version,
        surfaces=(surface,),
    )


def _add_organization(session: Session) -> None:
    session.add(
        OrganizationRecord(
            id=ORGANIZATION_ID,
            canonical_name="Surface Example",
            legal_name="Surface Example SAS",
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
