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
    max_depth: int = 1
    max_pages: int = 100
    max_total_bytes: int = 10_000_000
    max_resource_bytes: int = 1_000_000
    max_redirects: int = 3

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
        if not 0 <= self.max_depth <= 20:
            raise ValueError("max_depth must be between 0 and 20")
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
        allowed_path_prefixes=policy.allowed_path_prefixes,
        enabled=True,
        authorization_reference=policy.authorization_reference,
        authorization_reviewed_at=policy.reviewed_at,
        authorization_expires_at=policy.expires_at,
        max_depth=policy.max_depth,
        max_pages=policy.max_pages,
        max_total_bytes=policy.max_total_bytes,
        max_resource_bytes=policy.max_resource_bytes,
        max_redirects=policy.max_redirects,
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
