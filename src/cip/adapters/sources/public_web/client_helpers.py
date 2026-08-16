from __future__ import annotations

from urllib.parse import urlsplit

import httpx

from cip.adapters.sources.public_web.client_contract import (
    OCTET_STREAM_MIME_TYPE,
    PUBLIC_WEB_USER_AGENT,
    PublicWebPolicyDeniedError,
    PublicWebResponseError,
)
from cip.adapters.sources.public_web.ooxml_parsing import (
    DOCX_MIME,
    PPTX_MIME,
    XLSX_MIME,
    detect_ooxml_mime,
)
from cip.adapters.sources.public_web.registry import PublicWebTarget
from cip.modules.public_footprint.domain.scope import CrawlUsage
from cip.modules.public_footprint.domain.url_identity import CanonicalUrl, same_origin


def page_headers(
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
        "User-Agent": PUBLIC_WEB_USER_AGENT,
    }
    if include_validators and etag is not None:
        headers["If-None-Match"] = etag
    if include_validators and last_modified is not None:
        headers["If-Modified-Since"] = last_modified
    return headers


def normalized_page_mime(url: str, mime_type: str, body: bytes) -> str:
    if mime_type != OCTET_STREAM_MIME_TYPE:
        return mime_type
    detected = detect_ooxml_mime(body, url_path=urlsplit(url).path)
    return detected or mime_type


def robots_sitemaps(
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
            require_structured_url_in_scope(target, canonical)
        except PublicWebPolicyDeniedError:
            continue
        seen.add(canonical)
        discovered.append(canonical)
        if len(discovered) >= max_sitemaps:
            break
    return tuple(discovered)


def require_structured_url_in_scope(target: PublicWebTarget, url: str) -> None:
    decision = target.crawl_scope.evaluate_target(
        url,
        depth=0,
        redirects=0,
        usage=CrawlUsage(),
    )
    if not decision.allowed:
        raise PublicWebPolicyDeniedError(decision.reason.value)


def header(response: httpx.Response, name: str) -> str | None:
    value = response.headers.get(name)
    return str(value) if value is not None else None


def content_type(response: httpx.Response) -> str:
    value = header(response, "content-type") or ""
    return value.split(";", 1)[0].strip().casefold()


def bounded_body(response: httpx.Response, *, max_bytes: int) -> bytes:
    declared = header(response, "content-length")
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
