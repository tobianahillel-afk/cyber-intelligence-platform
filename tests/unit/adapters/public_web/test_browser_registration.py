from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from cip.adapters.sources.public_web.registry import PublicWebTarget
from cip.modules.collection_orchestration.application.ports import CollectionAdapter
from cip.modules.collection_orchestration.application.public_web_adapter import PublicWebAdapter
from cip.modules.collection_orchestration.application.public_web_browser_adapter import (
    PublicWebBrowserAdapter,
)
from cip.modules.collection_orchestration.application.public_web_registration import (
    register_public_web_adapters,
)
from cip.modules.source_governance.domain.models import (
    AuthorizationStatus,
    DataCategory,
    SourceAuthorization,
    SourcePolicy,
    SourceStatus,
    SourceType,
)
from cip.modules.source_governance.infrastructure.registry import SourceRegistryEntry

_NOW = datetime(2026, 8, 13, 12, tzinfo=UTC)


@pytest.mark.parametrize(
    ("source_type", "adapter_type", "adapter_id"),
    [
        (SourceType.STATIC_HTTP, PublicWebAdapter, "public-web-sitemap"),
        (SourceType.BROWSER, PublicWebBrowserAdapter, "public-web-browser"),
    ],
)
def test_registration_dispatches_public_web_source_type(
    source_type: SourceType,
    adapter_type: type[PublicWebAdapter] | type[PublicWebBrowserAdapter],
    adapter_id: str,
) -> None:
    target = _target(source_id="governed-source")
    adapters: dict[tuple[str, str], CollectionAdapter] = {}

    register_public_web_adapters(
        adapters,
        {target.source_id: _entry(source_type, source_id=target.source_id)},
        (target,),
        timeout_seconds=10.0,
    )

    registered = adapters[(target.id, adapter_id)]
    assert isinstance(registered, adapter_type)
    assert registered.source_id == target.id


def test_registration_preserves_legacy_matching_identity() -> None:
    target = _target()
    adapters: dict[tuple[str, str], CollectionAdapter] = {}

    register_public_web_adapters(
        adapters,
        {target.source_id: _entry(SourceType.STATIC_HTTP)},
        (target,),
        timeout_seconds=10.0,
    )

    assert (target.id, "public-web-sitemap") in adapters


def test_registration_skips_disabled_target() -> None:
    target = _target(enabled=False)
    adapters: dict[tuple[str, str], CollectionAdapter] = {}

    register_public_web_adapters(
        adapters,
        {},
        (target,),
        timeout_seconds=10.0,
    )

    assert adapters == {}


def test_registration_rejects_missing_policy() -> None:
    target = _target(source_id="governed-source")
    with pytest.raises(ValueError, match="governed-source"):
        register_public_web_adapters({}, {}, (target,), timeout_seconds=10.0)


def test_registration_rejects_unsupported_source_type() -> None:
    target = _target(source_id="governed-source")
    with pytest.raises(ValueError, match="unsupported source type"):
        register_public_web_adapters(
            {},
            {target.source_id: _entry(SourceType.API, source_id=target.source_id)},
            (target,),
            timeout_seconds=10.0,
        )


def _target(
    *,
    enabled: bool = True,
    source_id: str | None = None,
) -> PublicWebTarget:
    return PublicWebTarget(
        id="registration-test",
        source_id=source_id,
        organization_id=uuid4(),
        canonical_name="Registration Test",
        base_url="https://example.com/",
        seed_urls=("https://example.com/app",),
        sitemap_urls=(),
        feed_urls=(),
        discover_security_txt=False,
        discover_sitemaps=False,
        discover_feeds=False,
        allowed_path_prefixes=("/",),
        enabled=enabled,
        authorization_reference="registration-test-approval",
        authorization_reviewed_at=_NOW,
        max_link_depth=0,
        max_pages=1,
        max_total_bytes=20_000,
        max_resource_bytes=10_000,
        max_redirects=2,
    )


def _entry(
    source_type: SourceType,
    *,
    source_id: str = "registration-test",
) -> SourceRegistryEntry:
    return SourceRegistryEntry(
        policy=SourcePolicy(
            id=source_id,
            name="Registration Test",
            base_url="https://example.com/",
            status=SourceStatus.ENABLED,
            source_type=source_type,
            owner="tests",
            licence="Controlled registration test source",
            allowed_data_categories=frozenset(
                {
                    DataCategory.OFFICIAL_DOCUMENT_DISCOVERY,
                    DataCategory.TECHNOLOGY_OBSERVATION,
                }
            ),
            retention_days=30,
            raw_content_storage=False,
            human_review_required=False,
        ),
        authorization=SourceAuthorization(
            status=AuthorizationStatus.APPROVED,
            document_reference="registration-test-approval",
            reviewed_at=_NOW,
            approved_hosts=frozenset({"example.com"}),
            approved_path_prefixes=("/",),
            approved_purposes=frozenset({"corporate-public-footprint"}),
            automated_collection_allowed=True,
            raw_storage_allowed=False,
        ),
        economics={"monthly_cost": 0},
    )
