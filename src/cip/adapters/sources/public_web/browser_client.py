from __future__ import annotations

from dataclasses import replace
from datetime import datetime

import httpx

from cip.adapters.sources.public_web.browser_runtime import (
    BrowserPolicyDeniedError,
    BrowserRenderError,
    BrowserRenderLimits,
    render_public_web_page,
)
from cip.adapters.sources.public_web.client import (
    PublicWebClient,
    PublicWebDeadlineExceededError,
    PublicWebFetchResult,
    PublicWebPolicyDeniedError,
    PublicWebResponseError,
    RobotsRules,
)
from cip.adapters.sources.public_web.collection_policy import authorize_public_web_url
from cip.adapters.sources.public_web.registry import PublicWebTarget
from cip.modules.public_footprint.domain.scope import CrawlUsage
from cip.modules.public_footprint.domain.url_identity import CanonicalUrl
from cip.modules.source_governance.infrastructure.registry import SourceRegistryEntry
from cip.shared.kernel.time import require_aware_utc


class BrowserPublicWebClient(PublicWebClient):
    def __init__(
        self,
        client: httpx.Client,
        entry: SourceRegistryEntry,
        *,
        collected_at: datetime,
        limits: BrowserRenderLimits | None = None,
    ) -> None:
        super().__init__(client)
        self._entry = entry
        self._collected_at = require_aware_utc(collected_at, field_name="collected_at")
        self._limits = limits

    @property
    def supports_concurrent_fetches(self) -> bool:
        return False

    def fetch_page(
        self,
        target: PublicWebTarget,
        url: str,
        robots: RobotsRules,
        *,
        usage: CrawlUsage,
        depth: int = 0,
        etag: str | None = None,
        last_modified: str | None = None,
    ) -> PublicWebFetchResult:
        del etag, last_modified
        requested = CanonicalUrl(url).value
        if not robots.allows(requested):
            raise PublicWebPolicyDeniedError("robots.txt denied browser collection")
        limits = self._deadline_limits()
        try:
            rendered = render_public_web_page(
                target,
                requested,
                usage=usage,
                depth=depth,
                authorize_url=self._authorize,
                limits=limits,
            )
        except BrowserPolicyDeniedError as exc:
            raise PublicWebPolicyDeniedError(str(exc)) from exc
        except BrowserRenderError as exc:
            if self.deadline is not None and self.deadline.exceeded:
                raise PublicWebDeadlineExceededError("whole-crawl deadline exceeded") from exc
            raise PublicWebResponseError(str(exc)) from exc
        if self.deadline is not None and self.deadline.exceeded:
            raise PublicWebDeadlineExceededError("whole-crawl deadline exceeded")
        return rendered.fetch_result

    def _deadline_limits(self) -> BrowserRenderLimits:
        limits = self._limits or BrowserRenderLimits()
        if self.deadline is None:
            return limits
        remaining_ms = int(self.deadline.remaining_seconds * 1_000)
        if remaining_ms < 100:
            raise PublicWebDeadlineExceededError("whole-crawl deadline exceeded")
        settle_ms = min(limits.settle_timeout_ms, max(0, remaining_ms - 100))
        navigation_ms = min(
            limits.navigation_timeout_ms,
            max(100, remaining_ms - settle_ms),
        )
        return replace(
            limits,
            navigation_timeout_ms=navigation_ms,
            settle_timeout_ms=settle_ms,
        )

    def _authorize(self, url: str) -> None:
        authorize_public_web_url(self._entry, url, now=self._collected_at)
