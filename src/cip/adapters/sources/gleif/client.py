from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import quote

import httpx


class GleifSourceResponseError(RuntimeError):
    """GLEIF returned an unsafe or unusable response."""


@dataclass(frozen=True, slots=True)
class GleifFetchResult:
    body: bytes
    request_url: str


class GleifClient:
    MAX_RESPONSE_BYTES = 3_000_000

    def __init__(self, client: httpx.Client, *, api_base_url: str) -> None:
        self._client = client
        self._api_base_url = api_base_url.rstrip("/")

    def record_url(self, lei: str) -> str:
        return f"{self._api_base_url}/lei-records/{quote(lei, safe='')}"

    def relationship_url(self, lei: str, relationship: str) -> str:
        if relationship not in {"direct-parent", "ultimate-parent"}:
            raise ValueError("unsupported GLEIF relationship")
        return f"{self.record_url(lei)}/{relationship}-relationship"

    def fetch_record(self, lei: str) -> GleifFetchResult:
        result = self._get_json(self.record_url(lei), allow_not_found=False)
        if result is None:
            raise GleifSourceResponseError("GLEIF record unexpectedly returned no data")
        return result

    def fetch_relationship(
        self,
        lei: str,
        relationship: str,
    ) -> GleifFetchResult | None:
        return self._get_json(
            self.relationship_url(lei, relationship),
            allow_not_found=True,
        )

    def _get_json(self, url: str, *, allow_not_found: bool) -> GleifFetchResult | None:
        response = self._client.get(
            url,
            headers={"Accept": "application/vnd.api+json, application/json"},
        )
        if allow_not_found and response.status_code == 404:
            return None
        response.raise_for_status()
        _validate_json_response(response, max_bytes=self.MAX_RESPONSE_BYTES)
        return GleifFetchResult(body=response.content, request_url=str(response.request.url))


def _validate_json_response(response: httpx.Response, *, max_bytes: int) -> None:
    content_type = response.headers.get("content-type", "").split(";", maxsplit=1)[0].strip()
    if content_type not in {"application/json", "application/vnd.api+json"}:
        raise GleifSourceResponseError(
            f"unexpected content type: {content_type or 'missing'}"
        )
    declared = response.headers.get("content-length")
    if declared is not None:
        try:
            declared_size = int(declared)
        except ValueError as exc:
            raise GleifSourceResponseError("invalid Content-Length") from exc
        if declared_size > max_bytes:
            raise GleifSourceResponseError("response exceeds configured size limit")
    if len(response.content) > max_bytes:
        raise GleifSourceResponseError("response body exceeds configured size limit")
