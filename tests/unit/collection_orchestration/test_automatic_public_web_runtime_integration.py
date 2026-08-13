from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from sqlalchemy import select

from cip.modules.collection_orchestration.application.runtime import (
    build_collection_runtime,
    run_scheduler_once,
)
from cip.modules.collection_orchestration.infrastructure.models import CollectionJobRecord
from cip.modules.organizations.infrastructure.models import OrganizationRecord
from cip.shared.config.settings import Settings
from cip.shared.persistence.metadata import get_metadata
from cip.shared.persistence.session import (
    create_database_engine,
    create_session_factory,
    session_scope,
)

_NOW = datetime(2026, 8, 13, 18, 0, tzinfo=UTC)
_ORG_ID = UUID("15712d0d-9054-50b4-8a26-e25d9ea1f509")
_TARGET_ID = f"public-web-{_ORG_ID.hex}"


def test_collection_runtime_schedules_approved_automatic_public_web_target(
    tmp_path: Path,
) -> None:
    database_url = f"sqlite+pysqlite:///{tmp_path / 'runtime-auto-web.db'}"
    engine = create_database_engine(database_url)
    get_metadata().create_all(engine)
    factory = create_session_factory(engine)
    with session_scope(factory) as session:
        session.add(
            OrganizationRecord(
                id=_ORG_ID,
                canonical_name="Example Organization",
                legal_name=None,
                country_code=None,
                website_url="https://example.com/",
                registration_ids=[],
                created_at=_NOW,
                updated_at=_NOW,
            )
        )
    settings = Settings(
        _env_file=None,
        database_url=database_url,
        automatic_public_web_enabled=True,
        automatic_public_web_organization_ids=(_ORG_ID,),
        automatic_public_web_authorization_reference="sa16-l08-approved-test-target",
        automatic_public_web_reviewed_at=_NOW,
        automatic_public_web_refresh_interval_seconds=3_600,
        automatic_public_web_max_link_depth=0,
        automatic_public_web_max_pages=1,
    )

    runtime = build_collection_runtime(settings)

    assert (_TARGET_ID, "public-web-sitemap") in runtime.adapters
    assert any(
        schedule.source_id == _TARGET_ID
        and schedule.adapter_id == "public-web-sitemap"
        and schedule.interval_seconds == 3_600
        for schedule in runtime.schedules
    )
    assert run_scheduler_once(runtime, now=_NOW) >= 1
    with session_scope(runtime.factory) as session:
        jobs = tuple(
            session.scalars(
                select(CollectionJobRecord).where(CollectionJobRecord.source_id == _TARGET_ID)
            )
        )
    assert len(jobs) == 1
    assert jobs[0].adapter_id == "public-web-sitemap"
