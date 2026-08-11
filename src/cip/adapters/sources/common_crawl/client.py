from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from urllib.parse import urlsplit

import httpx
from pydantic import ValidationError

from cip.adapters.sources.common_crawl.schemas import (
    CommonCrawlCapture,
    CommonCrawlCollection,
)

MAX_RESPONSE_BYTES = 2 * 1024 * 1024
MAX_CAPTURES = 50
CAPTURE_FIELDS = (
    "timestamp",
    "url",
    "mime",
    "status",
    "digest",
    "length",
    "offset",
    "filename",
)
USER_AGENT = (
    "cyber-intelligence-platform/0.24 "
    "(+https://github.com/tobianahillel-afk/cyber-intelligence-platform)"
)


class CommonCrawlClientError(RuntimeError):
    def __init__(self, message: str, *, code: str, retryable: bool) -> None:
        super().__init__(message)
        self.code = code
        self.retryable = retryable


@dataclass(frozen=True, slots=True)
class CommonCrawlCaptureResult:
    captures: tuple[CommonCrawlCapture, ...]
    request_url: str


class CommonCrawlClient:
    def __init__(
        self,
        *,
        timeout_seconds: float = 30.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        self._timeout_seconds = timeout_seconds
        self._transport = transport

    def latest_collection(self, collection_url: str) -> CommonCrawlCollection:
        body, _ = self._get(collection_url)
        collection = max(_parse_collections(body), key=lambda item: item.to_at)
        _validate_collection_endpoint(collection)
        return collection

    def captures(
        self,
        collection: CommonCrawlCollection,
        *,
        url_pattern: str,
    ) -> CommonCrawlCaptureResult:
        params: dict[str, str | int] = {
            "url": url_pattern,
            "output": "json",
            "filter": "status:200",
            "collapse": "digest",
            "limit": MAX_CAPTURES,
            "fl": ",".join(CAPTURE_FIELDS),
        }
        body, request_url = self._get(collection.cdx_api, params=params)
        return CommonCrawlCaptureResult(
            captures=_parse_captures(body),
            request_url=request_url,
        )

    def _get(
        self,
        url: str,
        *,
        params: Mapping[str, str | int] | None = None,
    ) -> tuple[bytes, str]:
        try:
            with httpx.Client(
                timeout=self._timeout_seconds,
                follow_redirects=False,
                transport=self._transport,
                headers={"User-Agent": USER_AGENT},
            ) as client:
                response = client.get(url, params=params)
                response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            raise CommonCrawlClientError(
                f"Common Crawl returned HTTP {status}",
                code=f"http_{status}",
                retryable=status == 429 or status >= 500,
            ) from exc
        except (httpx.TimeoutException, httpx.TransportError) as exc:
            raise CommonCrawlClientError(
                str(exc) or type(exc).__name__,
                code="source_transport_error",
                retryable=True,
            ) from exc
        if len(response.content) > MAX_RESPONSE_BYTES:
            raise CommonCrawlClientError(
                "Common Crawl response exceeds size limit",
                code="unsafe_source_response",
                retryable=False,
            )
        return response.content, str(response.url)


def _parse_collections(body: bytes) -> tuple[CommonCrawlCollection, ...]:
    try:
        raw = json.loads(body)
        if not isinstance(raw, list) or not raw:
            raise ValueError("collection list must be non-empty")
        return tuple(CommonCrawlCollection.model_validate(item) for item in raw)
    except (json.JSONDecodeError, TypeError, ValueError, ValidationError) as exc:
        raise CommonCrawlClientError(
            "Common Crawl collection metadata changed",
            code="source_schema_drift",
            retryable=False,
        ) from exc


def _parse_captures(body: bytes) -> tuple[CommonCrawlCapture, ...]:
    try:
        lines = body.decode("utf-8").splitlines()[:MAX_CAPTURES]
    except UnicodeDecodeError as exc:
        raise _capture_schema_error(exc) from exc
    captures: list[CommonCrawlCapture] = []
    for line in lines:
        if not line.strip():
            continue
        try:
            captures.append(CommonCrawlCapture.model_validate(json.loads(line)))
        except (json.JSONDecodeError, ValidationError) as exc:
            raise _capture_schema_error(exc) from exc
    return tuple(captures)


def _validate_collection_endpoint(collection: CommonCrawlCollection) -> None:
    parsed = urlsplit(collection.cdx_api)
    if (
        parsed.scheme != "https"
        or parsed.hostname != "index.commoncrawl.org"
        or parsed.path != f"/{collection.id}-index"
        or parsed.query
        or parsed.fragment
    ):
        raise CommonCrawlClientError(
            "Common Crawl collection endpoint is outside approved shape",
            code="unsafe_source_response",
            retryable=False,
        )


def _capture_schema_error(exc: Exception) -> CommonCrawlClientError:
    return CommonCrawlClientError(
        "Common Crawl capture metadata changed",
        code="source_schema_drift",
        retryable=False,
    )