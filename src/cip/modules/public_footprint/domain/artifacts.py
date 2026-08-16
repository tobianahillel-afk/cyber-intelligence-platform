from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from hashlib import sha256
from re import fullmatch
from uuid import UUID, uuid4

from cip.modules.public_footprint.domain.url_identity import CanonicalUrl
from cip.shared.kernel.time import require_aware_utc

_MAX_IDENTITY = 200
_MAX_SELECTOR = 1_000
_MAX_FILENAME = 500
_MAX_MEDIA_TYPE = 200
_MAX_REASON = 500
_MAX_EXCERPT = 1_000


class BrowserArtifactKind(StrEnum):
    SCREENSHOT = "screenshot"
    DOWNLOAD = "download"


class BrowserArtifactState(StrEnum):
    PROCESSED = "processed"
    REJECTED = "rejected"


class BrowserScreenshotMode(StrEnum):
    VIEWPORT = "viewport"
    ELEMENT = "element"


@dataclass(frozen=True, slots=True)
class BrowserEvidenceArtifact:
    source_id: str
    provider_id: str
    target_id: str
    job_id: UUID
    plan_id: UUID
    plan_version: int
    step_id: str
    kind: BrowserArtifactKind
    state: BrowserArtifactState
    page_url: str
    source_url: str
    captured_at: datetime
    content_hash_sha256: str
    byte_size: int
    media_type: str
    source_locator: str
    raw_retention_allowed: bool
    raw_retained: bool = False
    storage_uri: str | None = None
    retention_until: datetime | None = None
    screenshot_mode: BrowserScreenshotMode | None = None
    viewport_width: int | None = None
    viewport_height: int | None = None
    element_selector: str | None = None
    original_filename: str | None = None
    extracted_text_hash_sha256: str | None = None
    excerpt: str | None = None
    rejection_reason: str | None = None
    id: UUID = field(default_factory=uuid4)

    def __post_init__(self) -> None:
        for field_name in ("source_id", "provider_id", "target_id", "step_id"):
            _bounded_required(getattr(self, field_name), field_name, _MAX_IDENTITY)
        if self.plan_version < 1:
            raise ValueError("artifact plan_version must be positive")
        page_url = CanonicalUrl(self.page_url).value
        source_url = CanonicalUrl(self.source_url).value
        captured_at = require_aware_utc(self.captured_at, field_name="captured_at")
        _require_hash(self.content_hash_sha256, "content_hash_sha256")
        extracted_hash = self.extracted_text_hash_sha256
        if extracted_hash is not None:
            _require_hash(extracted_hash, "extracted_text_hash_sha256")
        if self.byte_size < 1:
            raise ValueError("artifact byte_size must be positive")
        media_type = self.media_type.split(";", 1)[0].strip().casefold()
        if "/" not in media_type or len(media_type) > _MAX_MEDIA_TYPE:
            raise ValueError("artifact media_type is invalid")
        _bounded_required(self.source_locator, "source_locator", _MAX_FILENAME)
        _optional_bounded(self.storage_uri, "storage_uri", 2_048)
        _optional_bounded(self.element_selector, "element_selector", _MAX_SELECTOR)
        _optional_bounded(self.original_filename, "original_filename", _MAX_FILENAME)
        _optional_bounded(self.excerpt, "excerpt", _MAX_EXCERPT)
        _optional_bounded(self.rejection_reason, "rejection_reason", _MAX_REASON)
        retention_until = self.retention_until
        if retention_until is not None:
            retention_until = require_aware_utc(retention_until, field_name="retention_until")
            if retention_until <= captured_at:
                raise ValueError("artifact retention_until must follow captured_at")
        _validate_retention(self)
        _validate_kind_shape(self)
        _validate_state_shape(self)
        object.__setattr__(self, "page_url", page_url)
        object.__setattr__(self, "source_url", source_url)
        object.__setattr__(self, "captured_at", captured_at)
        object.__setattr__(self, "media_type", media_type)
        object.__setattr__(self, "retention_until", retention_until)

    @property
    def identity_key(self) -> str:
        material = (
            f"{self.plan_id}\0{self.plan_version}\0{self.step_id}\0"
            f"{self.kind.value}\0{self.content_hash_sha256}"
        )
        return sha256(material.encode("utf-8")).hexdigest()


def _validate_retention(artifact: BrowserEvidenceArtifact) -> None:
    if artifact.raw_retained and not artifact.raw_retention_allowed:
        raise ValueError("raw artifact cannot be retained when retention is not allowed")
    if artifact.raw_retained and (artifact.storage_uri is None or artifact.retention_until is None):
        raise ValueError("retained raw artifact requires storage_uri and retention_until")
    if not artifact.raw_retained and artifact.storage_uri is not None:
        raise ValueError("storage_uri requires raw_retained")


def _validate_kind_shape(artifact: BrowserEvidenceArtifact) -> None:
    if artifact.kind is BrowserArtifactKind.SCREENSHOT:
        if artifact.media_type != "image/png" or artifact.screenshot_mode is None:
            raise ValueError("screenshot artifact requires PNG media type and screenshot mode")
        if not artifact.viewport_width or not artifact.viewport_height:
            raise ValueError("screenshot artifact requires positive dimensions")
        if artifact.screenshot_mode is BrowserScreenshotMode.ELEMENT and artifact.element_selector is None:
            raise ValueError("element screenshot requires element_selector")
        if artifact.screenshot_mode is BrowserScreenshotMode.VIEWPORT and artifact.element_selector is not None:
            raise ValueError("viewport screenshot cannot declare element_selector")
        if artifact.original_filename is not None or artifact.extracted_text_hash_sha256 is not None:
            raise ValueError("screenshot artifact cannot declare download fields")
        return
    if artifact.screenshot_mode is not None or artifact.viewport_width is not None:
        raise ValueError("download artifact cannot declare screenshot fields")
    if artifact.viewport_height is not None or artifact.element_selector is not None:
        raise ValueError("download artifact cannot declare screenshot fields")


def _validate_state_shape(artifact: BrowserEvidenceArtifact) -> None:
    if artifact.state is BrowserArtifactState.PROCESSED:
        if artifact.rejection_reason is not None:
            raise ValueError("processed artifact cannot declare rejection_reason")
        return
    if artifact.rejection_reason is None:
        raise ValueError("rejected artifact requires rejection_reason")
    if artifact.raw_retained:
        raise ValueError("rejected artifact cannot retain raw bytes")


def _require_hash(value: str, field_name: str) -> None:
    if fullmatch(r"[0-9a-f]{64}", value) is None:
        raise ValueError(f"{field_name} must be a lowercase SHA-256 digest")


def _bounded_required(value: str, field_name: str, maximum: int) -> None:
    if not value.strip() or len(value) > maximum or "\x00" in value:
        raise ValueError(f"{field_name} is invalid")


def _optional_bounded(value: str | None, field_name: str, maximum: int) -> None:
    if value is not None and (not value.strip() or len(value) > maximum or "\x00" in value):
        raise ValueError(f"{field_name} is invalid")
