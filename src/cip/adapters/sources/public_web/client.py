from __future__ import annotations

from urllib.parse import urljoin
from urllib.robotparser import RobotFileParser

import httpx

from cip.adapters.sources.public_web.client_contract import (
    FEED_MIME_TYPES,
    NOT_MODIFIED_MIME_TYPE,
    OCTET_STREAM_MIME_TYPE,
    PUBLIC_WEB_USER_AGENT,
    REDIRECT_STATUSES,
    TOMBSTONE_STATUSES,
    PublicWebDeadlineExceededError,
    PublicWebFetchResult,
    PublicWebPolicyDeniedError,
    PublicWebResponseError,
    RobotsRules,
)
from cip.adapters.sources.public_web.client_helpers import (
    bounded_body,
    content_type,
    header,
    normalized_page_mime,
    page_headers,
    require_structured_url_in_scope,
    robots_sitemaps,
)
from cip.adapters.sources.public_web.client_http import BoundedHttpTransport
from cip.adapters.sources.public_web.crawl_runtime import CrawlDeadline
from cip.adapters.sources.public_web.registry import PublicWebTarget
from cip.adapters.sources.public_web.response_headers import bounded_evidence_headers
from cip.modules.public_footprint.domain.scope import CrawlUsage
from cip.modules.public_footprint.domain.url_identity import CanonicalUrl


