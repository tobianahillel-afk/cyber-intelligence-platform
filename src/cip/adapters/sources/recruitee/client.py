from __future__ import annotations

from dataclasses import dataclass

import httpx


class RecruiteeSourceResponseError(RuntimeError):
    """Recruitee returned an unsafe or unusable careers response."""


@dataclass(frozen=True, slots=True)
class RecruiteeFetchResult:
    body: bytes
    request_url: str


class RecruiteeClient:
    MAX_RESPONSE_BYTES = 8_000_000

    def __init__(self, client: httpx.Client) -> None:
        self._client = client

    def fetch_offers(self, offers_url: str) -> RecruiteeFetchResult:
        response = self._client.get(
            offers_url,
            headers={"Accept": "application/json"},
        )
        response.raise_for_status()
        _validate_content_type(response)
        _validate_size(response, max_bytes=self.MAX_RESPONSE_BYTES)
        return RecruiteeFetchResult(
            body=response.content,
            request_url=str(response.request.url),
        )


def _validate_content_type(response: httpx.Response) -> None:
    content_type = response.headers.get("content-type", "").split(";", maxsplit=1)[0].strip()
    if content_type != "application/json":
        raise RecruiteeSourceResponseError(
            f"unexpected content type: {content_type or 'missing'}"
        )


def _validate_size(response: httpx.Response, *, max_bytes: int) -> None:
    declared = response.headers.get("content-length")
    if declared is not None:
        try:
            declared_size = int(declared)
        except ValueError as exc:
            raise RecruiteeSourceResponseError("invalid Content-Length") from exc
        if declared_size > max_bytes:
            raise RecruiteeSourceResponseError("response exceeds configured size limit")
    if len(response.content) > max_bytes:
        raise RecruiteeSourceResponseError("response body exceeds configured size limit")
