from __future__ import annotations

from dataclasses import dataclass

import httpx


class SmartRecruitersSourceResponseError(RuntimeError):
    """SmartRecruiters returned an unsafe or unusable response."""


@dataclass(frozen=True, slots=True)
class SmartRecruitersFetchResult:
    body: bytes
    request_url: str


class SmartRecruitersClient:
    MAX_RESPONSE_BYTES = 5_000_000

    def __init__(self, client: httpx.Client, *, companies_base_url: str) -> None:
        self._client = client
        self._companies_base_url = companies_base_url.rstrip("/")

    def postings_url(self, company_identifier: str) -> str:
        return f"{self._companies_base_url}/{company_identifier}/postings"

    def posting_url(self, company_identifier: str, posting_id: str) -> str:
        return f"{self.postings_url(company_identifier)}/{posting_id}"

    def fetch_postings(
        self,
        company_identifier: str,
        *,
        offset: int,
        limit: int,
    ) -> SmartRecruitersFetchResult:
        if offset < 0:
            raise ValueError("offset must not be negative")
        if not 1 <= limit <= 100:
            raise ValueError("limit must be between 1 and 100")
        response = self._client.get(
            self.postings_url(company_identifier),
            headers={"Accept": "application/json"},
            params={
                "destination": "PUBLIC",
                "offset": offset,
                "limit": limit,
            },
        )
        return _validated_result(response)

    def fetch_posting(
        self,
        company_identifier: str,
        posting_id: str,
    ) -> SmartRecruitersFetchResult:
        response = self._client.get(
            self.posting_url(company_identifier, posting_id),
            headers={"Accept": "application/json"},
        )
        return _validated_result(response)


def _validated_result(response: httpx.Response) -> SmartRecruitersFetchResult:
    response.raise_for_status()
    _validate_content_type(response)
    _validate_size(response, max_bytes=SmartRecruitersClient.MAX_RESPONSE_BYTES)
    return SmartRecruitersFetchResult(
        body=response.content,
        request_url=str(response.request.url),
    )


def _validate_content_type(response: httpx.Response) -> None:
    content_type = response.headers.get("content-type", "").split(";", maxsplit=1)[0].strip()
    if content_type != "application/json":
        raise SmartRecruitersSourceResponseError(
            f"unexpected content type: {content_type or 'missing'}"
        )


def _validate_size(response: httpx.Response, *, max_bytes: int) -> None:
    declared = response.headers.get("content-length")
    if declared is not None:
        try:
            declared_size = int(declared)
        except ValueError as exc:
            raise SmartRecruitersSourceResponseError("invalid Content-Length") from exc
        if declared_size > max_bytes:
            raise SmartRecruitersSourceResponseError(
                "response exceeds configured size limit"
            )
    if len(response.content) > max_bytes:
        raise SmartRecruitersSourceResponseError(
            "response body exceeds configured size limit"
        )
