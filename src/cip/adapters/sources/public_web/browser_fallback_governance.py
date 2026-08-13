from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from cip.adapters.sources.public_web.browser_fallback import BrowserFallbackPolicy
from cip.adapters.sources.public_web.registry import PublicWebTarget
from cip.modules.source_governance.domain.models import (
    AuthorizationStatus,
    SourceAuthorization,
    SourcePolicy,
    SourceStatus,
    SourceType,
)
from cip.modules.source_governance.infrastructure.registry import SourceRegistryEntry
from cip.shared.kernel.time import require_aware_utc

AUTOMATIC_PUBLIC_WEB_BROWSER_SOURCE_ID = "automatic-public-company-web-browser"
_PURPOSE = "corporate-public-footprint"


@dataclass(frozen=True, slots=True)
class AutomaticBrowserFallbackPolicy:
    authorization_reference: str
    reviewed_at: datetime
    expires_at: datetime | None = None
    min_static_text_chars: int = 200
    max_browser_pages: int = 3

    def __post_init__(self) -> None:
        reference = self.authorization_reference.strip()
        if not reference:
            raise ValueError("browser fallback requires an authorization reference")
        reviewed = require_aware_utc(self.reviewed_at, field_name="browser_reviewed_at")
        expires = self.expires_at
        if expires is not None:
            expires = require_aware_utc(expires, field_name="browser_expires_at")
            if expires <= reviewed:
                raise ValueError("browser_expires_at must follow browser_reviewed_at")
        BrowserFallbackPolicy(
            min_static_text_chars=self.min_static_text_chars,
            max_browser_pages=self.max_browser_pages,
        )
        object.__setattr__(self, "authorization_reference", reference)
        object.__setattr__(self, "reviewed_at", reviewed)
        object.__setattr__(self, "expires_at", expires)

    def fallback_policy(self) -> BrowserFallbackPolicy:
        return BrowserFallbackPolicy(
            min_static_text_chars=self.min_static_text_chars,
            max_browser_pages=self.max_browser_pages,
        )


def build_browser_fallback_entry(
    static_entry: SourceRegistryEntry,
    target: PublicWebTarget,
    policy: AutomaticBrowserFallbackPolicy,
) -> SourceRegistryEntry:
    source_policy = SourcePolicy(
        id=AUTOMATIC_PUBLIC_WEB_BROWSER_SOURCE_ID,
        name="Automatic public company website browser fallback",
        base_url=target.base_url,
        status=SourceStatus.ENABLED,
        source_type=SourceType.BROWSER,
        owner=target.canonical_name,
        licence="Deployment-approved bounded first-party browser fallback",
        allowed_data_categories=static_entry.policy.allowed_data_categories,
        prohibited_data_categories=static_entry.policy.prohibited_data_categories,
        retention_days=static_entry.policy.retention_days,
        attribution_required=static_entry.policy.attribution_required,
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
        notes="Separate deployment approval for bounded browser fallback.",
    )
