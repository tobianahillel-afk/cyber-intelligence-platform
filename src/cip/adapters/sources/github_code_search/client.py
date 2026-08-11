from __future__ import annotations

from dataclasses import dataclass

import httpx
from pydantic import ValidationError

from cip.adapters.sources.github_code_search.schemas import GitHubCodeSearchResponse

API_VERSION = "2026-03-10"
MAX_RESPONSE_BYTES = 2 * 1024 * 1024
PER_PAGE = 20


class GitHubCodeSearchClientError(RuntimeError):
    def __init__(self, message: str, *, code: str, retryable: bool) -> None:
        super().__init__(message)
        self.code = code
        self.retryable = retryable


@dataclass(frozen=True, slots=True)
class GitHubCodeSearchResult:
    response: GitHubCodeSearchResponse
    request_url: str


class GitHubCodeSearchClient:
    def __init__(
        self,
        token: str,
        *,
        timeout_seconds: float = 30.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        if not token.strip():
            raise ValueError("GitHub code-search token is required")
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        self._token = token
        self._timeout_seconds = timeout_seconds
        self._transport = transport

    def search(self, endpoint_url: str, *, query: str) -> GitHubCodeSearchResult:
        try:
            with httpx.Client(
                timeout=self._timeout_seconds,
                follow_redirects=False,
                transport=self._transport,
            ) as client:
                response = client.get(
                    endpoint_url,
                    params={"q": query, "per_page": PER_PAGE, "page": 1},
                    headers={
                        "Accept": "application/vnd.github+json",
                        "Authorization": f"Bearer {self._token}",
                        "X-GitHub-Api-Version": API_VERSION,
                    },
                )
                response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            raise GitHubCodeSearchClientError(
                f"GitHub code search returned HTTP {status}",
                code=f"http_{status}",
                retryable=status in {403, 429} or status >= 500,
            ) from exc
        except (httpx.TimeoutException, httpx.TransportError) as exc:
            raise GitHubCodeSearchClientError(
                str(exc) or type(exc).__name__,
                code="source_transport_error",
                retryable=True,
            ) from exc
        if len(response.content) > MAX_RESPONSE_BYTES:
            raise GitHubCodeSearchClientError(
                "GitHub code-search response exceeds size limit",
                code="unsafe_source_response",
                retryable=False,
            )
        try:
            parsed = GitHubCodeSearchResponse.model_validate_json(response.content)
        except ValidationError as exc:
            raise GitHubCodeSearchClientError(
                "GitHub code-search response schema changed",
                code="source_schema_drift",
                retryable=False,
            ) from exc
        if parsed.incomplete_results:
            raise GitHubCodeSearchClientError(
                "GitHub code-search result set is incomplete",
                code="incomplete_provider_results",
                retryable=True,
            )
        if len(parsed.items) > PER_PAGE:
            raise GitHubCodeSearchClientError(
                "GitHub code-search returned too many items",
                code="unsafe_source_response",
                retryable=False,
            )
        return GitHubCodeSearchResult(response=parsed, request_url=str(response.url))
