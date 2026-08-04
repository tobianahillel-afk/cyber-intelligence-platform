from __future__ import annotations

from dataclasses import dataclass

import httpx


class RechercheEntreprisesSourceResponseError(RuntimeError):
    """The official company-search API returned an unsafe response."""


@dataclass(frozen=True, slots=True)
class RechercheEntreprisesFetchResult:
    body: bytes
    request_url: str


class RechercheEntreprisesClient:
    MAX_RESPONSE_BYTES = 3_000_000

    def __init__(
        self,
        client: httpx.Client,
        *,
        search_url: str,
        user_agent: str = "CyberIntelligencePlatform/0.9 organization-identity",
    ) -> None:
        self._client = client
        self._search_url = search_url.rstrip("/")
        self._user_agent = user_agent.strip()
        if not self._user_agent:
            raise ValueError("user_agent is required")

    @property
    def search_url(self) -> str:
        return self._search_url

    def search(
        self,
        query: str,
        *,
        page: int = 1,
        per_page: int = 25,
    ) -> RechercheEntreprisesFetchResult:
        normalized = query.strip()
        if not normalized:
            raise ValueError("query is required")
        if len(normalized) > 300:
            raise ValueError("query cannot exceed 300 characters")
        if page < 1:
            raise ValueError("page must be positive")
        if not 1 <= per_page <= 25:
            raise ValueError("per_page must be between 1 and 25")
        response = self._client.get(
            self._search_url,
            headers={
                "Accept": "application/json",
                "User-Agent": self._user_agent,
            },
            params={
                "q": normalized,
                "page": page,
                "per_page": per_page,
                "minimal": "true",
                "include": "siege,matching_etablissements",
                "limite_matching_etablissements": 25,
            },
        )
        response.raise_for_status()
        _validate_json_response(response, max_bytes=self.MAX_RESPONSE_BYTES)
        return RechercheEntreprisesFetchResult(
            body=response.content,
            request_url=str(response.request.url),
        )


def _validate_json_response(response: httpx.Response, *, max_bytes: int) -> None:
    content_type = response.headers.get("content-type", "").split(";", maxsplit=1)[0].strip()
    if content_type != "application/json":
        raise RechercheEntreprisesSourceResponseError(
            f"unexpected content type: {content_type or 'missing'}"
        )
    declared = response.headers.get("content-length")
    if declared is not None:
        try:
            declared_size = int(declared)
        except ValueError as exc:
            raise RechercheEntreprisesSourceResponseError("invalid Content-Length") from exc
        if declared_size > max_bytes:
            raise RechercheEntreprisesSourceResponseError(
                "response exceeds configured size limit"
            )
    if len(response.content) > max_bytes:
        raise RechercheEntreprisesSourceResponseError(
            "response body exceeds configured size limit"
        )
