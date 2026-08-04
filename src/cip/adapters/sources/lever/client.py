from __future__ import annotations

from dataclasses import dataclass

import httpx


class LeverSourceResponseError(RuntimeError):
    """Lever returned an unsafe or unusable response."""


@dataclass(frozen=True, slots=True)
class LeverFetchResult:
    body: bytes
    request_url: str


class LeverClient:
    MAX_RESPONSE_BYTES = 5_000_000

    def __init__(self, client: httpx.Client, *, postings_base_url: str) -> None:
        self._client = client
        self._postings_base_url = postings_base_url.rstrip("/")

    def postings_url(self, site_token: str) -> str:
        return f"{self._postings_base_url}/{site_token}"

    def fetch_postings(
        self,
        site_token: str,
        *,
        skip: int,
        limit: int,
    ) -> LeverFetchResult:
        if skip < 0:
            raise ValueError("skip must not be negative")
        if not 1 <= limit <= 100:
            raise ValueError("limit must be between 1 and 100")
        url = self.postings_url(site_token)
        response = self._client.get(
            url,
            headers={"Accept": "application/json"},
            params={"mode": "json", "skip": skip, "limit": limit},
        )
        response.raise_for_status()
        _validate_content_type(response)
        _validate_size(response, max_bytes=self.MAX_RESPONSE_BYTES)
        return LeverFetchResult(body=response.content, request_url=str(response.request.url))


def _validate_content_type(response: httpx.Response) -> None:
    content_type = response.headers.get("content-type", "").split(";", maxsplit=1)[0].strip()
    if content_type != "application/json":
        raise LeverSourceResponseError(
            f"unexpected content type: {content_type or 'missing'}"
        )


def _validate_size(response: httpx.Response, *, max_bytes: int) -> None:
    declared = response.headers.get("content-length")
    if declared is not None:
        try:
            declared_size = int(declared)
        except ValueError as exc:
            raise LeverSourceResponseError("invalid Content-Length") from exc
        if declared_size > max_bytes:
            raise LeverSourceResponseError("response exceeds configured size limit")
    if len(response.content) > max_bytes:
        raise LeverSourceResponseError("response body exceeds configured size limit")
