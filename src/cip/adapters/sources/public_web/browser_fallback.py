from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime

import httpx

from cip.adapters.sources.public_web.client import (
    PublicWebClient,
    PublicWebFetchResult,
    RobotsRules,
)
from cip.adapters.sources.public_web.parsing import extract_html
from cip.adapters.sources.public_web.registry import PublicWebTarget
from cip.modules.public_footprint.domain.scope import CrawlUsage
from cip.modules.source_governance.infrastructure.registry import SourceRegistryEntry
from cip.shared.kernel.time import require_aware_utc


@dataclass(frozen=True, slots=True)
class BrowserFallbackPolicy:
    min_static_text_chars: int = 200
    max_browser_pages: int = 3

    def __post_init__(self) -> None:
        if not 1 <= self.min_static_text_chars <= 100_000:
            raise ValueError("min_static_text_chars must be between 1 and 100000")
        if not 1 <= self.max_browser_pages <= 25:
            raise ValueError("max_browser_pages must be between 1 and 25")

    def should_render(self, fetched: PublicWebFetchResult) -> bool:
        if fetched.status_code != 200 or fetched.mime_type != "text/html":
            return False
        extracted = extract_html(
            fetched.body,
            max_text_chars=self.min_static_text_chars,
        )
        if len(extracted.text) >= self.min_static_text_chars:
            return False
        return b"<script" in fetched.body.lower()


class FallbackPublicWebClient(PublicWebClient):
    def __init__(
        self,
        client: httpx.Client,
        browser_entry: SourceRegistryEntry,
        *,
        collected_at: datetime,
        policy: BrowserFallbackPolicy,
        request_timeout_seconds: float | None = None,
    ) -> None:
        super().__init__(client, request_timeout_seconds=request_timeout_seconds)
        self._fallback_http_client = client
        self._browser_entry = browser_entry
        self._collected_at = require_aware_utc(collected_at, field_name="collected_at")
        self._policy = policy
        self._fallback_urls: list[str] = []

    @property
    def supports_concurrent_fetches(self) -> bool:
        return False

    @property
    def fallback_urls(self) -> tuple[str, ...]:
        return tuple(self._fallback_urls)

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
        static = super().fetch_page(
            target,
            url,
            robots,
            usage=usage,
            depth=depth,
            etag=etag,
            last_modified=last_modified,
        )
        if (
            len(self._fallback_urls) >= self._policy.max_browser_pages
            or not self._policy.should_render(static)
        ):
            return static
        from cip.adapters.sources.public_web.browser_client import BrowserPublicWebClient

        browser = BrowserPublicWebClient(
            self._fallback_http_client,
            self._browser_entry,
            collected_at=self._collected_at,
        )
        if self.deadline is not None:
            browser.bind_deadline(self.deadline)
        browser_usage = CrawlUsage(
            pages_fetched=usage.pages_fetched,
            bytes_fetched=usage.bytes_fetched + static.bytes_received,
        )
        rendered = browser.fetch_page(
            target,
            url,
            robots,
            usage=browser_usage,
            depth=depth,
        )
        self._fallback_urls.append(rendered.fetched_url)
        return replace(
            rendered,
            bytes_received=static.bytes_received + rendered.bytes_received,
        )