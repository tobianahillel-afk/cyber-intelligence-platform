from __future__ import annotations

from dataclasses import dataclass

import httpx


class SourceResponseError(RuntimeError):
    """The remote source returned an unsafe or unusable response."""


@dataclass(frozen=True, slots=True)
class CisaKevCheckpoint:
    etag: str | None = None
    last_modified: str | None = None
    catalog_version: str | None = None


@dataclass(frozen=True, slots=True)
class CisaKevFetchResult:
    body: bytes | None
    etag: str | None
    last_modified: str | None
    not_modified: bool


class CisaKevClient:
    MAX_RESPONSE_BYTES = 20_000_000

    def __init__(self, client: httpx.Client, *, feed_url: str) -> None:
        self._client = client
        self._feed_url = feed_url

    def fetch(self, checkpoint: CisaKevCheckpoint | None = None) -> CisaKevFetchResult:
        headers = {"Accept": "application/json"}
        if checkpoint is not None:
            if checkpoint.etag:
                headers["If-None-Match"] = checkpoint.etag
            if checkpoint.last_modified:
                headers["If-Modified-Since"] = checkpoint.last_modified
        response = self._client.get(self._feed_url, headers=headers)
        if response.status_code == httpx.codes.NOT_MODIFIED:
            return CisaKevFetchResult(
                body=None,
                etag=response.headers.get("etag") or (checkpoint.etag if checkpoint else None),
                last_modified=response.headers.get("last-modified")
                or (checkpoint.last_modified if checkpoint else None),
                not_modified=True,
            )
        response.raise_for_status()
        _validate_content_type(response)
        _validate_size(response, max_bytes=self.MAX_RESPONSE_BYTES)
        return CisaKevFetchResult(
            body=response.content,
            etag=response.headers.get("etag"),
            last_modified=response.headers.get("last-modified"),
            not_modified=False,
        )


def _validate_content_type(response: httpx.Response) -> None:
    content_type = response.headers.get("content-type", "").split(";", maxsplit=1)[0].strip()
    if content_type not in {"application/json", "application/octet-stream"}:
        raise SourceResponseError(f"unexpected content type: {content_type or 'missing'}")


def _validate_size(response: httpx.Response, *, max_bytes: int) -> None:
    declared = response.headers.get("content-length")
    if declared is not None:
        try:
            declared_size = int(declared)
        except ValueError as exc:
            raise SourceResponseError("invalid Content-Length") from exc
        if declared_size > max_bytes:
            raise SourceResponseError("response exceeds configured size limit")
    if len(response.content) > max_bytes:
        raise SourceResponseError("response body exceeds configured size limit")
