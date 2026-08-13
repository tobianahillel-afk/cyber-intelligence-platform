from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy.orm import Session

from cip.adapters.sources.public_web.browser_fallback_governance import (
    AutomaticBrowserFallbackPolicy,
    build_browser_fallback_entry,
)
from cip.adapters.sources.public_web.provisioning import (
    AutomaticPublicWebPolicy,
    provision_public_web_target,
)
from cip.adapters.sources.public_web.registry import PublicWebTarget
from cip.modules.collection_orchestration.application.ports import CollectionAdapter
from cip.modules.collection_orchestration.application.public_web_adapter import PublicWebAdapter
from cip.modules.collection_orchestration.application.public_web_fallback_adapter import PublicWebFallbackAdapter
from cip.modules.collection_orchestration.domain.models import SourceSchedule
from cip.modules.organizations.domain.entities import Organization
from cip.modules.organizations.infrastructure.models import OrganizationRecord
from cip.shared.config.public_web_browser_settings import PublicWebBrowserFallbackSettings
from cip.shared.config.settings import Settings
from cip.shared.kernel.time import require_aware_utc


@dataclass(frozen=True, slots=True)
class AutomaticPublicWebRuntimeConfig:
    enabled: bool = False
    organization_ids: tuple[UUID, ...] = ()
    authorization_reference: str | None = None
    reviewed_at: datetime | None = None
    expires_at: datetime | None = None
    refresh_interval_seconds: int = 86_400
    max_link_depth: int = 1
    max_pages: int = 100
    max_total_bytes: int = 10_000_000
    max_resource_bytes: int = 1_000_000
    max_redirects: int = 3
    browser_fallback_enabled: bool = False
    browser_authorization_reference: str | None = None
    browser_reviewed_at: datetime | None = None
    browser_expires_at: datetime | None = None
    browser_min_static_text_chars: int = 200
    browser_max_pages: int = 3

    def policy(self) -> AutomaticPublicWebPolicy | None:
        if not self.enabled:
            return None
        if not self.organization_ids:
            raise ValueError("automatic public web requires approved organization ids")
        if self.authorization_reference is None:
            raise ValueError("automatic public web requires an authorization reference")
        if self.reviewed_at is None:
            raise ValueError("automatic public web requires an authorization review time")
        return AutomaticPublicWebPolicy(
            authorization_reference=self.authorization_reference,
            reviewed_at=self.reviewed_at,
            expires_at=self.expires_at,
            refresh_interval_seconds=self.refresh_interval_seconds,
            max_link_depth=self.max_link_depth,
            max_pages=self.max_pages,
            max_total_bytes=self.max_total_bytes,
            max_resource_bytes=self.max_resource_bytes,
            max_redirects=self.max_redirects,
        )

    def browser_policy(self) -> AutomaticBrowserFallbackPolicy | None:
        if not self.browser_fallback_enabled:
            return None
        if self.browser_authorization_reference is None:
            raise ValueError("browser fallback requires an authorization reference")
        if self.browser_reviewed_at is None:
            raise ValueError("browser fallback requires an authorization review time")
        return AutomaticBrowserFallbackPolicy(
            authorization_reference=self.browser_authorization_reference,
            reviewed_at=self.browser_reviewed_at,
            expires_at=self.browser_expires_at,
            min_static_text_chars=self.browser_min_static_text_chars,
            max_browser_pages=self.browser_max_pages,
        )

    @classmethod
    def from_settings(cls, settings: Settings) -> AutomaticPublicWebRuntimeConfig:
        browser = PublicWebBrowserFallbackSettings()
        return cls(
            enabled=settings.automatic_public_web_enabled,
            organization_ids=settings.automatic_public_web_organization_ids,
            authorization_reference=settings.automatic_public_web_authorization_reference,
            reviewed_at=settings.automatic_public_web_reviewed_at,
            expires_at=settings.automatic_public_web_expires_at,
            refresh_interval_seconds=settings.automatic_public_web_refresh_interval_seconds,
            max_link_depth=settings.automatic_public_web_max_link_depth,
            max_pages=settings.automatic_public_web_max_pages,
            max_total_bytes=settings.automatic_public_web_max_total_bytes,
            max_resource_bytes=settings.automatic_public_web_max_resource_bytes,
            max_redirects=settings.automatic_public_web_max_redirects,
            browser_fallback_enabled=browser.enabled,
            browser_authorization_reference=browser.authorization_reference,
            browser_reviewed_at=browser.reviewed_at,
            browser_expires_at=browser.expires_at,
            browser_min_static_text_chars=browser.min_static_text_chars,
            browser_max_pages=browser.max_pages,
        )


@dataclass(frozen=True, slots=True)
class AutomaticPublicWebRuntimeBundle:
    adapters: dict[tuple[str, str], CollectionAdapter]
    schedules: tuple[SourceSchedule, ...]
    targets: tuple[PublicWebTarget, ...]


def build_automatic_public_web_runtime(
    session: Session,
    config: AutomaticPublicWebRuntimeConfig,
    *,
    now: datetime,
    timeout_seconds: float,
) -> AutomaticPublicWebRuntimeBundle:
    current = require_aware_utc(now, field_name="now")
    policy = config.policy()
    if policy is None:
        return AutomaticPublicWebRuntimeBundle({}, (), ())
    browser_policy = config.browser_policy()
    adapters: dict[tuple[str, str], CollectionAdapter] = {}
    schedules: list[SourceSchedule] = []
    targets: list[PublicWebTarget] = []
    for organization_id in sorted(set(config.organization_ids), key=str):
        organization = _load_organization(session, organization_id, current)
        provisioned = provision_public_web_target(
            organization,
            policy,
            first_crawl_at=current,
        )
        if browser_policy is None:
            adapter: CollectionAdapter = PublicWebAdapter(
                provisioned.source_entry,
                provisioned.target,
                timeout_seconds=timeout_seconds,
            )
        else:
            browser_entry = build_browser_fallback_entry(
                provisioned.source_entry,
                provisioned.target,
                browser_policy,
            )
            adapter = PublicWebFallbackAdapter(
                provisioned.source_entry,
                browser_entry,
                provisioned.target,
                fallback_policy=browser_policy.fallback_policy(),
                timeout_seconds=timeout_seconds,
            )
        identity = (adapter.source_id, adapter.adapter_id)
        if identity in adapters:
            raise ValueError(f"duplicate automatic public web adapter: {identity}")
        adapters[identity] = adapter
        schedules.append(
            SourceSchedule(
                source_id=adapter.source_id,
                adapter_id=adapter.adapter_id,
                interval_seconds=provisioned.refresh_interval_seconds,
            )
        )
        targets.append(provisioned.target)
    return AutomaticPublicWebRuntimeBundle(
        adapters=adapters,
        schedules=tuple(schedules),
        targets=tuple(targets),
    )


def _load_organization(
    session: Session,
    organization_id: UUID,
    now: datetime,
) -> Organization:
    record = session.get(OrganizationRecord, organization_id)
    if record is None:
        raise ValueError(f"approved automatic public web organization not found: {organization_id}")
    if record.website_url is None:
        raise ValueError(
            f"approved automatic public web organization has no website: {organization_id}"
        )
    return Organization(
        id=record.id,
        canonical_name=record.canonical_name,
        legal_name=record.legal_name,
        country_code=record.country_code,
        website_url=record.website_url,
        registration_ids=tuple(record.registration_ids),
        created_at=now,
        updated_at=now,
    )
