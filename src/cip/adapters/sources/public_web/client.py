from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urljoin
from urllib.robotparser import RobotFileParser

import httpx

from cip.adapters.sources.public_web.registry import PublicWebTarget
from cip.modules.public_footprint.domain.scope import CrawlUsage
from cip.modules.public_footprint.domain.url_identity import CanonicalUrl

_USER_AGENT = "CyberIntelligencePlatform/0.12 (+public-evidence-collector)"
_REDIRECT_STATUSES = {
    httpx.codes.MOVED_PERMANENTLY,
    httpx.codes.FOUND,
    httpx.codes.SEE_OTHER,
    httpx.codes.TEMPORARY_REDIRECT,
    httpx.codes.PERMANENT_REDIRECT,
}


class PublicWebResponseError(RuntimeError):
    """A public-web response violated the configured safety contract."""


class PublicWebPolicyDeniedError(RuntimeError):
    """Robots or target scope denied a public-web request."""


@dataclass(frozen=True, slots=True)
class PublicWebFetchResult:
    requested_url: str
    fetched_url: str
    body: bytes
    mime_type: str
    etag: str | None
    last_modified: str | None
    redirects: int


@dataclass(frozen=True, slots=True)
class RobotsRules:
    parser: RobotFileParser
    source_url: str
    missing: bool
    bytes_fetched: int

    def allows(self, url: str) -> bool:
        return self.missing or self.parser.can_fetch(_USER_AGENT, url)


class PublicWebClient:
    ROBOTS_MAX_BYTES = 256_000
    SITEMAP_MAX_BYTES = 1_000_000

    def __init__(self, client: httpx.Client) -> None:
        self._client = client

    def fetch_robots(self, target: PublicWebTarget) -> RobotsRules:
        response = self._client.get(
            target.robots_url,
            headers={"Accept": "text/plain", "User-Agent": _USER_AGENT},
            follow_redirects=False,
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
        if mime_type not in {"text/plain", "application/octet-stream"}:
            raise PublicWebResponseError("robots.txt returned an unexpected content type")
        body = _bounded_body(response, max_bytes=self.ROBOTS_MAX_BYTES)
        parser = RobotFileParser()
        parser.set_url(target.robots_url)
        parser.parse(body.decode("utf-8", errors="replace").splitlines())
        return RobotsRules(
            parser,
            target.robots_url,
            missing=False,
            bytes_fetched=len(body),
        )

    def fetch_sitemap(
        self,
        target: PublicWebTarget,
        sitemap_url: str,
        robots: RobotsRules,
    ) -> PublicWebFetchResult:
        canonical = CanonicalUrl(sitemap_url).value
        if canonical not in target.sitemap_urls:
            raise PublicWebPolicyDeniedError("sitemap URL is not explicitly configured")
        if not robots.allows(canonical):
            raise PublicWebPolicyDeniedError("robots.txt denied sitemap collection")
        response = self._client.get(
            canonical,
            headers={
                "Accept": "application/xml,text/xml;q=0.9,*/*;q=0.1",
                "User-Agent": _USER_AGENT,
            },
            follow_redirects=False,
        )
        if response.status_code in _REDIRECT_STATUSES:
            raise PublicWebResponseError("sitemap redirects are not followed")
        response.raise_for_status()
        mime_type = _content_type(response)
        if mime_type not in {
            "application/xml",
            "text/xml",
            "application/octet-stream",
        }:
            raise PublicWebResponseError("sitemap returned an unexpected content type")
        return PublicWebFetchResult(
            requested_url=canonical,
            fetched_url=canonical,
            body=_bounded_body(response, max_bytes=self.SITEMAP_MAX_BYTES),
            mime_type=mime_type,
            etag=_header(response, "etag"),
            last_modified=_header(response, "last-modified"),
            redirects=0,
        )

    def fetch_page(
        self,
        target: PublicWebTarget,
        url: str,
        robots: RobotsRules,
        *,
        usage: CrawlUsage,
    ) -> PublicWebFetchResult:
        requested = CanonicalUrl(url).value
        current = requested
        redirects = 0
        while True:
            decision = target.crawl_scope.evaluate_target(
                current,
                depth=0,
                redirects=redirects,
                usage=usage,
            )
            if not decision.allowed:
                raise PublicWebPolicyDeniedError(decision.reason.value)
            if not robots.allows(current):
                raise PublicWebPolicyDeniedError("robots.txt denied page collection")
            response = self._client.get(
                current,
                headers={
                    "Accept": "text/html,application/pdf,text/plain;q=0.9,*/*;q=0.1",
                    "User-Agent": _USER_AGENT,
                },
                follow_redirects=False,
            )
            if response.status_code in _REDIRECT_STATUSES:
                location = _header(response, "location")
                if not location:
                    raise PublicWebResponseError("redirect response omitted Location")
                redirects += 1
                current = CanonicalUrl(urljoin(current, location)).value
                continue
            response.raise_for_status()
            mime_type = _content_type(response)
            body = _bounded_body(response, max_bytes=target.max_resource_bytes)
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
            )


def _header(response: httpx.Response, name: str) -> str | None:
    value = response.headers.get(name)
    return str(value) if value is not None else None


def _content_type(response: httpx.Response) -> str:
    value = _header(response, "content-type") or ""
    return value.split(";", 1)[0].strip().casefold()


def _bounded_body(response: httpx.Response, *, max_bytes: int) -> bytes:
    declared = _header(response, "content-length")
    if declared is not None:
        try:
            declared_size = int(declared)
        except ValueError as exc:
            raise PublicWebResponseError("invalid Content-Length") from exc
        if declared_size < 0 or declared_size > max_bytes:
            raise PublicWebResponseError("response exceeds configured size limit")
    body = response.content
    if len(body) > max_bytes:
        raise PublicWebResponseError("response body exceeds configured size limit")
    return body