class PublicWebClient:
    ROBOTS_MAX_BYTES = 256_000
    SITEMAP_MAX_BYTES = 1_000_000
    FEED_MAX_BYTES = 1_000_000

    def __init__(
        self,
        client: httpx.Client,
        *,
        request_timeout_seconds: float | None = None,
    ) -> None:
        self._transport = BoundedHttpTransport(
            client,
            request_timeout_seconds=request_timeout_seconds,
        )

    @property
    def deadline(self) -> CrawlDeadline | None:
        return self._transport.deadline

    @property
    def supports_concurrent_fetches(self) -> bool:
        return True

    def bind_deadline(self, deadline: CrawlDeadline) -> None:
        self._transport.bind_deadline(deadline)

    def fetch_robots(self, target: PublicWebTarget) -> RobotsRules:
        response = self._transport.get(
            target.robots_url,
            headers={"Accept": "text/plain", "User-Agent": PUBLIC_WEB_USER_AGENT},
            follow_redirects=False,
            max_bytes=self.ROBOTS_MAX_BYTES,
        )
        if response.status_code == httpx.codes.NOT_FOUND:
            parser = RobotFileParser()
            parser.set_url(target.robots_url)
            parser.parse([])
            return RobotsRules(
                parser,
                target.robots_url,
                missing=True,
                bytes_fetched=0,
            )
        if response.status_code in REDIRECT_STATUSES:
            raise PublicWebResponseError("robots.txt redirects are not followed")
        response.raise_for_status()
        mime_type = content_type(response)
        if mime_type not in {"text/plain", OCTET_STREAM_MIME_TYPE}:
            raise PublicWebResponseError("robots.txt returned an unexpected content type")
        body = bounded_body(response, max_bytes=self.ROBOTS_MAX_BYTES)
        lines = body.decode("utf-8", errors="replace").splitlines()
        parser = RobotFileParser()
        parser.set_url(target.robots_url)
        parser.parse(lines)
        return RobotsRules(
            parser,
            target.robots_url,
            missing=False,
            bytes_fetched=len(body),
            sitemap_urls=robots_sitemaps(
                lines,
                target,
                max_sitemaps=target.max_sitemaps,
            ),
        )

    def fetch_sitemap(
        self,
        target: PublicWebTarget,
        sitemap_url: str,
        robots: RobotsRules,
        *,
        discovered: bool = False,
    ) -> PublicWebFetchResult:
        canonical = CanonicalUrl(sitemap_url).value
        explicit = canonical in target.sitemap_urls
        if not explicit:
            if not discovered:
                raise PublicWebPolicyDeniedError(
                    "sitemap URL is not explicitly configured"
                )
            if not target.discover_sitemaps:
                raise PublicWebPolicyDeniedError(
                    "sitemap URL is not configured or discoverable"
                )
            require_structured_url_in_scope(target, canonical)
        if not robots.allows(canonical):
            raise PublicWebPolicyDeniedError("robots.txt denied sitemap collection")
        response = self._transport.get(
            canonical,
            headers={
                "Accept": "application/xml,text/xml;q=0.9,*/*;q=0.1",
                "User-Agent": PUBLIC_WEB_USER_AGENT,
            },
            follow_redirects=False,
            max_bytes=self.SITEMAP_MAX_BYTES,
        )
        if response.status_code in REDIRECT_STATUSES:
            raise PublicWebResponseError("sitemap redirects are not followed")
        response.raise_for_status()
        mime_type = content_type(response)
        if mime_type not in {
            "application/xml",
            "text/xml",
            OCTET_STREAM_MIME_TYPE,
        }:
            raise PublicWebResponseError("sitemap returned an unexpected content type")
        body = bounded_body(response, max_bytes=self.SITEMAP_MAX_BYTES)
        return PublicWebFetchResult(
            requested_url=canonical,
            fetched_url=canonical,
            body=body,
            mime_type=mime_type,
            etag=header(response, "etag"),
            last_modified=header(response, "last-modified"),
            redirects=0,
            status_code=response.status_code,
            bytes_received=len(body),
        )

    def fetch_feed(
        self,
        target: PublicWebTarget,
        feed_url: str,
        robots: RobotsRules,
        *,
        discovered: bool = False,
    ) -> PublicWebFetchResult:
        canonical = CanonicalUrl(feed_url).value
        explicit = canonical in target.feed_urls
        if not explicit:
            if not discovered:
                raise PublicWebPolicyDeniedError("feed URL is not explicitly configured")
            if not target.discover_feeds:
                raise PublicWebPolicyDeniedError(
                    "feed URL is not configured or discoverable"
                )
            require_structured_url_in_scope(target, canonical)
        if not robots.allows(canonical):
            raise PublicWebPolicyDeniedError("robots.txt denied feed collection")
        response = self._transport.get(
            canonical,
            headers={
                "Accept": (
                    "application/rss+xml,application/atom+xml,"
                    "application/xml;q=0.9,text/xml;q=0.9"
                ),
                "User-Agent": PUBLIC_WEB_USER_AGENT,
            },
            follow_redirects=False,
            max_bytes=self.FEED_MAX_BYTES,
        )
        if response.status_code in REDIRECT_STATUSES:
            raise PublicWebResponseError("feed redirects are not followed")
        response.raise_for_status()
        mime_type = content_type(response)
        if mime_type not in FEED_MIME_TYPES:
            raise PublicWebResponseError("feed returned an unexpected content type")
        body = bounded_body(response, max_bytes=self.FEED_MAX_BYTES)
        return PublicWebFetchResult(
            requested_url=canonical,
            fetched_url=canonical,
            body=body,
            mime_type=mime_type,
            etag=header(response, "etag"),
            last_modified=header(response, "last-modified"),
            redirects=0,
            status_code=response.status_code,
            bytes_received=len(body),
        )

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
        requested = CanonicalUrl(url).value
        current = requested
        redirects = 0
        bytes_received = 0
        conditional_request = etag is not None or last_modified is not None
        while True:
            decision = target.crawl_scope.evaluate_target(
                current,
                depth=depth,
                redirects=redirects,
                usage=usage,
            )
            if not decision.allowed:
                raise PublicWebPolicyDeniedError(decision.reason.value)
            if not robots.allows(current):
                raise PublicWebPolicyDeniedError("robots.txt denied page collection")
            remaining_fetch_bytes = (
                target.max_total_bytes - usage.bytes_fetched - bytes_received
            )
            if remaining_fetch_bytes <= 0:
                raise PublicWebPolicyDeniedError("total_byte_budget_exceeded")
            response = self._transport.get(
                current,
                headers=page_headers(
                    include_validators=current == requested,
                    etag=etag,
                    last_modified=last_modified,
                ),
                follow_redirects=False,
                max_bytes=min(target.max_resource_bytes, remaining_fetch_bytes),
            )
            bytes_received += len(response.content)
            if response.status_code in REDIRECT_STATUSES:
                location = header(response, "location")
                if not location:
                    raise PublicWebResponseError("redirect response omitted Location")
                redirects += 1
                current = CanonicalUrl(urljoin(current, location)).value
                continue
            if response.status_code == httpx.codes.NOT_MODIFIED:
                if not conditional_request or current != requested:
                    raise PublicWebResponseError(
                        "unexpected 304 response without an applicable validator"
                    )
                return PublicWebFetchResult(
                    requested_url=requested,
                    fetched_url=current,
                    body=b"",
                    mime_type=NOT_MODIFIED_MIME_TYPE,
                    etag=header(response, "etag") or etag,
                    last_modified=header(response, "last-modified") or last_modified,
                    redirects=redirects,
                    status_code=response.status_code,
                    bytes_received=bytes_received,
                )
            if response.status_code in TOMBSTONE_STATUSES:
                return PublicWebFetchResult(
                    requested_url=requested,
                    fetched_url=current,
                    body=b"",
                    mime_type="application/x-public-resource-tombstone",
                    etag=header(response, "etag"),
                    last_modified=header(response, "last-modified"),
                    redirects=redirects,
                    status_code=response.status_code,
                    bytes_received=bytes_received,
                )
            response.raise_for_status()
            mime_type = content_type(response)
            body = bounded_body(response, max_bytes=target.max_resource_bytes)
            mime_type = normalized_page_mime(current, mime_type, body)
            response_decision = target.crawl_scope.evaluate_response(
                mime_type=mime_type,
                resource_bytes=len(body),
                usage=usage,
            )
            if not response_decision.allowed:
                raise PublicWebPolicyDeniedError(response_decision.reason.value)
            return PublicWebFetchResult(
                requested_url=requested,
                fetched_url=current,
                body=body,
                mime_type=mime_type,
                etag=header(response, "etag"),
                last_modified=header(response, "last-modified"),
                redirects=redirects,
                status_code=response.status_code,
                response_headers=bounded_evidence_headers(response.headers.multi_items()),
                bytes_received=bytes_received,
            )


__all__ = [
    "PublicWebClient",
    "PublicWebDeadlineExceededError",
    "PublicWebFetchResult",
    "PublicWebPolicyDeniedError",
    "PublicWebResponseError",
    "RobotsRules",
]
