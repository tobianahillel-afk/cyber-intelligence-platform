from __future__ import annotations

from dataclasses import dataclass

import httpx


class TeamtailorSourceResponseError(RuntimeError):
    """Teamtailor returned an unsafe or unusable public-jobs response."""


@dataclass(frozen=True, slots=True)
class TeamtailorFetchResult:
    body: bytes
    request_url: str


class TeamtailorClient:
    MAX_RESPONSE_BYTES = 8_000_000

    def __init__(self, client: httpx.Client) -> None:
        self._client = client

    def fetch_jobs_page(
        self,
        url: str,
        *,
        api_token: str,
        api_version: str,
        page_size: int = 30,
    ) -> TeamtailorFetchResult:
        if not api_token.strip():
            raise ValueError("api_token is required")
        if not 1 <= page_size <= 30:
            raise ValueError("page_size must be between 1 and 30")
        response = self._client.get(
            url,
            headers={
                "Accept": "application/vnd.api+json, application/json",
                "Authorization": f"Token token={api_token}",
                "X-Api-Version": api_version,
            },
            params={"include": "department,locations", "page[size]": page_size}
            if "?" not in url
            else None,
        )
        response.raise_for_status()
        _validate_content_type(response)
        _validate_size(response, max_bytes=self.MAX_RESPONSE_BYTES)
        return TeamtailorFetchResult(
            body=response.content,
            request_url=str(response.request.url),
        )


def _validate_content_type(response: httpx.Response) -> None:
    content_type = response.headers.get("content-type", "").split(";", maxsplit=1)[0].strip()
    if content_type not in {"application/vnd.api+json", "application/json"}:
        raise TeamtailorSourceResponseError(
            f"unexpected content type: {content_type or 'missing'}"
        )


def _validate_size(response: httpx.Response, *, max_bytes: int) -> None:
    declared = response.headers.get("content-length")
    if declared is not None:
        try:
            declared_size = int(declared)
        except ValueError as exc:
            raise TeamtailorSourceResponseError("invalid Content-Length") from exc
        if declared_size > max_bytes:
            raise TeamtailorSourceResponseError("response exceeds configured size limit")
    if len(response.content) > max_bytes:
        raise TeamtailorSourceResponseError("response body exceeds configured size limit")
