from __future__ import annotations

from datetime import UTC, datetime

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
    engine = create_database_engine(f"sqlite+pysqlite:///{tmp_path / 'automatic-web.db'}")
    get_metadata().create_all(engine)
    factory = create_session_factory(engine)
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
