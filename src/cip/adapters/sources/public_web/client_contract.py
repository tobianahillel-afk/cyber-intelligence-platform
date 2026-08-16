from __future__ import annotations

from dataclasses import dataclass
from urllib.robotparser import RobotFileParser

import httpx

from cip import __version__

PUBLIC_WEB_USER_AGENT = (
    f"CyberIntelligencePlatform/{__version__} (+public-evidence-collector)"
)
REDIRECT_STATUSES = {
    httpx.codes.MOVED_PERMANENTLY,
    httpx.codes.FOUND,
    httpx.codes.SEE_OTHER,
    httpx.codes.TEMPORARY_REDIRECT,
    httpx.codes.PERMANENT_REDIRECT,
}
TOMBSTONE_STATUSES = {httpx.codes.NOT_FOUND, httpx.codes.GONE}
FEED_MIME_TYPES = {
    "application/atom+xml",
    "application/rss+xml",
    "application/xml",
    "text/xml",
}
NOT_MODIFIED_MIME_TYPE = "application/x-public-resource-not-modified"
OCTET_STREAM_MIME_TYPE = "application/octet-stream"


class PublicWebResponseError(RuntimeError):
    """A public-web response violated the configured safety contract."""


class PublicWebPolicyDeniedError(RuntimeError):
    """Robots or target scope denied a public-web request."""


class PublicWebDeadlineExceededError(RuntimeError):
    """The configured whole-crawl wall-clock deadline expired."""


@dataclass(frozen=True, slots=True)
class PublicWebFetchResult:
    requested_url: str
    fetched_url: str
    body: bytes
    mime_type: str
    etag: str | None
    last_modified: str | None
    redirects: int
    status_code: int = 200
    response_headers: tuple[tuple[str, str], ...] = ()
    bytes_received: int = 0


@dataclass(frozen=True, slots=True)
class RobotsRules:
    parser: RobotFileParser
    source_url: str
    missing: bool
    bytes_fetched: int
    sitemap_urls: tuple[str, ...] = ()

    def allows(self, url: str) -> bool:
        return self.missing or self.parser.can_fetch(PUBLIC_WEB_USER_AGENT, url)
