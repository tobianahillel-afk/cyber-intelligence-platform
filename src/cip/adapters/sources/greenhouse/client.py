from __future__ import annotations

from dataclasses import dataclass

import httpx


class GreenhouseSourceResponseError(RuntimeError):
    """Greenhouse returned an unsafe or unusable response."""


@dataclass(frozen=True, slots=True)
class GreenhouseFetchResult:
    body: bytes
    request_url: str


class GreenhouseClient:
    MAX_RESPONSE_BYTES = 5_000_000

    def __init__(self, client: httpx.Client, *, boards_base_url: str) -> None:
        self._client = client
        self._boards_base_url = boards_base_url.rstrip("/")

    def jobs_url(self, board_token: str) -> str:
        return f"{self._boards_base_url}/{board_token}/jobs"

    def fetch_jobs(self, board_token: str) -> GreenhouseFetchResult:
        url = self.jobs_url(board_token)
        response = self._client.get(
            url,
            headers={"Accept": "application/json"},
            params={"content": "true"},
        )
        response.raise_for_status()
        _validate_content_type(response)
        _validate_size(response, max_bytes=self.MAX_RESPONSE_BYTES)
        return GreenhouseFetchResult(body=response.content, request_url=str(response.request.url))


def _validate_content_type(response: httpx.Response) -> None:
    content_type = response.headers.get("content-type", "").split(";", maxsplit=1)[0].strip()
    if content_type != "application/json":
        raise GreenhouseSourceResponseError(
            f"unexpected content type: {content_type or 'missing'}"
        )


def _validate_size(response: httpx.Response, *, max_bytes: int) -> None:
    declared = response.headers.get("content-length")
    if declared is not None:
        try:
            declared_size = int(declared)
        except ValueError as exc:
            raise GreenhouseSourceResponseError("invalid Content-Length") from exc
        if declared_size > max_bytes:
            raise GreenhouseSourceResponseError("response exceeds configured size limit")
    if len(response.content) > max_bytes:
        raise GreenhouseSourceResponseError("response body exceeds configured size limit")
