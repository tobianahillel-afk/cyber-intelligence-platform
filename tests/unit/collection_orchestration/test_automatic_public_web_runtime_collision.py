from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from cip.modules.collection_orchestration.application import automatic_public_web_runtime
from cip.modules.collection_orchestration.application.automatic_public_web_runtime import (
    AutomaticPublicWebRuntimeConfig,
    build_automatic_public_web_runtime,
)
from cip.modules.organizations.infrastructure.models import OrganizationRecord
from cip.shared.persistence.metadata import get_metadata
from cip.shared.persistence.session import (
    create_database_engine,
    create_session_factory,
    session_scope,
)

_NOW = datetime(2026, 8, 13, 18, 0, tzinfo=UTC)


def test_automatic_runtime_rejects_adapter_identity_collision(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    first_id = uuid4()
    second_id = uuid4()
    engine = create_database_engine(f"sqlite+pysqlite:///{tmp_path / 'collision.db'}")
    get_metadata().create_all(engine)
    factory = create_session_factory(engine)
    with session_scope(factory) as session:
        session.add_all(
            [
                _record(first_id, "Collision One", "https://example.com/"),
                _record(second_id, "Collision Two", "https://example.org/"),
            ]
        )

    class DuplicateIdentityAdapter:
        adapter_id = "public-web-sitemap"
        source_id = "duplicate-runtime-target"

        def __init__(self, *args: object, **kwargs: object) -> None:
            pass

    monkeypatch.setattr(
        automatic_public_web_runtime,
        "PublicWebAdapter",
        DuplicateIdentityAdapter,
    )
    config = AutomaticPublicWebRuntimeConfig(
        enabled=True,
        organization_ids=(first_id, second_id),
        authorization_reference="sa16-l08-approved-runtime-targets",
        reviewed_at=_NOW,
    )
    with (
        session_scope(factory) as session,
        pytest.raises(ValueError, match="duplicate automatic public web adapter"),
    ):
        build_automatic_public_web_runtime(
            session,
            config,
            now=_NOW,
            timeout_seconds=5.0,
        )


def _record(organization_id, name: str, website_url: str) -> OrganizationRecord:
    return OrganizationRecord(
        id=organization_id,
        canonical_name=name,
        legal_name=None,
        country_code=None,
        website_url=website_url,
        registration_ids=[],
        created_at=_NOW,
        updated_at=_NOW,
    )
