from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlencode

import httpx


class CordisFundingResponseError(RuntimeError):
    """CORDIS returned an unsafe or unusable SPARQL response."""


@dataclass(frozen=True, slots=True)
class CordisFundingFetchResult:
    body: bytes
    request_url: str


class CordisFundingClient:
    PAGE_SIZE = 100
    MAX_RESPONSE_BYTES = 5_000_000
    QUERY_TEMPLATE = """PREFIX eurio: <http://data.europa.eu/s66#>
SELECT DISTINCT ?project_id ?project_title ?organisation_name ?role_label
                ?start_date ?end_date ?eu_contribution
WHERE {
  ?project a eurio:Project ;
           eurio:identifier ?project_id ;
           eurio:title ?project_title ;
           eurio:hasInvolvedParty ?role .
  ?role eurio:isRoleOf ?organisation .
  ?organisation eurio:legalName ?organisation_name .
  OPTIONAL { ?role eurio:roleLabel ?role_label . }
  OPTIONAL { ?project eurio:startDate ?start_date . }
  OPTIONAL { ?project eurio:endDate ?end_date . }
  OPTIONAL { ?project eurio:ecMaxContribution ?eu_contribution . }
}
ORDER BY DESC(?start_date) ?project_id ?organisation_name
LIMIT __LIMIT__
OFFSET __OFFSET__
"""

    def __init__(self, client: httpx.Client, *, endpoint_url: str) -> None:
        self._client = client
        self._endpoint_url = endpoint_url.rstrip("/")

    def page_url(self, offset: int) -> str:
        if offset < 0:
            raise ValueError("offset cannot be negative")
        query = self.QUERY_TEMPLATE.replace("__LIMIT__", str(self.PAGE_SIZE)).replace(
            "__OFFSET__", str(offset)
        )
        params = urlencode(
            {
                "query": query,
                "format": "application/sparql-results+json",
            }
        )
        return f"{self._endpoint_url}?{params}"

    def fetch_url(self, url: str) -> CordisFundingFetchResult:
        response = self._client.get(
            url,
            headers={"Accept": "application/sparql-results+json"},
        )
        response.raise_for_status()
        _validate_content_type(response)
        _validate_size(response, max_bytes=self.MAX_RESPONSE_BYTES)
        return CordisFundingFetchResult(body=response.content, request_url=str(response.url))


def _validate_content_type(response: httpx.Response) -> None:
    content_type = response.headers.get("content-type", "").split(";", maxsplit=1)[0].strip()
    accepted = {"application/sparql-results+json", "application/json"}
    if content_type not in accepted:
        raise CordisFundingResponseError(
            f"unexpected content type: {content_type or 'missing'}"
        )


def _validate_size(response: httpx.Response, *, max_bytes: int) -> None:
    declared = response.headers.get("content-length")
    if declared is not None:
        try:
            declared_size = int(declared)
        except ValueError as exc:
            raise CordisFundingResponseError("invalid Content-Length") from exc
        if declared_size > max_bytes:
            raise CordisFundingResponseError("response exceeds configured size limit")
    if len(response.content) > max_bytes:
        raise CordisFundingResponseError("response body exceeds configured size limit")
