from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlencode

import httpx


class AdemeFundingResponseError(RuntimeError):
    """ADEME Data Fair returned an unsafe or unusable response."""


@dataclass(frozen=True, slots=True)
class AdemeFundingFetchResult:
    body: bytes
    request_url: str


class AdemeFundingClient:
    PAGE_SIZE = 100
    MAX_RESPONSE_BYTES = 5_000_000
    SELECT_FIELDS = (
        "_id",
        "nomBeneficiaire",
        "objet",
        "nature",
        "dateConvention",
        "montant",
    )

    def __init__(self, client: httpx.Client, *, lines_url: str) -> None:
        self._client = client
        self._lines_url = lines_url.rstrip("/")

    def first_page_url(self) -> str:
        query = urlencode(
            {
                "select": ",".join(self.SELECT_FIELDS),
                "size": self.PAGE_SIZE,
            }
        )
        return f"{self._lines_url}?{query}"

    def fetch_url(self, url: str) -> AdemeFundingFetchResult:
        response = self._client.get(url, headers={"Accept": "application/json"})
        response.raise_for_status()
        _validate_content_type(response)
        _validate_size(response, max_bytes=self.MAX_RESPONSE_BYTES)
        return AdemeFundingFetchResult(body=response.content, request_url=str(response.url))


def _validate_content_type(response: httpx.Response) -> None:
    content_type = response.headers.get("content-type", "").split(";", maxsplit=1)[0].strip()
    if content_type != "application/json":
        raise AdemeFundingResponseError(
            f"unexpected content type: {content_type or 'missing'}"
        )


def _validate_size(response: httpx.Response, *, max_bytes: int) -> None:
    declared = response.headers.get("content-length")
    if declared is not None:
        try:
            declared_size = int(declared)
        except ValueError as exc:
            raise AdemeFundingResponseError("invalid Content-Length") from exc
        if declared_size > max_bytes:
            raise AdemeFundingResponseError("response exceeds configured size limit")
    if len(response.content) > max_bytes:
        raise AdemeFundingResponseError("response body exceeds configured size limit")
