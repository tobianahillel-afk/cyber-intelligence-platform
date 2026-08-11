from __future__ import annotations

from dataclasses import dataclass

import httpx


class CordisFundingResponseError(RuntimeError):
    """CORDIS returned an unsafe or unusable bulk response."""


@dataclass(frozen=True, slots=True)
class CordisFundingFetchResult:
    body: bytes
    request_url: str
    etag: str | None
    last_modified: str | None


class CordisFundingClient:
    MAX_RESPONSE_BYTES = 100_000_000

    def __init__(self, client: httpx.Client, *, archive_url: str) -> None:
        self._client = client
        self._archive_url = archive_url

    @property
    def archive_url(self) -> str:
        return self._archive_url

    def fetch(self) -> CordisFundingFetchResult:
        response = self._client.get(
            self._archive_url,
            headers={"Accept": "application/zip, application/octet-stream"},
        )
        response.raise_for_status()
        _validate_content_type(response)
        _validate_size(response, max_bytes=self.MAX_RESPONSE_BYTES)
        return CordisFundingFetchResult(
            body=response.content,
            request_url=str(response.url),
            etag=response.headers.get("etag"),
            last_modified=response.headers.get("last-modified"),
        )


def _validate_content_type(response: httpx.Response) -> None:
    content_type = response.headers.get("content-type", "").split(";", maxsplit=1)[0].strip()
    accepted = {"application/zip", "application/octet-stream"}
    if content_type not in accepted:
        raise CordisFundingResponseError(
            f"unexpected content type: {content_type or 'missing'}"
        )


def _validate_size(response: httpx.Response, *, max_bytes: int) -> None:
    declared = response.headers.get("content-length")
    if declared is not None:
        try:
            declared_size = int(declared)
        except ValueError as exc:
            raise CordisFundingResponseError("invalid Content-Length") from exc
        if declared_size > max_bytes:
            raise CordisFundingResponseError("response exceeds configured size limit")
    if len(response.content) > max_bytes:
        raise CordisFundingResponseError("response body exceeds configured size limit")
