from __future__ import annotations

from datetime import date, datetime

import httpx
import pytest
from pydantic import ValidationError

from cip.adapters.sources.boamp.client import (
    BoampClient,
    BoampSourceResponseError,
)
from cip.adapters.sources.boamp.schemas import BoampNotice, BoampResponse


def test_client_requests_bounded_selected_window() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["method"] = request.method
        captured["params"] = dict(request.url.params)
        return httpx.Response(
            200,
            headers={"content-type": "application/json"},
            json={"total_count": 0, "results": []},
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as http_client:
        result = BoampClient(
            http_client,
            records_url="https://boamp.example/api/records",
        ).fetch_page(since_date=date(2026, 8, 3), offset=100)

    params = captured["params"]
    assert captured["method"] == "GET"
    assert isinstance(params, dict)
    assert params["where"] == "dateparution >= date'2026-08-03'"
    assert params["order_by"] == "dateparution desc,idweb desc"
    assert params["limit"] == "100"
    assert params["offset"] == "100"
    assert "nomacheteur" in params["select"]
    assert BoampResponse.model_validate_json(result.body).results == []


def test_client_rejects_negative_offset() -> None:
    with httpx.Client(transport=httpx.MockTransport(lambda _: httpx.Response(200))) as client:
        with pytest.raises(ValueError, match="offset"):
            BoampClient(client, records_url="https://boamp.example/records").fetch_page(
                since_date=date(2026, 8, 3),
                offset=-1,
            )


def test_client_rejects_non_json_and_invalid_or_oversized_lengths() -> None:
    responses = iter(
        [
            httpx.Response(200, headers={"content-type": "text/html"}, text="no"),
            httpx.Response(
                200,
                headers={"content-type": "application/json", "content-length": "invalid"},
                content=b"{}",
            ),
            httpx.Response(
                200,
                headers={
                    "content-type": "application/json",
                    "content-length": str(BoampClient.MAX_RESPONSE_BYTES + 1),
                },
                content=b"{}",
            ),
        ]
    )

    def handler(_: httpx.Request) -> httpx.Response:
        return next(responses)

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        boamp = BoampClient(client, records_url="https://boamp.example/records")
        with pytest.raises(BoampSourceResponseError, match="content type"):
            boamp.fetch_page(since_date=date(2026, 8, 3), offset=0)
        with pytest.raises(BoampSourceResponseError, match="Content-Length"):
            boamp.fetch_page(since_date=date(2026, 8, 3), offset=0)
        with pytest.raises(BoampSourceResponseError, match="size limit"):
            boamp.fetch_page(since_date=date(2026, 8, 3), offset=0)


def test_schema_normalizes_dates_nested_text_and_notice_url() -> None:
    notice = BoampNotice.model_validate(
        _notice(
            dateparution="20260804",
            datelimitereponse="30/08/2026",
            descripteur_libelle=["Cybersécurité", {"detail": "SIEM"}],
            type_marche={"label": "Services SOC"},
            type_avis=["Avis de marché"],
            url_avis=" ",
        )
    )

    assert notice.publication_timestamp() == datetime(2026, 8, 4)
    assert notice.deadline_timestamp() == datetime(2026, 8, 30)
    assert "Cybersécurité" in notice.searchable_text()
    assert "Services SOC" in notice.searchable_text()
    assert notice.notice_url().endswith("q=idweb:26-123456")


def test_schema_rejects_missing_required_text_and_ignores_unknown_fields() -> None:
    payload = _notice(extra_remote_field="ignored")
    notice = BoampNotice.model_validate(payload)
    assert notice.idweb == "26-123456"

    payload["nomacheteur"] = " "
    with pytest.raises(ValidationError, match="required BOAMP text"):
        BoampNotice.model_validate(payload)


def _notice(**changes: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "idweb": "26-123456",
        "objet": "Service de supervision SIEM",
        "dateparution": "2026-08-04",
        "datelimitereponse": "2026-08-30T12:00:00Z",
        "nomacheteur": "Ville Exemple",
        "etat": "initial",
        "nature_libelle": "Avis de marché",
        "type_avis": ["Marché"],
        "descripteur_libelle": ["Cybersécurité"],
        "type_marche": ["Services"],
        "titulaire": None,
        "url_avis": "https://www.boamp.fr/avis/detail/26-123456",
    }
    payload.update(changes)
    return payload
