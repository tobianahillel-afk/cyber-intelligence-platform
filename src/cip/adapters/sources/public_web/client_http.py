from __future__ import annotations

from contextlib import AbstractContextManager

import httpx

from cip.adapters.sources.public_web.client_contract import (
    PublicWebDeadlineExceededError,
    PublicWebResponseError,
)
from cip.adapters.sources.public_web.crawl_runtime import CrawlDeadline


class BoundedHttpTransport:
    """Stream public HTTP responses under per-request and whole-crawl limits."""

    def __init__(
        self,
        client: httpx.Client,
        *,
        request_timeout_seconds: float | None = None,
    ) -> None:
        if request_timeout_seconds is not None and request_timeout_seconds <= 0:
            raise ValueError("request_timeout_seconds must be positive")
        self._client = client
        self._request_timeout_seconds = request_timeout_seconds
        self._deadline: CrawlDeadline | None = None

    @property
    def deadline(self) -> CrawlDeadline | None:
        return self._deadline

    def bind_deadline(self, deadline: CrawlDeadline) -> None:
        if self._deadline is not None and self._deadline is not deadline:
            raise ValueError("public web client is already bound to another crawl deadline")
        self._deadline = deadline

    def get(
        self,
        url: str,
        *,
        headers: dict[str, str],
        follow_redirects: bool,
        max_bytes: int,
    ) -> httpx.Response:
        timeout = self._effective_timeout()
        try:
            with self._open_stream(
                url,
                headers=headers,
                follow_redirects=follow_redirects,
                timeout=timeout,
            ) as response:
                _validate_declared_length(response, max_bytes=max_bytes)
                body = bytearray()
                self._require_deadline()
                for chunk in response.iter_bytes():
                    body.extend(chunk)
                    if len(body) > max_bytes:
                        raise PublicWebResponseError(
                            "response body exceeds configured size limit"
                        )
                    self._require_deadline()
                return httpx.Response(
                    status_code=response.status_code,
                    headers=response.headers,
                    content=bytes(body),
                    request=response.request,
                )
        except httpx.TimeoutException as exc:
            if self._deadline is not None and self._deadline.exceeded:
                raise PublicWebDeadlineExceededError(
                    "whole-crawl deadline exceeded"
                ) from exc
            raise

    def _effective_timeout(self) -> float | None:
        timeout = self._request_timeout_seconds
        if self._deadline is None:
            return timeout
        remaining = self._deadline.remaining_seconds
        if remaining <= 0:
            raise PublicWebDeadlineExceededError("whole-crawl deadline exceeded")
        return remaining if timeout is None else min(timeout, remaining)

    def _require_deadline(self) -> None:
        if self._deadline is not None and self._deadline.exceeded:
            raise PublicWebDeadlineExceededError("whole-crawl deadline exceeded")

    def _open_stream(
        self,
        url: str,
        *,
        headers: dict[str, str],
        follow_redirects: bool,
        timeout: float | None,
    ) -> AbstractContextManager[httpx.Response]:
        if timeout is None:
            return self._client.stream(
                "GET",
                url,
                headers=headers,
                follow_redirects=follow_redirects,
            )
        return self._client.stream(
            "GET",
            url,
            headers=headers,
            follow_redirects=follow_redirects,
            timeout=timeout,
        )


def _validate_declared_length(response: httpx.Response, *, max_bytes: int) -> None:
    declared = response.headers.get("content-length")
    if declared is None:
        return
    try:
        declared_size = int(declared)
    except ValueError as exc:
        raise PublicWebResponseError("invalid Content-Length") from exc
    if declared_size < 0 or declared_size > max_bytes:
        raise PublicWebResponseError("response exceeds configured size limit")
