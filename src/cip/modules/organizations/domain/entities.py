from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from re import fullmatch
from urllib.parse import urlparse
from uuid import UUID, uuid4

from cip.shared.kernel.time import require_aware_utc, utc_now


@dataclass(frozen=True, slots=True)
class Organization:
    canonical_name: str
    id: UUID = field(default_factory=uuid4)
    legal_name: str | None = None
    country_code: str | None = None
    website_url: str | None = None
    registration_ids: tuple[str, ...] = ()
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        canonical_name = self.canonical_name.strip()
        if not canonical_name:
            raise ValueError("canonical_name is required")
        if len(canonical_name) > 300:
            raise ValueError("canonical_name cannot exceed 300 characters")
        object.__setattr__(self, "canonical_name", canonical_name)
        if self.legal_name is not None and len(self.legal_name.strip()) > 300:
            raise ValueError("legal_name cannot exceed 300 characters")
        if self.country_code is not None and not fullmatch(r"[A-Z]{2}", self.country_code):
            raise ValueError("country_code must be ISO 3166-1 alpha-2 uppercase")
        if self.website_url is not None and not _is_http_url(self.website_url):
            raise ValueError("website_url must use http or https")
        object.__setattr__(
            self,
            "created_at",
            require_aware_utc(self.created_at, field_name="created_at"),
        )
        object.__setattr__(
            self,
            "updated_at",
            require_aware_utc(self.updated_at, field_name="updated_at"),
        )
        if self.updated_at < self.created_at:
            raise ValueError("updated_at cannot precede created_at")


def _is_http_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.hostname)
