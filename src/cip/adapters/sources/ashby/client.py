from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import quote

import httpx


class AshbySourceResponseError(RuntimeError):
    """Ashby returned an unsafe or unusable public job-board response."""


@dataclass(frozen=True, slots=True)
class AshbyFetchResult:
    body: bytes
    request_url: str


class AshbyClient:
    MAX_RESPONSE_BYTES = 8_000_000

    def __init__(self, client: httpx.Client, *, postings_base_url: str) -> None:
        self._client = client
        self._postings_base_url = postings_base_url.rstrip("/")

    def board_url(self, board_name: str) -> str:
        normalized = board_name.strip()
        if not normalized:
            raise ValueError("board_name is required")
        return f"{self._postings_base_url}/{quote(normalized, safe='')}"

    def fetch_jobs(self, board_name: str) -> AshbyFetchResult:
        url = self.board_url(board_name)
        response = self._client.get(
            url,
            headers={"Accept": "application/json"},
            params={"includeCompensation": "false"},
        )
        response.raise_for_status()
        _validate_content_type(response)
        _validate_size(response, max_bytes=self.MAX_RESPONSE_BYTES)
        return AshbyFetchResult(body=response.content, request_url=str(response.request.url))


def _validate_content_type(response: httpx.Response) -> None:
    content_type = response.headers.get("content-type", "").split(";", maxsplit=1)[0].strip()
    if content_type != "application/json":
        raise AshbySourceResponseError(
            f"unexpected content type: {content_type or 'missing'}"
        )


def _validate_size(response: httpx.Response, *, max_bytes: int) -> None:
    declared = response.headers.get("content-length")
    if declared is not None:
        try:
            declared_size = int(declared)
        except ValueError as exc:
            raise AshbySourceResponseError("invalid Content-Length") from exc
        if declared_size > max_bytes:
            raise AshbySourceResponseError("response exceeds configured size limit")
    if len(response.content) > max_bytes:
        raise AshbySourceResponseError("response body exceeds configured size limit")
