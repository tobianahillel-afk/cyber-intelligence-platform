from __future__ import annotations

from cip.shared.config.public_web_browser_settings import (
    PublicWebBrowserFallbackSettings,
)
from cip.shared.config.settings import Settings


def automatic_public_web_config_from_settings(settings: Settings):
    from cip.modules.collection_orchestration.application.automatic_public_web_config import (
        AutomaticPublicWebRuntimeConfig,
    )

    browser = PublicWebBrowserFallbackSettings()
    return AutomaticPublicWebRuntimeConfig(
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
