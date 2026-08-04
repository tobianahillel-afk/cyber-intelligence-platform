from __future__ import annotations

from dataclasses import dataclass

import httpx


class BodaccIdentitySourceResponseError(RuntimeError):
    """BODACC returned an unsafe or unusable identity response."""


@dataclass(frozen=True, slots=True)
class BodaccIdentityFetchResult:
    body: bytes
    request_url: str


class BodaccIdentityClient:
    MAX_RESPONSE_BYTES = 5_000_000
    SELECT_FIELDS = (
        "id",
        "dateparution",
        "typeavis",
        "typeavis_lib",
        "familleavis",
        "familleavis_lib",
        "commercant",
        "ville",
        "registre",
        "cp",
        "modificationsgenerales",
        "radiationaurcs",
        "url_complete",
    )

    def __init__(self, client: httpx.Client, *, records_url: str) -> None:
        self._client = client
        self._records_url = records_url.rstrip("/")

    @property
    def records_url(self) -> str:
        return self._records_url

    def fetch_announcements(
        self,
        siren: str,
        *,
        limit: int = 100,
    ) -> BodaccIdentityFetchResult:
        if len(siren) != 9 or not siren.isdigit():
            raise ValueError("siren must contain exactly 9 digits")
        if not 1 <= limit <= 100:
            raise ValueError("limit must be between 1 and 100")
        response = self._client.get(
            self._records_url,
            headers={"Accept": "application/json"},
            params={
                "select": ",".join(self.SELECT_FIELDS),
                "where": f'search(registre, "{siren}")',
                "order_by": "dateparution desc,id desc",
                "limit": limit,
                "offset": 0,
            },
        )
        response.raise_for_status()
        _validate_json_response(response, max_bytes=self.MAX_RESPONSE_BYTES)
        return BodaccIdentityFetchResult(
            body=response.content,
            request_url=str(response.request.url),
        )


def _validate_json_response(response: httpx.Response, *, max_bytes: int) -> None:
    content_type = response.headers.get("content-type", "").split(";", maxsplit=1)[0].strip()
    if content_type != "application/json":
        raise BodaccIdentitySourceResponseError(
            f"unexpected content type: {content_type or 'missing'}"
        )
    declared = response.headers.get("content-length")
    if declared is not None:
        try:
            declared_size = int(declared)
        except ValueError as exc:
            raise BodaccIdentitySourceResponseError("invalid Content-Length") from exc
        if declared_size > max_bytes:
            raise BodaccIdentitySourceResponseError(
                "response exceeds configured size limit"
            )
    if len(response.content) > max_bytes:
        raise BodaccIdentitySourceResponseError(
            "response body exceeds configured size limit"
        )
