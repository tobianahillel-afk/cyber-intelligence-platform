from __future__ import annotations

from dataclasses import dataclass

import httpx


class TedSourceResponseError(RuntimeError):
    """TED returned an unsafe or unusable response."""


@dataclass(frozen=True, slots=True)
class TedSearchCheckpoint:
    latest_publication_number: str | None = None


@dataclass(frozen=True, slots=True)
class TedSearchFetchResult:
    body: bytes


class TedSearchClient:
    MAX_RESPONSE_BYTES = 5_000_000
    DEFAULT_LIMIT = 100
    SEARCH_FIELDS = (
        "publication-number",
        "notice-title",
        "buyer-name",
        "buyer-country",
        "publication-date",
        "deadline-receipt-tender-date-lot",
        "classification-cpv",
        "notice-type",
        "procedure-identifier",
        "contract-identifier",
        "contract-conclusion-date",
        "winner-decision-date",
        "winner-name",
        "winner-identifier",
        "contract-title",
        "tender-value",
        "tender-value-cur",
    )
    SEARCH_QUERY = (
        'FT=(siem OR soc OR cybersecurity OR "cyber security" OR cybersecurite '
        'OR cybersécurité OR xdr OR mdr OR pentest OR "penetration test" '
        'OR "test intrusion" OR "incident response" OR dfir OR iam OR pam '
        'OR "zero trust" OR "cloud security" OR appsec OR devsecops OR grc '
        'OR "iso 27001" OR "data protection" OR "network security" '
        'OR "security awareness" OR "industrial security")'
    )

    def __init__(self, client: httpx.Client, *, search_url: str) -> None:
        self._client = client
        self._search_url = search_url

    def fetch(self) -> TedSearchFetchResult:
        response = self._client.post(
            self._search_url,
            headers={"Accept": "application/json", "Content-Type": "application/json"},
            json={
                "query": self.SEARCH_QUERY,
                "fields": list(self.SEARCH_FIELDS),
                "limit": self.DEFAULT_LIMIT,
                "scope": "ALL",
                "checkQuerySyntax": False,
                "paginationMode": "PAGE_NUMBER",
                "page": 1,
                "onlyLatestVersions": True,
            },
        )
        response.raise_for_status()
        _validate_content_type(response)
        _validate_size(response, max_bytes=self.MAX_RESPONSE_BYTES)
        return TedSearchFetchResult(body=response.content)


def _validate_content_type(response: httpx.Response) -> None:
    content_type = response.headers.get("content-type", "").split(";", maxsplit=1)[0].strip()
    if content_type != "application/json":
        raise TedSourceResponseError(f"unexpected content type: {content_type or 'missing'}")


def _validate_size(response: httpx.Response, *, max_bytes: int) -> None:
    declared = response.headers.get("content-length")
    if declared is not None:
        try:
            declared_size = int(declared)
        except ValueError as exc:
            raise TedSourceResponseError("invalid Content-Length") from exc
        if declared_size > max_bytes:
            raise TedSourceResponseError("response exceeds configured size limit")
    if len(response.content) > max_bytes:
        raise TedSourceResponseError("response body exceeds configured size limit")
