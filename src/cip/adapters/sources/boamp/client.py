from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import httpx


class BoampSourceResponseError(RuntimeError):
    """BOAMP returned an unsafe or unusable response."""


@dataclass(frozen=True, slots=True)
class BoampCheckpoint:
    latest_idweb: str | None = None
    latest_publication_date: str | None = None


@dataclass(frozen=True, slots=True)
class BoampFetchResult:
    body: bytes


class BoampClient:
    MAX_RESPONSE_BYTES = 5_000_000
    PAGE_SIZE = 100
    SELECT_FIELDS = (
        "idweb",
        "objet",
        "dateparution",
        "datelimitereponse",
        "nomacheteur",
        "etat",
        "nature_libelle",
        "type_avis",
        "descripteur_libelle",
        "type_marche",
        "titulaire",
        "url_avis",
    )

    def __init__(self, client: httpx.Client, *, records_url: str) -> None:
        self._client = client
        self._records_url = records_url

    def fetch_page(self, *, since_date: date, offset: int) -> BoampFetchResult:
        if offset < 0:
            raise ValueError("offset cannot be negative")
        response = self._client.get(
            self._records_url,
            headers={"Accept": "application/json"},
            params={
                "select": ",".join(self.SELECT_FIELDS),
                "where": f"dateparution >= date'{since_date.isoformat()}'",
                "order_by": "dateparution desc,idweb desc",
                "limit": self.PAGE_SIZE,
                "offset": offset,
            },
        )
        response.raise_for_status()
        _validate_content_type(response)
        _validate_size(response, max_bytes=self.MAX_RESPONSE_BYTES)
        return BoampFetchResult(body=response.content)


def _validate_content_type(response: httpx.Response) -> None:
    content_type = response.headers.get("content-type", "").split(";", maxsplit=1)[0].strip()
    if content_type != "application/json":
        raise BoampSourceResponseError(
            f"unexpected content type: {content_type or 'missing'}"
        )


def _validate_size(response: httpx.Response, *, max_bytes: int) -> None:
    declared = response.headers.get("content-length")
    if declared is not None:
        try:
            declared_size = int(declared)
        except ValueError as exc:
            raise BoampSourceResponseError("invalid Content-Length") from exc
        if declared_size > max_bytes:
            raise BoampSourceResponseError("response exceeds configured size limit")
    if len(response.content) > max_bytes:
        raise BoampSourceResponseError("response body exceeds configured size limit")
