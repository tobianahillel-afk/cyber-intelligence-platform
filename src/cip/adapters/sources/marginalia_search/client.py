from __future__ import annotations

from dataclasses import dataclass

import httpx
from pydantic import ValidationError

from cip.adapters.sources.marginalia_search.registry import MarginaliaSearchEntitlement
from cip.adapters.sources.marginalia_search.schemas import MarginaliaSearchResponse

_MAX_RESPONSE_BYTES = 2 * 1024 * 1024
_MAX_RESULTS = 20
_API_URL = "https://api2.marginalia-search.com/search"
_USER_AGENT = (
    "cyber-intelligence-platform/0.24 "
    "(https://github.com/tobianahillel-afk/cyber-intelligence-platform)"
)


class MarginaliaSearchClientError(RuntimeError):
    def __init__(self, message: str, *, code: str, retryable: bool) -> None:
        super().__init__(message)
        self.code = code
        self.retryable = retryable


@dataclass(frozen=True, slots=True)
class MarginaliaQueryResult:
    response: MarginaliaSearchResponse
    request_url: str


class MarginaliaSearchClient:
    def __init__(
        self,
        entitlement: MarginaliaSearchEntitlement,
        *,
        timeout_seconds: float = 30.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        self._entitlement = entitlement
        self._timeout_seconds = timeout_seconds
        self._transport = transport

    def search(self, *, query: str, api_key: str) -> MarginaliaQueryResult:
        self._entitlement.assert_live_collection_ready()
        normalized_query = query.strip()
        normalized_key = api_key.strip()
        if not normalized_query:
            raise ValueError("query must be non-empty")
        if not normalized_key:
            raise ValueError("api_key must be non-empty")
        if normalized_key.casefold() == "public":
            raise PermissionError(
                "Marginalia public development key is not accepted for production collection"
            )

        try:
            with httpx.Client(
                timeout=self._timeout_seconds,
                follow_redirects=False,
                transport=self._transport,
            ) as client:
                with client.stream(
                    "GET",
                    _API_URL,
                    headers={
                        "Accept": "application/json",
                        "API-Key": normalized_key,
                        "User-Agent": _USER_AGENT,
                    },
                    params={
                        "query": normalized_query,
                        "count": str(_MAX_RESULTS),
                        "dc": "3",
                        "nsfw": "1",
                    },
                ) as response:
                    response.raise_for_status()
                    content_type = response.headers.get("content-type", "").casefold()
                    if "json" not in content_type:
                        raise MarginaliaSearchClientError(
                            "Marginalia response is not JSON",
                            code="unsafe_source_response",
                            retryable=False,
                        )
                    content = _read_bounded_body(response)
                    request_url = str(response.request.url)
        except MarginaliaSearchClientError:
            raise
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            raise MarginaliaSearchClientError(
                f"Marginalia returned HTTP {status}",
                code=f"http_{status}",
                retryable=status == 429 or status >= 500,
            ) from exc
        except (httpx.TimeoutException, httpx.TransportError) as exc:
            raise MarginaliaSearchClientError(
                str(exc) or type(exc).__name__,
                code="source_transport_error",
                retryable=True,
            ) from exc

        try:
            parsed = MarginaliaSearchResponse.model_validate_json(content)
        except ValidationError as exc:
            raise MarginaliaSearchClientError(
                "Marginalia response schema changed",
                code="source_schema_drift",
                retryable=False,
            ) from exc
        return MarginaliaQueryResult(
            response=parsed,
            request_url=request_url,
        )


def _read_bounded_body(response: httpx.Response) -> bytes:
    body = bytearray()
    for chunk in response.iter_bytes():
        if len(body) + len(chunk) > _MAX_RESPONSE_BYTES:
            raise MarginaliaSearchClientError(
                "Marginalia response exceeds size limit",
                code="unsafe_source_response",
                retryable=False,
            )
        body.extend(chunk)
    return bytes(body)
