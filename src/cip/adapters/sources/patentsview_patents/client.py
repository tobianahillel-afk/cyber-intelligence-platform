from __future__ import annotations

from dataclasses import dataclass
from json import dumps

import httpx
from pydantic import ValidationError

from cip.adapters.sources.patentsview_patents.schemas import PatentsViewPatentResponse

_MAX_RESPONSE_BYTES = 2 * 1024 * 1024
_MAX_RESULTS = 20
_FIELDS = (
    "patent_id",
    "patent_title",
    "patent_date",
    "patent_type",
    "assignees.assignee_organization",
)


class PatentsViewClientError(RuntimeError):
    def __init__(self, message: str, *, code: str, retryable: bool) -> None:
        super().__init__(message)
        self.code = code
        self.retryable = retryable


@dataclass(frozen=True, slots=True)
class PatentsViewQueryResult:
    response: PatentsViewPatentResponse
    request_url: str


class PatentsViewClient:
    def __init__(
        self,
        api_key: str,
        *,
        timeout_seconds: float = 30.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        token = api_key.strip()
        if not token:
            raise ValueError("PatentsView api_key is required")
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        self._api_key = token
        self._timeout_seconds = timeout_seconds
        self._transport = transport

    def patents_for_assignee(
        self,
        url: str,
        *,
        assignee_organization: str,
    ) -> PatentsViewQueryResult:
        query = dumps(
            {"assignees.assignee_organization": assignee_organization},
            separators=(",", ":"),
        )
        fields = dumps(_FIELDS, separators=(",", ":"))
        options = dumps({"size": _MAX_RESULTS}, separators=(",", ":"))
        sort = dumps([{"patent_id": "asc"}], separators=(",", ":"))
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
                        "X-Api-Key": self._api_key,
                    },
                    params={"q": query, "f": fields, "o": options, "s": sort},
                )
                response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            raise PatentsViewClientError(
                f"PatentsView returned HTTP {status}",
                code=f"http_{status}",
                retryable=status == 429 or status >= 500,
            ) from exc
        except (httpx.TimeoutException, httpx.TransportError) as exc:
            raise PatentsViewClientError(
                str(exc) or type(exc).__name__,
                code="source_transport_error",
                retryable=True,
            ) from exc

        if "json" not in response.headers.get("content-type", "").casefold():
            raise PatentsViewClientError(
                "PatentsView response is not JSON",
                code="unsafe_source_response",
                retryable=False,
            )
        if len(response.content) > _MAX_RESPONSE_BYTES:
            raise PatentsViewClientError(
                "PatentsView response exceeds size limit",
                code="unsafe_source_response",
                retryable=False,
            )
        try:
            parsed = PatentsViewPatentResponse.model_validate_json(response.content)
        except ValidationError as exc:
            raise PatentsViewClientError(
                "PatentsView response schema changed",
                code="source_schema_drift",
                retryable=False,
            ) from exc
        if parsed.error or parsed.count != len(parsed.patents):
            raise PatentsViewClientError(
                "PatentsView returned an inconsistent response envelope",
                code="source_schema_drift",
                retryable=False,
            )
        return PatentsViewQueryResult(response=parsed, request_url=str(response.request.url))
