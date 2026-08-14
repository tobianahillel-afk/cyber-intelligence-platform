from __future__ import annotations

from contextlib import AbstractContextManager
from dataclasses import dataclass
from urllib.parse import urljoin, urlsplit
from urllib.robotparser import RobotFileParser

import httpx

from cip import __version__
from cip.adapters.sources.public_web.crawl_runtime import CrawlDeadline
from cip.adapters.sources.public_web.ooxml_parsing import (
    DOCX_MIME,
    PPTX_MIME,
    XLSX_MIME,
    detect_ooxml_mime,
)
from cip.adapters.sources.public_web.registry import PublicWebTarget
from cip.adapters.sources.public_web.response_headers import bounded_evidence_headers
from cip.modules.public_footprint.domain.scope import CrawlUsage
from cip.modules.public_footprint.domain.url_identity import CanonicalUrl, same_origin

_USER_AGENT = f"CyberIntelligencePlatform/{__version__} (+public-evidence-collector)"
_REDIRECT_STATUSES = {
    httpx.codes.MOVED_PERMANENTLY,
    httpx.codes.FOUND,
    httpx.codes.SEE_OTHER,
    httpx.codes.TEMPORARY_REDIRECT,
    httpx.codes.PERMANENT_REDIRECT,
}
_TOMBSTONE_STATUSES = {httpx.codes.NOT_FOUND, httpx.codes.GONE}
_FEED_MIME_TYPES = {
    "application/atom+xml",
    "application/rss+xml",
    "application/xml",
    "text/xml",
}
_NOT_MODIFIED_MIME_TYPE = "application/x-public-resource-not-modified"
_OCTET_STREAM_MIME_TYPE = "application/octet-stream"


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
        return self.missing or self.parser.can_fetch(_USER_AGENT, url)


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
        if request_timeout_seconds is not None and request_timeout_seconds <= 0:
            raise ValueError("request_timeout_seconds must be positive")
        self._client = client
        self._request_timeout_seconds = request_timeout_seconds
        self._deadline: CrawlDeadline | None = None

    @property
    def deadline(self) -> CrawlDeadline | None:
        return self._deadline

    @property
    def supports_concurrent_fetches(self) -> bool:
        return True

    def bind_deadline(self, deadline: CrawlDeadline) -> None:
        if self._deadline is not None and self._deadline is not deadline:
            raise ValueError("public web client is already bound to another crawl deadline")
        self._deadline = deadline

    def fetch_robots(self, target: PublicWebTarget) -> RobotsRules:
        response = self._get(
            target.robots_url,
            headers={"Accept": "text/plain", "User-Agent": _USER_AGENT},
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
        if response.status_code in _REDIRECT_STATUSES:
            raise PublicWebResponseError("robots.txt redirects are not followed")
        response.raise_for_status()
        mime_type = _content_type(response)
        if mime_type not in {"text/plain", _OCTET_STREAM_MIME_TYPE}:
            raise PublicWebResponseError("robots.txt returned an unexpected content type")
        body = _bounded_body(response, max_bytes=self.ROBOTS_MAX_BYTES)
        lines = body.decode("utf-8", errors="replace").splitlines()
        parser = RobotFileParser()
        parser.set_url(target.robots_url)
        parser.parse(lines)
        return RobotsRules(
            parser,
            target.robots_url,
            missing=False,
            bytes_fetched=len(body),
            sitemap_urls=_robots_sitemaps(lines, target, max_sitemaps=target.max_sitemaps),
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
            _require_structured_url_in_scope(target, canonical)
        if not robots.allows(canonical):
            raise PublicWebPolicyDeniedError("robots.txt denied sitemap collection")
        response = self._get(
            canonical,
            headers={
                "Accept": "application/xml,text/xml;q=0.9,*/*;q=0.1",
                "User-Agent": _USER_AGENT,
            },
            follow_redirects=False,
            max_bytes=self.SITEMAP_MAX_BYTES,
        )
        if response.status_code in _REDIRECT_STATUSES:
            raise PublicWebResponseError("sitemap redirects are not followed")
        response.raise_for_status()
        mime_type = _content_type(response)
        if mime_type not in {
            "application/xml",
            "text/xml",
            _OCTET_STREAM_MIME_TYPE,
        }:
            raise PublicWebResponseError("sitemap returned an unexpected content type")
        body = _bounded_body(response, max_bytes=self.SITEMAP_MAX_BYTES)
        return PublicWebFetchResult(
            requested_url=canonical,
            fetched_url=canonical,
            body=body,
            mime_type=mime_type,
            etag=_header(response, "etag"),
            last_modified=_header(response, "last-modified"),
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
            _require_structured_url_in_scope(target, canonical)
        if not robots.allows(canonical):
            raise PublicWebPolicyDeniedError("robots.txt denied feed collection")
        response = self._get(
            canonical,
            headers={
                "Accept": (
                    "application/rss+xml,application/atom+xml,"
                    "application/xml;q=0.9,text/xml;q=0.9"
                ),
                "User-Agent": _USER_AGENT,
            },
            follow_redirects=False,
            max_bytes=self.FEED_MAX_BYTES,
        )
        if response.status_code in _REDIRECT_STATUSES:
            raise PublicWebResponseError("feed redirects are not followed")
        response.raise_for_status()
        mime_type = _content_type(response)
        if mime_type not in _FEED_MIME_TYPES:
            raise PublicWebResponseError("feed returned an unexpected content type")
        body = _bounded_body(response, max_bytes=self.FEED_MAX_BYTES)
        return PublicWebFetchResult(
            requested_url=canonical,
            fetched_url=canonical,
            body=body,
            mime_type=mime_type,
            etag=_header(response, "etag"),
            last_modified=_header(response, "last-modified"),
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
            response = self._get(
                current,
                headers=_page_headers(
                    include_validators=current == requested,
                    etag=etag,
                    last_modified=last_modified,
                ),
                follow_redirects=False,
                max_bytes=min(target.max_resource_bytes, remaining_fetch_bytes),
            )
            bytes_received += len(response.content)
            if response.status_code in _REDIRECT_STATUSES:
                location = _header(response, "location")
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
                    mime_type=_NOT_MODIFIED_MIME_TYPE,
                    etag=_header(response, "etag") or etag,
                    last_modified=_header(response, "last-modified") or last_modified,
                    redirects=redirects,
                    status_code=response.status_code,
                    bytes_received=bytes_received,
                )
            if response.status_code in _TOMBSTONE_STATUSES:
                return PublicWebFetchResult(
                    requested_url=requested,
                    fetched_url=current,
                    body=b"",
                    mime_type="application/x-public-resource-tombstone",
                    etag=_header(response, "etag"),
                    last_modified=_header(response, "last-modified"),
                    redirects=redirects,
                    status_code=response.status_code,
                    bytes_received=bytes_received,
                )
            response.raise_for_status()
            mime_type = _content_type(response)
            body = _bounded_body(response, max_bytes=target.max_resource_bytes)
            mime_type = _normalized_page_mime(current, mime_type, body)
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
                etag=_header(response, "etag"),
                last_modified=_header(response, "last-modified"),
                redirects=redirects,
                status_code=response.status_code,
                response_headers=bounded_evidence_headers(response.headers.multi_items()),
                bytes_received=bytes_received,
            )

    def _get(
        self,
        url: str,
        *,
        headers: dict[str, str],
        follow_redirects: bool,
        max_bytes: int,
    ) -> httpx.Response:
        timeout = self._effective_timeout()
        try:
            with self._open_stream(
                url,
                headers=headers,
                follow_redirects=follow_redirects,
                timeout=timeout,
            ) as response:
                _validate_declared_length(response, max_bytes=max_bytes)
                body = bytearray()
                self._require_deadline()
                for chunk in response.iter_bytes():
                    body.extend(chunk)
                    if len(body) > max_bytes:
                        raise PublicWebResponseError(
                            "response body exceeds configured size limit"
                        )
                    self._require_deadline()
                return httpx.Response(
                    status_code=response.status_code,
                    headers=response.headers,
                    content=bytes(body),
                    request=response.request,
                )
        except httpx.TimeoutException as exc:
            if self._deadline is not None and self._deadline.exceeded:
                raise PublicWebDeadlineExceededError("whole-crawl deadline exceeded") from exc
            raise

    def _effective_timeout(self) -> float | None:
        timeout = self._request_timeout_seconds
        if self._deadline is None:
            return timeout
        remaining = self._deadline.remaining_seconds
        if remaining <= 0:
            raise PublicWebDeadlineExceededError("whole-crawl deadline exceeded")
        return remaining if timeout is None else min(timeout, remaining)

    def _require_deadline(self) -> None:
        if self._deadline is not None and self._deadline.exceeded:
            raise PublicWebDeadlineExceededError("whole-crawl deadline exceeded")

    def _open_stream(
        self,
        url: str,
        *,
        headers: dict[str, str],
        follow_redirects: bool,
        timeout: float | None,
    ) -> AbstractContextManager[httpx.Response]:
        if timeout is None:
            return self._client.stream(
                "GET",
                url,
                headers=headers,
                follow_redirects=follow_redirects,
            )
        return self._client.stream(
            "GET",
            url,
            headers=headers,
            follow_redirects=follow_redirects,
            timeout=timeout,
        )


def _page_headers(
    *,
    include_validators: bool,
    etag: str | None,
    last_modified: str | None,
) -> dict[str, str]:
    headers = {
        "Accept": (
            "text/html,application/pdf,text/plain,"
            f"{DOCX_MIME},{XLSX_MIME},{PPTX_MIME};q=0.9,*/*;q=0.1"
        ),
        "User-Agent": _USER_AGENT,
    }
    if include_validators and etag is not None:
        headers["If-None-Match"] = etag
    if include_validators and last_modified is not None:
        headers["If-Modified-Since"] = last_modified
    return headers


def _normalized_page_mime(url: str, mime_type: str, body: bytes) -> str:
    if mime_type != _OCTET_STREAM_MIME_TYPE:
        return mime_type
    detected = detect_ooxml_mime(body, url_path=urlsplit(url).path)
    return detected or mime_type


def _robots_sitemaps(
    lines: list[str],
    target: PublicWebTarget,
    *,
    max_sitemaps: int,
) -> tuple[str, ...]:
    if not target.discover_sitemaps:
        return ()
    discovered: list[str] = []
    seen: set[str] = set()
    for line in lines:
        key, separator, value = line.partition(":")
        if not separator or key.strip().casefold() != "sitemap":
            continue
        try:
            canonical = CanonicalUrl(value.strip()).value
        except ValueError:
            continue
        if not same_origin(target.base_url, canonical) or canonical in seen:
            continue
        try:
            _require_structured_url_in_scope(target, canonical)
        except PublicWebPolicyDeniedError:
            continue
        seen.add(canonical)
        discovered.append(canonical)
        if len(discovered) >= max_sitemaps:
            break
    return tuple(discovered)


def _require_structured_url_in_scope(target: PublicWebTarget, url: str) -> None:
    decision = target.crawl_scope.evaluate_target(
        url,
        depth=0,
        redirects=0,
        usage=CrawlUsage(),
    )
    if not decision.allowed:
        raise PublicWebPolicyDeniedError(decision.reason.value)


def _header(response: httpx.Response, name: str) -> str | None:
    value = response.headers.get(name)
    return str(value) if value is not None else None


def _content_type(response: httpx.Response) -> str:
    value = _header(response, "content-type") or ""
    return value.split(";", 1)[0].strip().casefold()


def _validate_declared_length(response: httpx.Response, *, max_bytes: int) -> None:
    declared = _header(response, "content-length")
    if declared is None:
        return
    try:
        declared_size = int(declared)
    except ValueError as exc:
        raise PublicWebResponseError("invalid Content-Length") from exc
    if declared_size < 0 or declared_size > max_bytes:
        raise PublicWebResponseError("response exceeds configured size limit")


def _bounded_body(response: httpx.Response, *, max_bytes: int) -> bytes:
    _validate_declared_length(response, max_bytes=max_bytes)
    body = response.content
    if len(body) > max_bytes:
        raise PublicWebResponseError("response body exceeds configured size limit")
    return body
