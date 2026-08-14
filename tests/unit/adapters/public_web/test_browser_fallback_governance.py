from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from cip.adapters.sources.public_web.browser_fallback_governance import (
    AUTOMATIC_PUBLIC_WEB_BROWSER_SOURCE_ID,
    AutomaticBrowserFallbackPolicy,
    build_browser_fallback_entry,
)
from cip.adapters.sources.public_web.registry import PublicWebTarget
from cip.modules.source_governance.domain.models import (
    AuthorizationStatus,
    DataCategory,
    SourceAuthorization,
    SourcePolicy,
    SourceStatus,
    SourceType,
)
from cip.modules.source_governance.infrastructure.registry import SourceRegistryEntry

_NOW = datetime(2026, 8, 13, 18, tzinfo=UTC)


def test_policy_normalizes_and_builds_browser_entry() -> None:
    policy = AutomaticBrowserFallbackPolicy(
        authorization_reference="  browser-change  ",
        reviewed_at=_NOW,
        expires_at=_NOW + timedelta(days=30),
        min_static_text_chars=50,
        max_browser_pages=2,
    )
    target = _target()

    entry = build_browser_fallback_entry(_static_entry(), target, policy)

    assert policy.authorization_reference == "browser-change"
    assert policy.fallback_policy().min_static_text_chars == 50
    assert policy.fallback_policy().max_browser_pages == 2
    assert entry.policy.id == AUTOMATIC_PUBLIC_WEB_BROWSER_SOURCE_ID
    assert entry.policy.source_type is SourceType.BROWSER
    assert entry.policy.raw_content_storage is False
    assert entry.authorization.status is AuthorizationStatus.APPROVED
    assert entry.authorization.document_reference == "browser-change"
    assert entry.authorization.approved_hosts == frozenset({target.host})
    assert entry.authorization.approved_path_prefixes == target.allowed_path_prefixes
    assert entry.authorization.raw_storage_allowed is False


def test_policy_allows_no_expiry() -> None:
    policy = AutomaticBrowserFallbackPolicy(
        authorization_reference="browser-change",
        reviewed_at=_NOW,
    )

    assert policy.expires_at is None


@pytest.mark.parametrize("reference", ["", "   "])
def test_policy_rejects_empty_authorization_reference(reference: str) -> None:
    with pytest.raises(ValueError, match="authorization reference"):
        AutomaticBrowserFallbackPolicy(
            authorization_reference=reference,
            reviewed_at=_NOW,
        )


def test_policy_rejects_expiry_not_after_review() -> None:
    with pytest.raises(ValueError, match="must follow"):
        AutomaticBrowserFallbackPolicy(
            authorization_reference="browser-change",
            reviewed_at=_NOW,
            expires_at=_NOW,
        )


def test_policy_rejects_naive_review_time() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        AutomaticBrowserFallbackPolicy(
            authorization_reference="browser-change",
            reviewed_at=datetime(2026, 8, 13, 18),
        )


def _target() -> PublicWebTarget:
    return PublicWebTarget(
        id="fallback-target",
        source_id="static-source",
        organization_id=uuid4(),
        canonical_name="Fallback Test",
        base_url="https://example.com/",
        seed_urls=("https://example.com/",),
        sitemap_urls=(),
        feed_urls=(),
        discover_security_txt=False,
        discover_sitemaps=False,
        discover_feeds=False,
        allowed_path_prefixes=("/",),
        enabled=True,
        authorization_reference="static-approval",
        authorization_reviewed_at=_NOW,
        max_link_depth=0,
        max_pages=3,
        max_total_bytes=1_000_000,
        max_resource_bytes=100_000,
        max_redirects=1,
    )


def _static_entry() -> SourceRegistryEntry:
    return SourceRegistryEntry(
        policy=SourcePolicy(
            id="static-source",
            name="Static source",
            base_url="https://example.com/",
            status=SourceStatus.ENABLED,
            source_type=SourceType.STATIC_HTTP,
            owner="tests",
            licence="Controlled test source",
            allowed_data_categories=frozenset(
                {DataCategory.OFFICIAL_DOCUMENT_DISCOVERY}
            ),
            retention_days=30,
            raw_content_storage=False,
            human_review_required=False,
        ),
        authorization=SourceAuthorization(
            status=AuthorizationStatus.APPROVED,
            document_reference="static-approval",
            reviewed_at=_NOW,
            approved_hosts=frozenset({"example.com"}),
            approved_path_prefixes=("/",),
            approved_purposes=frozenset({"corporate-public-footprint"}),
            automated_collection_allowed=True,
            raw_storage_allowed=False,
        ),
        economics={"monthly_cost": 0},
    )
