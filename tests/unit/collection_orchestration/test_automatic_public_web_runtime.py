from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from cip.modules.collection_orchestration.application.automatic_public_web_runtime import (
    AutomaticPublicWebRuntimeConfig,
    build_automatic_public_web_runtime,
)
from cip.shared.persistence.metadata import get_metadata
from cip.shared.persistence.session import (
    create_database_engine,
    create_session_factory,
    session_scope,
)

_NOW = datetime(2026, 8, 13, 18, 0, tzinfo=UTC)


def test_automatic_public_web_runtime_is_disabled_by_default(tmp_path) -> None:
    factory = _factory(tmp_path)
    with session_scope(factory) as session:
        bundle = build_automatic_public_web_runtime(
            session,
            AutomaticPublicWebRuntimeConfig(),
            now=_NOW,
            timeout_seconds=5.0,
        )

    assert bundle.adapters == {}
    assert bundle.schedules == ()
    assert bundle.targets == ()


@pytest.mark.parametrize(
    "config",
    [
        AutomaticPublicWebRuntimeConfig(enabled=True),
        AutomaticPublicWebRuntimeConfig(enabled=True, organization_ids=(uuid4(),)),
        AutomaticPublicWebRuntimeConfig(
            enabled=True,
            organization_ids=(uuid4(),),
            authorization_reference="approved",
        ),
    ],
)
def test_automatic_public_web_runtime_requires_explicit_approval(
    tmp_path,
    config: AutomaticPublicWebRuntimeConfig,
) -> None:
    factory = _factory(tmp_path)
    with session_scope(factory) as session:
        with pytest.raises(ValueError, match="automatic public web requires"):
            build_automatic_public_web_runtime(
                session,
                config,
                now=_NOW,
                timeout_seconds=5.0,
            )


def _factory(tmp_path):
    engine = create_database_engine(f"sqlite+pysqlite:///{tmp_path / 'automatic-web.db'}")
    get_metadata().create_all(engine)
    return create_session_factory(engine)
