from __future__ import annotations

from dataclasses import dataclass

import httpx
from pydantic import ValidationError

from cip.adapters.sources.crossref_publications.schemas import CrossrefWorksResponse

_MAX_RESPONSE_BYTES = 2 * 1024 * 1024
_MAX_RESULTS = 20
_USER_AGENT = (
    "cyber-intelligence-platform/0.24 "
    "(https://github.com/tobianahillel-afk/cyber-intelligence-platform)"
)


class CrossrefClientError(RuntimeError):
    def __init__(self, message: str, *, code: str, retryable: bool) -> None:
        super().__init__(message)
        self.code = code
        self.retryable = retryable


@dataclass(frozen=True, slots=True)
class CrossrefQueryResult:
    response: CrossrefWorksResponse
    request_url: str


class CrossrefClient:
    def __init__(
        self,
        *,
        timeout_seconds: float = 30.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        self._timeout_seconds = timeout_seconds
        self._transport = transport

    def works_for_ror(self, url: str, *, ror_id: str) -> CrossrefQueryResult:
        try:
            with httpx.Client(
                timeout=self._timeout_seconds,
                follow_redirects=False,
                transport=self._transport,
            ) as client:
                response = client.get(
                    url,
                    headers={
                        "Accept": "application/json",
                        "User-Agent": _USER_AGENT,
                    },
                    params={
                        "filter": f"ror-id:{ror_id}",
                        "rows": str(_MAX_RESULTS),
                        "select": "DOI,title,type,URL",
                    },
                )
                response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            raise CrossrefClientError(
                f"Crossref returned HTTP {status}",
                code=f"http_{status}",
                retryable=status == 429 or status >= 500,
            ) from exc
        except (httpx.TimeoutException, httpx.TransportError) as exc:
            raise CrossrefClientError(
                str(exc) or type(exc).__name__,
                code="source_transport_error",
                retryable=True,
            ) from exc

        content_type = response.headers.get("content-type", "").casefold()
        if "json" not in content_type:
            raise CrossrefClientError(
                "Crossref response is not JSON",
                code="unsafe_source_response",
                retryable=False,
            )
        if len(response.content) > _MAX_RESPONSE_BYTES:
            raise CrossrefClientError(
                "Crossref response exceeds size limit",
                code="unsafe_source_response",
                retryable=False,
            )
        try:
            parsed = CrossrefWorksResponse.model_validate_json(response.content)
        except ValidationError as exc:
            raise CrossrefClientError(
                "Crossref response schema changed",
                code="source_schema_drift",
                retryable=False,
            ) from exc
        if parsed.status.casefold() != "ok" or parsed.message_type.casefold() != "work-list":
            raise CrossrefClientError(
                "Crossref returned an unexpected response envelope",
                code="source_schema_drift",
                retryable=False,
            )
        return CrossrefQueryResult(response=parsed, request_url=str(response.request.url))
