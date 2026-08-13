from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest

from cip.modules.collection_orchestration.application.automatic_public_web_runtime import (
    AutomaticPublicWebRuntimeConfig,
    build_automatic_public_web_runtime,
)
from cip.modules.collection_orchestration.application.public_web_adapter import PublicWebAdapter
from cip.modules.collection_orchestration.application.public_web_fallback_adapter import (
    PublicWebFallbackAdapter,
)
from cip.modules.organizations.infrastructure.models import OrganizationRecord
from cip.modules.source_governance.domain.models import SourceType
from cip.shared.persistence.metadata import get_metadata
from cip.shared.persistence.session import (
    create_database_engine,
    create_session_factory,
    session_scope,
)

_NOW = datetime(2026, 8, 13, 18, tzinfo=UTC)
_ORG_ID = UUID("15712d0d-9054-50b4-8a26-e25d9ea1f509")


def test_browser_fallback_is_disabled_by_default(tmp_path) -> None:
    factory = _factory(tmp_path)
    _persist_org(factory)
    with session_scope(factory) as session:
        bundle = build_automatic_public_web_runtime(
            session,
            _config(),
            now=_NOW,
            timeout_seconds=5.0,
        )

    adapter = next(iter(bundle.adapters.values()))
    assert isinstance(adapter, PublicWebAdapter)
    assert bundle.schedules[0].adapter_id == "public-web-sitemap"


@pytest.mark.parametrize(
    "overrides",
    [
        {"browser_fallback_enabled": True},
        {
            "browser_fallback_enabled": True,
            "browser_authorization_reference": "browser-approved",
        },
    ],
)
def test_browser_fallback_requires_separate_authorization(
    tmp_path,
    overrides: dict[str, object],
) -> None:
    factory = _factory(tmp_path)
    _persist_org(factory)
    with (
        session_scope(factory) as session,
        pytest.raises(ValueError, match="browser fallback requires"),
    ):
        build_automatic_public_web_runtime(
            session,
            _config(**overrides),
            now=_NOW,
            timeout_seconds=5.0,
        )


def test_browser_fallback_builds_explicit_browser_adapter(tmp_path) -> None:
    factory = _factory(tmp_path)
    _persist_org(factory)
    with session_scope(factory) as session:
        bundle = build_automatic_public_web_runtime(
            session,
            _config(
                browser_fallback_enabled=True,
                browser_authorization_reference="browser-approved",
                browser_reviewed_at=_NOW,
                browser_min_static_text_chars=300,
                browser_max_pages=2,
            ),
            now=_NOW,
            timeout_seconds=5.0,
        )

    adapter = next(iter(bundle.adapters.values()))
    assert isinstance(adapter, PublicWebFallbackAdapter)
    assert adapter.adapter_id == "public-web-browser-fallback"
    assert adapter._static_entry.policy.source_type is SourceType.STATIC_HTTP
    assert adapter._browser_entry.policy.source_type is SourceType.BROWSER
    assert adapter._browser_entry.policy.id == "automatic-public-company-web-browser"
    assert adapter._browser_entry.authorization.document_reference == "browser-approved"
    assert adapter._browser_entry.authorization.approved_hosts == frozenset({"example.com"})
    assert bundle.schedules[0].adapter_id == "public-web-browser-fallback"


def test_browser_fallback_rejects_invalid_expiry(tmp_path) -> None:
    factory = _factory(tmp_path)
    _persist_org(factory)
    with (
        session_scope(factory) as session,
        pytest.raises(ValueError, match="browser_expires_at"),
    ):
        build_automatic_public_web_runtime(
            session,
            _config(
                browser_fallback_enabled=True,
                browser_authorization_reference="browser-approved",
                browser_reviewed_at=_NOW,
                browser_expires_at=_NOW - timedelta(minutes=1),
            ),
            now=_NOW,
            timeout_seconds=5.0,
        )


def _config(**overrides: object) -> AutomaticPublicWebRuntimeConfig:
    values: dict[str, object] = {
        "enabled": True,
        "organization_ids": (_ORG_ID,),
        "authorization_reference": "static-approved",
        "reviewed_at": _NOW,
        "max_link_depth": 0,
        "max_pages": 1,
    }
    values.update(overrides)
    return AutomaticPublicWebRuntimeConfig(**values)  # type: ignore[arg-type]


def _factory(tmp_path):
    engine = create_database_engine(f"sqlite+pysqlite:///{tmp_path / 'fallback-runtime.db'}")
    get_metadata().create_all(engine)
    return create_session_factory(engine)


def _persist_org(factory) -> None:
    with session_scope(factory) as session:
        session.add(
            OrganizationRecord(
                id=_ORG_ID,
                canonical_name="Fallback Organization",
                legal_name=None,
                country_code=None,
                website_url="https://example.com/",
                registration_ids=[],
                created_at=_NOW,
                updated_at=_NOW,
            )
        )
