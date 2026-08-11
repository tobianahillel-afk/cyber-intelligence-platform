from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import quote

import httpx


class BrregSourceResponseError(RuntimeError):
    """BRREG returned an unsafe or unusable response."""


class BrregEntityRemovedError(RuntimeError):
    """BRREG reports that an entity was removed from public disclosure."""


@dataclass(frozen=True, slots=True)
class BrregFetchResult:
    body: bytes
    request_url: str


class BrregIdentityClient:
    MAX_RESPONSE_BYTES = 1_000_000
    ACCEPT = "application/vnd.brreg.enhetsregisteret.enhet.v2+json"

    def __init__(self, client: httpx.Client, *, entities_url: str) -> None:
        self._client = client
        self._entities_url = entities_url.rstrip("/")

    def entity_url(self, registration_number: str) -> str:
        normalized = "".join(character for character in registration_number if character.isdigit())
        if len(normalized) != 9:
            raise ValueError("BRREG organisation number must contain 9 digits")
        return f"{self._entities_url}/{quote(normalized, safe='')}"

    def fetch_entity(self, registration_number: str) -> BrregFetchResult:
        url = self.entity_url(registration_number)
        response = self._client.get(url, headers={"Accept": self.ACCEPT})
        if response.status_code == 410:
            raise BrregEntityRemovedError("BRREG entity removed from public disclosure")
        response.raise_for_status()
        _validate_content_type(response)
        _validate_size(response, max_bytes=self.MAX_RESPONSE_BYTES)
        return BrregFetchResult(body=response.content, request_url=str(response.url))


def _validate_content_type(response: httpx.Response) -> None:
    content_type = response.headers.get("content-type", "").split(";", maxsplit=1)[0].strip()
    allowed = {
        "application/json",
        "application/vnd.brreg.enhetsregisteret.enhet.v2+json",
    }
    if content_type not in allowed:
        raise BrregSourceResponseError(
            f"unexpected content type: {content_type or 'missing'}"
        )


def _validate_size(response: httpx.Response, *, max_bytes: int) -> None:
    declared = response.headers.get("content-length")
    if declared is not None:
        try:
            declared_size = int(declared)
        except ValueError as exc:
            raise BrregSourceResponseError("invalid Content-Length") from exc
        if declared_size > max_bytes:
            raise BrregSourceResponseError("response exceeds configured size limit")
    if len(response.content) > max_bytes:
        raise BrregSourceResponseError("response body exceeds configured size limit")
