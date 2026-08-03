from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from re import fullmatch
from urllib.parse import urlparse
from uuid import UUID, uuid4

from cip.modules.source_governance.domain.models import DataCategory
from cip.shared.kernel.time import require_aware_utc, utc_now


@dataclass(frozen=True, slots=True)
class RawObservation:
    source_id: str
    adapter_id: str
    adapter_version: str
    collection_job_id: UUID
    source_record_type: str
    source_url: str
    payload_hash_sha256: str
    data_categories: frozenset[DataCategory]
    id: UUID = field(default_factory=uuid4)
    source_record_key: str | None = None
    collected_at: datetime = field(default_factory=utc_now)
    observed_at: datetime | None = None
    published_at: datetime | None = None
    source_updated_at: datetime | None = None
    payload_reference: str | None = None
    schema_fingerprint: str | None = None
    content_language: str | None = None
    classification: str = "internal"
    retention_until: datetime | None = None

    def __post_init__(self) -> None:
        for name in ("source_id", "adapter_id", "adapter_version", "source_record_type"):
            if not str(getattr(self, name)).strip():
                raise ValueError(f"{name} is required")
        parsed = urlparse(self.source_url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise ValueError("source_url must use http or https")
        if not fullmatch(r"[0-9a-f]{64}", self.payload_hash_sha256):
            raise ValueError("payload_hash_sha256 must be a lowercase SHA-256 digest")
        if not self.data_categories:
            raise ValueError("at least one data category is required")
        object.__setattr__(
            self,
            "collected_at",
            require_aware_utc(self.collected_at, field_name="collected_at"),
        )
        for field_name in (
            "observed_at",
            "published_at",
            "source_updated_at",
            "retention_until",
        ):
            value = getattr(self, field_name)
            if value is not None:
                object.__setattr__(
                    self,
                    field_name,
                    require_aware_utc(value, field_name=field_name),
                )
        if self.retention_until is not None and self.retention_until <= self.collected_at:
            raise ValueError("retention_until must be later than collected_at")

    @property
    def deduplication_key(self) -> str:
        record_key = self.source_record_key or ""
        return f"{self.source_id}:{record_key}:{self.payload_hash_sha256}"
