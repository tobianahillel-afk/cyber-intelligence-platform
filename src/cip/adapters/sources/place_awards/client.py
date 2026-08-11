from __future__ import annotations

from dataclasses import dataclass

import httpx


class PlaceSourceResponseError(RuntimeError):
    """PLACE open-data API returned an unsafe or unusable response."""


@dataclass(frozen=True, slots=True)
class PlaceFetchResult:
    body: bytes


class PlaceAwardsClient:
    PAGE_SIZE = 100
    MAX_RESPONSE_BYTES = 5_000_000
    SELECT_FIELDS = (
        "annee_de_notification",
        "entite_publique",
        "entite_d_achat",
        "code_postal_entite_d_achat",
        "nom_attributaire",
        "siret_attributaire",
        "date_de_notification",
        "code_postal_attributaire",
        "ville",
        "nature_du_marche",
        "objet_du_marche",
        "tranche_budgetaire",
        "montant",
        "attributaire_est_une_pme",
        "geocode_att",
    )

    def __init__(self, client: httpx.Client, *, records_url: str) -> None:
        self._client = client
        self._records_url = records_url

    def fetch_page(self, *, offset: int) -> PlaceFetchResult:
        if offset < 0 or offset % self.PAGE_SIZE != 0:
            raise ValueError("PLACE offset must be a non-negative page boundary")
        response = self._client.get(
            self._records_url,
            headers={"Accept": "application/json"},
            params={
                "select": ",".join(self.SELECT_FIELDS),
                "order_by": "date_de_notification DESC,entite_publique ASC",
                "limit": self.PAGE_SIZE,
                "offset": offset,
            },
        )
        response.raise_for_status()
        _validate_content_type(response)
        _validate_size(response, max_bytes=self.MAX_RESPONSE_BYTES)
        return PlaceFetchResult(body=response.content)


def _validate_content_type(response: httpx.Response) -> None:
    content_type = response.headers.get("content-type", "").split(";", maxsplit=1)[0].strip()
    if content_type != "application/json":
        raise PlaceSourceResponseError(
            f"unexpected content type: {content_type or 'missing'}"
        )


def _validate_size(response: httpx.Response, *, max_bytes: int) -> None:
    declared = response.headers.get("content-length")
    if declared is not None:
        try:
            declared_size = int(declared)
        except ValueError as exc:
            raise PlaceSourceResponseError("invalid Content-Length") from exc
        if declared_size > max_bytes:
            raise PlaceSourceResponseError("response exceeds configured size limit")
    if len(response.content) > max_bytes:
        raise PlaceSourceResponseError("response body exceeds configured size limit")
