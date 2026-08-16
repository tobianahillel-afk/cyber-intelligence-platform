from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from cip.adapters.sources.public_web.registry import PublicWebTarget
from cip.modules.organizations.domain.entities import Organization
from cip.modules.public_footprint.domain.url_identity import CanonicalUrl
from cip.modules.source_governance.domain.models import (
    AuthorizationStatus,
    DataCategory,
    SourceAuthorization,
    SourcePolicy,
    SourceStatus,
    SourceType,
)
from cip.modules.source_governance.infrastructure.registry import SourceRegistryEntry
from cip.shared.kernel.time import require_aware_utc

AUTOMATIC_PUBLIC_WEB_SOURCE_ID = "automatic-public-company-web"
_PURPOSE = "corporate-public-footprint"
_PROHIBITED_DATA = frozenset(
    {
        DataCategory.CREDENTIAL,
        DataCategory.VICTIM_FILE,
        DataCategory.PRIVATE_COMMUNICATION,
        DataCategory.PRIVATE_PERSONAL_DATA,
        DataCategory.RESTRICTED_CONTENT,
    }
)


@dataclass(frozen=True, slots=True)
class AutomaticPublicWebPolicy:
    authorization_reference: str
    reviewed_at: datetime
    expires_at: datetime | None = None
    allowed_path_prefixes: tuple[str, ...] = ("/",)
    refresh_interval_seconds: int = 86_400
    max_link_depth: int = 1
    discover_sitemaps: bool = True
    discover_feeds: bool = True
    max_sitemap_depth: int = 2
    max_sitemaps: int = 10
    max_feeds: int = 5
    max_pages: int = 100
    max_total_bytes: int = 10_000_000
    max_resource_bytes: int = 1_000_000
    max_redirects: int = 3
    crawl_deadline_seconds: int = 300
    max_crawl_concurrency: int = 1

    def __post_init__(self) -> None:
        reference = self.authorization_reference.strip()
        if not reference:
            raise ValueError("authorization_reference is required")
        reviewed = require_aware_utc(self.reviewed_at, field_name="reviewed_at")
        expires = self.expires_at
        if expires is not None:
            expires = require_aware_utc(expires, field_name="expires_at")
            if expires <= reviewed:
                raise ValueError("expires_at must follow reviewed_at")
        if not self.allowed_path_prefixes or any(
            not prefix.startswith("/") for prefix in self.allowed_path_prefixes
        ):
            raise ValueError("allowed_path_prefixes must contain absolute paths")
        if self.refresh_interval_seconds < 60:
            raise ValueError("refresh_interval_seconds must be at least 60")
        if not 0 <= self.max_link_depth <= 20:
            raise ValueError("max_link_depth must be between 0 and 20")
        if not 0 <= self.max_sitemap_depth <= 10:
            raise ValueError("max_sitemap_depth must be between 0 and 10")
        if not 1 <= self.max_sitemaps <= 100:
            raise ValueError("max_sitemaps must be between 1 and 100")
        if not 1 <= self.max_feeds <= 50:
            raise ValueError("max_feeds must be between 1 and 50")
        if not 1 <= self.crawl_deadline_seconds <= 3_600:
            raise ValueError("crawl_deadline_seconds must be between 1 and 3600")
        if not 1 <= self.max_crawl_concurrency <= 16:
            raise ValueError("max_crawl_concurrency must be between 1 and 16")
        object.__setattr__(self, "authorization_reference", reference)
        object.__setattr__(self, "reviewed_at", reviewed)
        object.__setattr__(self, "expires_at", expires)


@dataclass(frozen=True, slots=True)
class ProvisionedPublicWebTarget:
    target: PublicWebTarget
    source_entry: SourceRegistryEntry
    first_crawl_at: datetime
    refresh_interval_seconds: int


def provision_public_web_target(
    organization: Organization,
    policy: AutomaticPublicWebPolicy,
    *,
    first_crawl_at: datetime,
) -> ProvisionedPublicWebTarget:
    if organization.website_url is None:
        raise ValueError("organization requires a canonical website_url")
    first_crawl = require_aware_utc(first_crawl_at, field_name="first_crawl_at")
    base = CanonicalUrl(organization.website_url)
    homepage = f"{base.origin}/"
    target = PublicWebTarget(
        id=f"public-web-{organization.id.hex}",
        source_id=AUTOMATIC_PUBLIC_WEB_SOURCE_ID,
        organization_id=organization.id,
        canonical_name=organization.canonical_name,
        base_url=homepage,
        seed_urls=(homepage,),
        sitemap_urls=(),
        feed_urls=(),
        discover_security_txt=True,
        discover_sitemaps=policy.discover_sitemaps,
        discover_feeds=policy.discover_feeds,
        allowed_path_prefixes=policy.allowed_path_prefixes,
        enabled=True,
        authorization_reference=policy.authorization_reference,
        authorization_reviewed_at=policy.reviewed_at,
        authorization_expires_at=policy.expires_at,
        max_link_depth=policy.max_link_depth,
        max_sitemap_depth=policy.max_sitemap_depth,
        max_sitemaps=policy.max_sitemaps,
        max_feeds=policy.max_feeds,
        max_pages=policy.max_pages,
        max_total_bytes=policy.max_total_bytes,
        max_resource_bytes=policy.max_resource_bytes,
        max_redirects=policy.max_redirects,
        crawl_deadline_seconds=policy.crawl_deadline_seconds,
        max_crawl_concurrency=policy.max_crawl_concurrency,
    )
    return ProvisionedPublicWebTarget(
        target=target,
        source_entry=_source_entry(target, policy),
        first_crawl_at=first_crawl,
        refresh_interval_seconds=policy.refresh_interval_seconds,
    )


def _source_entry(
    target: PublicWebTarget,
    policy: AutomaticPublicWebPolicy,
) -> SourceRegistryEntry:
    source_policy = SourcePolicy(
        id=AUTOMATIC_PUBLIC_WEB_SOURCE_ID,
        name="Automatic public company website research",
        base_url=target.base_url,
        status=SourceStatus.ENABLED,
        source_type=SourceType.STATIC_HTTP,
        owner=target.canonical_name,
        licence="Deployment-approved bounded first-party public web research",
        allowed_data_categories=frozenset(
            {
                DataCategory.OFFICIAL_DOCUMENT_DISCOVERY,
                DataCategory.TECHNOLOGY_OBSERVATION,
            }
        ),
        prohibited_data_categories=_PROHIBITED_DATA,
        retention_days=365,
        attribution_required=True,
        raw_content_storage=False,
        human_review_required=False,
    )
    authorization = SourceAuthorization(
        status=AuthorizationStatus.APPROVED,
        document_reference=policy.authorization_reference,
        reviewed_at=policy.reviewed_at,
        expires_at=policy.expires_at,
        approved_hosts=frozenset({target.host}),
        approved_path_prefixes=target.allowed_path_prefixes,
        approved_purposes=frozenset({_PURPOSE}),
        automated_collection_allowed=True,
        raw_storage_allowed=False,
    )
    return SourceRegistryEntry(
        policy=source_policy,
        authorization=authorization,
        economics={"monthly_cost": 0},
        notes="Generated from a deployment-approved canonical organization domain.",
    )
