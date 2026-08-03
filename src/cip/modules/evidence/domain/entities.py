from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from re import fullmatch
from urllib.parse import urlparse
from uuid import UUID, uuid4

from cip.shared.kernel.time import require_aware_utc, utc_now


@dataclass(frozen=True, slots=True)
class Evidence:
    source_id: str
    source_url: str
    summary: str
    confidence: float
    id: UUID = field(default_factory=uuid4)
    source_record_key: str | None = None
    collected_at: datetime = field(default_factory=utc_now)
    published_at: datetime | None = None
    observed_at: datetime | None = None
    content_hash_sha256: str | None = None
    raw_storage_uri: str | None = None
    raw_storage_permitted: bool = False
    retention_until: datetime | None = None

    def __post_init__(self) -> None:
        if not self.source_id.strip():
            raise ValueError("source_id is required")
        if not _is_http_url(self.source_url):
            raise ValueError("source_url must use http or https")
        if not self.summary.strip():
            raise ValueError("summary is required")
        if len(self.summary) > 4_000:
            raise ValueError("summary cannot exceed 4000 characters")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")
        object.__setattr__(
            self,
            "collected_at",
            require_aware_utc(self.collected_at, field_name="collected_at"),
        )
        for field_name in ("published_at", "observed_at", "retention_until"):
            value = getattr(self, field_name)
            if value is not None:
                object.__setattr__(
                    self,
                    field_name,
                    require_aware_utc(value, field_name=field_name),
                )
        if self.content_hash_sha256 is not None and not fullmatch(
            r"[0-9a-f]{64}",
            self.content_hash_sha256,
        ):
            raise ValueError("content_hash_sha256 must be a lowercase SHA-256 digest")
        if self.raw_storage_uri is not None and not self.raw_storage_permitted:
            raise ValueError("raw_storage_uri requires raw_storage_permitted")
        if self.retention_until is not None and self.retention_until <= self.collected_at:
            raise ValueError("retention_until must be later than collected_at")


def _is_http_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.hostname)
