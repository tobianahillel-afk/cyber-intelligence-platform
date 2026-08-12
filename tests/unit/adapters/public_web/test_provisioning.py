from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest

from cip.adapters.sources.public_web.provisioning import (
    AUTOMATIC_PUBLIC_WEB_SOURCE_ID,
    AutomaticPublicWebPolicy,
    provision_public_web_target,
)
from cip.adapters.sources.public_web.registry import PublicWebTarget
from cip.modules.organizations.domain.entities import Organization
from cip.modules.source_governance.domain.models import (
    CollectionRequest,
    DataCategory,
    DecisionReason,
    SourceRuntimeState,
)

_NOW = datetime(2026, 8, 12, 10, 0, tzinfo=UTC)
_ORG_ID = UUID("15712d0d-9054-50b4-8a26-e25d9ea1f509")


def _organization(*, website_url: str | None = "https://www.python.org/about/") -> Organization:
    return Organization(
        id=_ORG_ID,
        canonical_name="Python Software Foundation",
        website_url=website_url,
        created_at=_NOW,
        updated_at=_NOW,
    )


def _policy(**overrides: object) -> AutomaticPublicWebPolicy:
    values: dict[str, object] = {
        "authorization_reference": "sa16-l01-controlled-target",
        "reviewed_at": _NOW,
        "allowed_path_prefixes": ("/",),
        "refresh_interval_seconds": 86_400,
    }
    values.update(overrides)
    return AutomaticPublicWebPolicy(**values)  # type: ignore[arg-type]


def test_provisioning_creates_deterministic_governed_homepage_target() -> None:
    provisioned = provision_public_web_target(
        _organization(),
        _policy(),
        first_crawl_at=_NOW + timedelta(minutes=5),
    )

    target = provisioned.target
    assert target.id == f"public-web-{_ORG_ID.hex}"
    assert target.source_id == AUTOMATIC_PUBLIC_WEB_SOURCE_ID
    assert target.id != target.source_id
    assert target.base_url == "https://www.python.org/"
    assert target.seed_urls == ("https://www.python.org/",)
    assert target.sitemap_urls == ()
    assert target.feed_urls == ()
    assert target.discover_security_txt is True
    assert target.security_txt_url == "https://www.python.org/.well-known/security.txt"
    assert target.executable_at(_NOW) is True
    assert provisioned.first_crawl_at == _NOW + timedelta(minutes=5)
    assert provisioned.refresh_interval_seconds == 86_400


def test_generated_source_governance_allows_scope_and_denies_other_hosts() -> None:
    provisioned = provision_public_web_target(
        _organization(),
        _policy(),
        first_crawl_at=_NOW,
    )
    entry = provisioned.source_entry

    allowed = entry.policy.evaluate(
        CollectionRequest(
            data_category=DataCategory.OFFICIAL_DOCUMENT_DISCOVERY,
            target_url="https://www.python.org/robots.txt",
            purpose="corporate-public-footprint",
            automated=True,
            store_raw_content=False,
        ),
        entry.authorization,
        SourceRuntimeState(remaining_requests=1),
        now=_NOW,
    )
    denied = entry.policy.evaluate(
        CollectionRequest(
            data_category=DataCategory.OFFICIAL_DOCUMENT_DISCOVERY,
            target_url="https://example.com/",
            purpose="corporate-public-footprint",
            automated=True,
            store_raw_content=False,
        ),
        entry.authorization,
        SourceRuntimeState(remaining_requests=1),
        now=_NOW,
    )

    assert allowed.allowed is True
    assert denied.allowed is False
    assert denied.reason is DecisionReason.HOST_NOT_ALLOWED
    assert entry.authorization.raw_storage_allowed is False


def test_provisioning_requires_canonical_website() -> None:
    with pytest.raises(ValueError, match="canonical website_url"):
        provision_public_web_target(
            _organization(website_url=None),
            _policy(),
            first_crawl_at=_NOW,
        )


def test_expired_target_fails_closed() -> None:
    provisioned = provision_public_web_target(
        _organization(),
        _policy(expires_at=_NOW + timedelta(hours=1)),
        first_crawl_at=_NOW,
    )

    assert provisioned.target.executable_at(_NOW + timedelta(hours=2)) is False


def test_legacy_target_defaults_source_id_to_target_id() -> None:
    target = PublicWebTarget(
        id="legacy-source",
        organization_id=_ORG_ID,
        canonical_name="Legacy",
        base_url="https://example.com/",
        seed_urls=("https://example.com/",),
        sitemap_urls=(),
        allowed_path_prefixes=("/",),
        enabled=True,
        authorization_reference="legacy-review",
        authorization_reviewed_at=_NOW,
    )

    assert target.source_id == "legacy-source"
