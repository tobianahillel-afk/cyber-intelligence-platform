from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from urllib.parse import urlsplit

import httpx
from pydantic import BaseModel, ValidationError

from cip.adapters.sources.w3c_standards.schemas import (
    W3cAffiliation,
    W3cParticipationsResponse,
    W3cSpecification,
    W3cSpecificationsResponse,
)

_MAX_RESPONSE_BYTES = 2 * 1024 * 1024
_MAX_GROUPS = 5
_MAX_RESULTS = 20


class W3cClientError(RuntimeError):
    def __init__(self, message: str, *, code: str, retryable: bool) -> None:
        super().__init__(message)
        self.code = code
        self.retryable = retryable


@dataclass(frozen=True, slots=True)
class W3cSpecificationRecord:
    group_type: str
    group_shortname: str
    specification: W3cSpecification
    source_url: str


@dataclass(frozen=True, slots=True)
class W3cQueryResult:
    affiliation: W3cAffiliation
    records: tuple[W3cSpecificationRecord, ...]


class W3cClient:
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

    def specifications_for_affiliation(
        self,
        affiliations_url: str,
        *,
        affiliation_id: int,
        expected_name: str,
    ) -> W3cQueryResult:
        root = _api_root(affiliations_url)
        affiliation_url = f"{affiliations_url.rstrip('/')}/{affiliation_id}"
        participations_url = f"{affiliation_url}/participations"
        with httpx.Client(
            timeout=self._timeout_seconds,
            follow_redirects=False,
            transport=self._transport,
        ) as client:
            affiliation, _ = _get_model(
                client,
                affiliation_url,
                W3cAffiliation,
            )
            if _normalize_name(affiliation.name) != _normalize_name(expected_name):
                raise W3cClientError(
                    "W3C affiliation identity did not match configured organization target",
                    code="target_identity_mismatch",
                    retryable=False,
                )
            participations, _ = _get_model(
                client,
                participations_url,
                W3cParticipationsResponse,
                params={"items": _MAX_RESULTS, "page": 1, "embed": 1},
            )
            records: list[W3cSpecificationRecord] = []
            seen: set[tuple[str, str, str]] = set()
            groups_seen = 0
            for participation in participations.embedded.participations:
                group_link = participation.links.get("group")
                if group_link is None:
                    continue
                identity = _group_identity(group_link.href, root)
                if identity is None:
                    continue
                group_type, group_shortname, group_url = identity
                groups_seen += 1
                if groups_seen > _MAX_GROUPS:
                    break
                specifications, source_url = _get_model(
                    client,
                    f"{group_url}/specifications",
                    W3cSpecificationsResponse,
                    params={"items": _MAX_RESULTS, "page": 1, "embed": 1},
                )
                for specification in specifications.embedded.specifications:
                    key = (
                        group_type,
                        group_shortname.casefold(),
                        specification.shortname.casefold(),
                    )
                    if key in seen:
                        continue
                    seen.add(key)
                    records.append(
                        W3cSpecificationRecord(
                            group_type=group_type,
                            group_shortname=group_shortname,
                            specification=specification,
                            source_url=source_url,
                        )
                    )
                    if len(records) >= _MAX_RESULTS:
                        return W3cQueryResult(
                            affiliation=affiliation,
                            records=tuple(records),
                        )
        return W3cQueryResult(affiliation=affiliation, records=tuple(records))


def _get_model[MODEL: BaseModel](
    client: httpx.Client,
    url: str,
    model: type[MODEL],
    *,
    params: Mapping[str, str | int | float | bool | None] | None = None,
) -> tuple[MODEL, str]:
    try:
        response = client.get(
            url,
            params=params,
            headers={"Accept": "application/json"},
        )
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        status = exc.response.status_code
        raise W3cClientError(
            f"W3C API returned HTTP {status}",
            code=f"http_{status}",
            retryable=status == 429 or status >= 500,
        ) from exc
    except (httpx.TimeoutException, httpx.TransportError) as exc:
        raise W3cClientError(
            str(exc) or type(exc).__name__,
            code="source_transport_error",
            retryable=True,
        ) from exc
    content_type = response.headers.get("content-type", "").casefold()
    if "json" not in content_type or len(response.content) > _MAX_RESPONSE_BYTES:
        raise W3cClientError(
            "W3C API returned an unsafe response",
            code="unsafe_source_response",
            retryable=False,
        )
    try:
        parsed = model.model_validate_json(response.content)
    except ValidationError as exc:
        raise W3cClientError(
            "W3C API response schema changed",
            code="source_schema_drift",
            retryable=False,
        ) from exc
    return parsed, str(response.request.url)


def _api_root(affiliations_url: str) -> str:
    parsed = urlsplit(affiliations_url)
    if (
        parsed.scheme != "https"
        or parsed.hostname != "api.w3.org"
        or parsed.path.rstrip("/") != "/affiliations"
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError("W3C affiliations base URL must be https://api.w3.org/affiliations")
    return "https://api.w3.org"


def _group_identity(href: str, root: str) -> tuple[str, str, str] | None:
    parsed = urlsplit(href)
    if parsed.scheme != "https" or parsed.hostname != "api.w3.org":
        return None
    if parsed.query or parsed.fragment:
        return None
    parts = tuple(part for part in parsed.path.split("/") if part)
    if len(parts) != 3 or parts[0] != "groups":
        return None
    group_type, group_shortname = parts[1], parts[2]
    if not group_type or not group_shortname:
        return None
    return group_type, group_shortname, f"{root}/groups/{group_type}/{group_shortname}"


def _normalize_name(value: str) -> str:
    return " ".join(value.split()).casefold()
