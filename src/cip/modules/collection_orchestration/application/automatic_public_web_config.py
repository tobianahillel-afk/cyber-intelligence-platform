from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from cip.adapters.sources.public_web.browser_fallback_governance import (
    AutomaticBrowserFallbackPolicy,
)
from cip.modules.collection_orchestration.application.automatic_public_web_base_config import (
    AutomaticPublicWebBaseConfig,
)
from cip.modules.collection_orchestration.application.automatic_public_web_settings_map import (
    automatic_public_web_config_from_settings,
)
from cip.shared.config.settings import Settings


@dataclass(frozen=True, slots=True)
class AutomaticPublicWebRuntimeConfig(AutomaticPublicWebBaseConfig):
    browser_fallback_enabled: bool = False
    browser_authorization_reference: str | None = None
    browser_reviewed_at: datetime | None = None
    browser_expires_at: datetime | None = None
    browser_min_static_text_chars: int = 200
    browser_max_pages: int = 3

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
        return automatic_public_web_config_from_settings(settings)
