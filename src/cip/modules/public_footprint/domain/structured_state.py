from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import StrEnum
from hashlib import sha256
from typing import Any
from uuid import UUID, uuid4

from cip.modules.public_footprint.domain.url_identity import CanonicalUrl

_MAX_PAYLOAD_CHARS = 32_768
_MAX_LOCATOR_CHARS = 2_048
_MAX_EXTRACTOR_CHARS = 100


class PublicStructuredStateKind(StrEnum):
    NETWORK_JSON = "network_json"
    SCRIPT_STATE = "script_state"


@dataclass(frozen=True, slots=True)
class PublicStructuredState:
    organization_id: UUID
    resource_version_id: UUID
    kind: PublicStructuredStateKind
    page_url: str
    source_locator: str
    payload_json: str
    source_url: str | None = None
    http_status: int | None = None
    media_type: str | None = None
    extractor_id: str | None = None
    id: UUID = field(default_factory=uuid4)

    def __post_init__(self) -> None:
        page_url = CanonicalUrl(self.page_url).value
        source_locator = _required_text(
            self.source_locator,
            max_length=_MAX_LOCATOR_CHARS,
            field_name="source_locator",
        )
        payload_json = _canonical_payload(self.payload_json)
        source_url = CanonicalUrl(self.source_url).value if self.source_url else None
        media_type = _optional_media_type(self.media_type)
        extractor_id = _optional_text(
            self.extractor_id,
            max_length=_MAX_EXTRACTOR_CHARS,
            field_name="extractor_id",
        )
        if self.kind is PublicStructuredStateKind.NETWORK_JSON:
            if source_url is None or self.http_status is None or media_type is None:
                raise ValueError("network JSON requires source_url, http_status and media_type")
            if not 200 <= self.http_status <= 299:
                raise ValueError("network JSON status must be 2xx")
            if extractor_id is not None:
                raise ValueError("network JSON cannot have an extractor_id")
        else:
            if extractor_id is None:
                raise ValueError("script state requires extractor_id")
            if source_url is not None or self.http_status is not None or media_type is not None:
                raise ValueError("script state cannot carry HTTP response metadata")
        object.__setattr__(self, "page_url", page_url)
        object.__setattr__(self, "source_locator", source_locator)
        object.__setattr__(self, "payload_json", payload_json)
        object.__setattr__(self, "source_url", source_url)
        object.__setattr__(self, "media_type", media_type)
        object.__setattr__(self, "extractor_id", extractor_id)

    @property
    def payload_hash_sha256(self) -> str:
        return sha256(self.payload_json.encode("utf-8")).hexdigest()

    @property
    def identity_key(self) -> str:
        material = (
            f"{self.organization_id}\0{self.resource_version_id}\0{self.kind.value}\0"
            f"{self.source_url or ''}\0{self.source_locator}\0{self.payload_hash_sha256}"
        )
        return sha256(material.encode("utf-8")).hexdigest()


def _canonical_payload(raw: str) -> str:
    try:
        payload: Any = json.loads(raw)
    except (json.JSONDecodeError, RecursionError, ValueError) as exc:
        raise ValueError("payload_json must contain valid JSON") from exc
    if not isinstance(payload, dict | list):
        raise ValueError("payload_json must contain a JSON object or array")
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    if not canonical or len(canonical) > _MAX_PAYLOAD_CHARS:
        raise ValueError(f"payload_json cannot exceed {_MAX_PAYLOAD_CHARS} characters")
    return canonical


def _required_text(value: str, *, max_length: int, field_name: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field_name} is required")
    if len(normalized) > max_length:
        raise ValueError(f"{field_name} cannot exceed {max_length} characters")
    return normalized


def _optional_text(value: str | None, *, max_length: int, field_name: str) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    if not normalized:
        return None
    if len(normalized) > max_length:
        raise ValueError(f"{field_name} cannot exceed {max_length} characters")
    return normalized


def _optional_media_type(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.split(";", 1)[0].strip().casefold()
    if "/" not in normalized or len(normalized) > 200:
        raise ValueError("media_type must be a bounded MIME type")
    return normalized
