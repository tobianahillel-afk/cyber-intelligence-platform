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
    PublicStructuredState,
    PublicStructuredStateKind,
    ResourceRetrievalState,
)
from cip.modules.public_footprint.infrastructure.models import (
    PublicResourceVersionRecord,
    PublicStructuredStateRecord,
)
from cip.modules.public_footprint.infrastructure.projections import (
    persist_public_footprint_projections,
)
from cip.modules.public_footprint.infrastructure.structured_state_persistence import (
    persist_structured_states,
)
from cip.shared.persistence.metadata import get_metadata

NOW = datetime(2026, 8, 14, 13, 30, tzinfo=UTC)
ORGANIZATION_ID = UUID("cdcdcdcd-cdcd-cdcd-cdcd-cdcdcdcdcdcd")


def test_replay_reuses_persisted_version_and_does_not_duplicate_state() -> None:
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
        assert _count(session, PublicStructuredStateRecord) == 1
        persisted_version = session.scalar(select(PublicResourceVersionRecord))
        persisted_state = session.scalar(select(PublicStructuredStateRecord))
        assert persisted_version is not None
        assert persisted_state is not None
        assert persisted_state.resource_version_id == persisted_version.id
        assert persisted_state.payload_json == '{"vendor":"Splunk"}'


def test_same_state_on_changed_version_preserves_history() -> None:
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
        assert _count(session, PublicStructuredStateRecord) == 2
        version_ids = set(
            session.scalars(select(PublicStructuredStateRecord.resource_version_id))
        )
        assert version_ids == {first.version.id, second.version.id}


def test_structured_state_identity_collision_fails_closed() -> None:
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
        state = projection.structured_states[0]
        state_key = state.identity_key_for_version(persisted_version.id)
        session.add(
            PublicStructuredStateRecord(
                id=state.id,
                state_key=state_key,
                organization_id=state.organization_id,
                resource_version_id=persisted_version.id,
                kind=state.kind.value,
                page_url=state.page_url,
                source_locator=state.source_locator,
                source_url=state.source_url,
                http_status=state.http_status,
                media_type=state.media_type,
                extractor_id=state.extractor_id,
                payload_hash_sha256=state.payload_hash_sha256,
                payload_json='{"vendor":"Different"}',
                created_at=NOW,
            )
        )
        session.flush()

        with pytest.raises(ValueError, match="identity collision"):
            persist_structured_states(
                session,
                projection.structured_states,
                resource_version_id=persisted_version.id,
                now=NOW,
            )


def _projection(
    *,
    content_hash: str,
    fetched_at: datetime = NOW,
    retrieval_state: ResourceRetrievalState = ResourceRetrievalState.FETCHED,
    supersedes_version_id: UUID | None = None,
) -> PublicFootprintProjection:
    resource = PublicResource(
        organization_id=ORGANIZATION_ID,
        source_id="corporate-site",
        source_record_key="https://example.test/app",
        canonical_url="https://example.test/app",
        source_url="https://example.test/app",
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
    state = PublicStructuredState(
        organization_id=ORGANIZATION_ID,
        resource_version_id=version.id,
        kind=PublicStructuredStateKind.NETWORK_JSON,
        page_url=resource.canonical_url,
        source_locator="https://example.test/api/state",
        source_url="https://example.test/api/state",
        http_status=200,
        media_type="application/json",
        payload_json='{"vendor":"Splunk"}',
    )
    return PublicFootprintProjection(
        resource=resource,
        version=version,
        structured_states=(state,),
    )


def _add_organization(session: Session) -> None:
    session.add(
        OrganizationRecord(
            id=ORGANIZATION_ID,
            canonical_name="Structured State Example",
            legal_name="Structured State Example SAS",
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
