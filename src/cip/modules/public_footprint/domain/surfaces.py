from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from hashlib import sha256
from uuid import UUID, uuid4

from cip.modules.public_footprint.domain.url_identity import CanonicalUrl


class PublicSurfaceKind(StrEnum):
    CANONICAL_LINK = "canonical_link"
    ALTERNATE_LINK = "alternate_link"
    STYLESHEET = "stylesheet"
    SCRIPT = "script"
    RESOURCE_REFERENCE = "resource_reference"
    FORM_ENDPOINT = "form_endpoint"
    DOCUMENT_LINK = "document_link"
    MEDIA_LINK = "media_link"
    RESPONSE_HEADER = "response_header"


@dataclass(frozen=True, slots=True)
class PublicSurfaceReference:
    organization_id: UUID
    resource_version_id: UUID
    kind: PublicSurfaceKind
    source_locator: str
    target_url: str | None = None
    relation: str | None = None
    http_method: str | None = None
    media_type: str | None = None
    name: str | None = None
    value: str | None = None
    id: UUID = field(default_factory=uuid4)

    def __post_init__(self) -> None:
        locator = _required_text(self.source_locator, 500, "source_locator")
        target_url = (
            CanonicalUrl(self.target_url).value if self.target_url is not None else None
        )
        relation = _optional_text(self.relation, 200, "relation", casefold=True)
        method = _optional_text(self.http_method, 16, "http_method")
        if method is not None:
            method = method.upper()
        media_type = _optional_media_type(self.media_type)
        name = _optional_text(self.name, 100, "name", casefold=True)
        value = _optional_text(self.value, 2_000, "value")
        if self.kind is PublicSurfaceKind.RESPONSE_HEADER:
            if target_url is not None or name is None or value is None:
                raise ValueError("response-header surfaces require name/value and no target URL")
        elif target_url is None:
            raise ValueError("URL surface references require target_url")
        object.__setattr__(self, "source_locator", locator)
        object.__setattr__(self, "target_url", target_url)
        object.__setattr__(self, "relation", relation)
        object.__setattr__(self, "http_method", method)
        object.__setattr__(self, "media_type", media_type)
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "value", value)

    @property
    def identity_key(self) -> str:
        material = "\0".join(
            (
                str(self.organization_id),
                str(self.resource_version_id),
                self.kind.value,
                self.source_locator,
                self.target_url or "",
                self.relation or "",
                self.http_method or "",
                self.media_type or "",
                self.name or "",
                self.value or "",
            )
        )
        return sha256(material.encode("utf-8")).hexdigest()


def _required_text(value: str, max_length: int, field_name: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field_name} is required")
    if len(normalized) > max_length:
        raise ValueError(f"{field_name} cannot exceed {max_length} characters")
    return normalized


def _optional_text(
    value: str | None,
    max_length: int,
    field_name: str,
    *,
    casefold: bool = False,
) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    if not normalized:
        return None
    if len(normalized) > max_length:
        raise ValueError(f"{field_name} cannot exceed {max_length} characters")
    return normalized.casefold() if casefold else normalized


def _optional_media_type(value: str | None) -> str | None:
    normalized = _optional_text(value, 200, "media_type", casefold=True)
    if normalized is None:
        return None
    return normalized.split(";", 1)[0].strip()
