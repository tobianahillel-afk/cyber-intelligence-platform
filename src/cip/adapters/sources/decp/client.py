from __future__ import annotations

from dataclasses import dataclass

import httpx


class DecpSourceResponseError(RuntimeError):
    """DECP returned an unsafe or unusable response."""


@dataclass(frozen=True, slots=True)
class DecpCheckpoint:
    latest_revision_key: str | None = None
    latest_publication_date: str | None = None


@dataclass(frozen=True, slots=True)
class DecpFetchResult:
    body: bytes


class DecpClient:
    PAGE_SIZE = 100
    MAX_RESPONSE_BYTES = 5_000_000
    SELECT_FIELDS = (
        "id",
        "nature",
        "objet",
        "codecpv",
        "procedure",
        "acheteur_id",
        "acheteur_nom",
        "dureemois",
        "datenotification",
        "datepublicationdonnees",
        "montant",
        "titulaire_denominationsociale_1",
        "titulaire_id_1",
        "titulaire_typeidentifiant_1",
        "titulaire_denominationsociale_2",
        "titulaire_id_2",
        "titulaire_typeidentifiant_2",
        "titulaire_denominationsociale_3",
        "titulaire_id_3",
        "titulaire_typeidentifiant_3",
        "booleanmodification",
        "idmodification",
        "objetmodification",
        "datenotificationmodification",
        "dureemoismodification",
        "datepublicationdonneesmodification",
        "montantmodification",
        "titulairesmodification",
        "source",
        "updated_at",
    )

    def __init__(self, client: httpx.Client, *, records_url: str) -> None:
        self._client = client
        self._records_url = records_url

    def fetch_page(self, *, offset: int) -> DecpFetchResult:
        if offset < 0 or offset % self.PAGE_SIZE != 0:
            raise ValueError("DECP offset must be a non-negative page boundary")
        response = self._client.get(
            self._records_url,
            headers={"Accept": "application/json"},
            params={
                "select": ",".join(self.SELECT_FIELDS),
                "order_by": "datepublicationdonnees DESC,id ASC",
                "limit": self.PAGE_SIZE,
                "offset": offset,
            },
        )
        response.raise_for_status()
        _validate_content_type(response)
        _validate_size(response, max_bytes=self.MAX_RESPONSE_BYTES)
        return DecpFetchResult(body=response.content)


def _validate_content_type(response: httpx.Response) -> None:
    content_type = response.headers.get("content-type", "").split(";", maxsplit=1)[0].strip()
    if content_type != "application/json":
        raise DecpSourceResponseError(
            f"unexpected content type: {content_type or 'missing'}"
        )


def _validate_size(response: httpx.Response, *, max_bytes: int) -> None:
    declared = response.headers.get("content-length")
    if declared is not None:
        try:
            declared_size = int(declared)
        except ValueError as exc:
            raise DecpSourceResponseError("invalid Content-Length") from exc
        if declared_size > max_bytes:
            raise DecpSourceResponseError("response exceeds configured size limit")
    if len(response.content) > max_bytes:
        raise DecpSourceResponseError("response body exceeds configured size limit")
