from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from cip.adapters.sources.public_web.provisioning import AUTOMATIC_PUBLIC_WEB_SOURCE_ID
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
    with (
        session_scope(factory) as session,
        pytest.raises(ValueError, match="automatic public web requires"),
    ):
        build_automatic_public_web_runtime(
            session,
            config,
            now=_NOW,
            timeout_seconds=5.0,
        )


def test_automatic_public_web_runtime_builds_distinct_target_jobs(tmp_path) -> None:
    first_id = UUID("15712d0d-9054-50b4-8a26-e25d9ea1f509")
    second_id = UUID("7a1ab1ff-1bdd-48f1-b5b2-636d361b4784")
    factory = _factory(tmp_path)
    with session_scope(factory) as session:
        session.add_all(
            [
                _record(first_id, "Example One", "https://example.com/"),
                _record(second_id, "Example Two", "https://example.org/"),
            ]
        )
    config = AutomaticPublicWebRuntimeConfig(
        enabled=True,
        organization_ids=(second_id, first_id, second_id),
        authorization_reference="sa16-l08-approved-runtime-targets",
        reviewed_at=_NOW,
        refresh_interval_seconds=3_600,
        max_link_depth=0,
        max_pages=1,
    )
    with session_scope(factory) as session:
        bundle = build_automatic_public_web_runtime(
            session,
            config,
            now=_NOW,
            timeout_seconds=5.0,
        )
    assert len(bundle.targets) == 2
    assert {target.source_id for target in bundle.targets} == {
        AUTOMATIC_PUBLIC_WEB_SOURCE_ID
    }
    expected = {
        f"public-web-{first_id.hex}",
        f"public-web-{second_id.hex}",
    }
    assert {target.id for target in bundle.targets} == expected
    assert {schedule.source_id for schedule in bundle.schedules} == expected
    assert {schedule.interval_seconds for schedule in bundle.schedules} == {3_600}
    assert set(bundle.adapters) == {
        (target_id, "public-web-sitemap") for target_id in expected
    }


def _factory(tmp_path):
    engine = create_database_engine(f"sqlite+pysqlite:///{tmp_path / 'automatic-web.db'}")
    get_metadata().create_all(engine)
    return create_session_factory(engine)


def _record(
    organization_id: UUID,
    name: str,
    website_url: str | None,
) -> OrganizationRecord:
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
