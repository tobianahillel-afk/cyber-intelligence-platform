from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePosixPath
from urllib.parse import urlsplit

from cip.adapters.sources.public_web.client_contract import OCTET_STREAM_MIME_TYPE
from cip.adapters.sources.public_web.ooxml_parsing import (
    DOCX_MIME,
    PPTX_MIME,
    XLSX_MIME,
    detect_ooxml_mime,
)

PDF_MIME = "application/pdf"
TEXT_MIME = "text/plain"
PNG_MIME = "image/png"
_ALLOWED_DOWNLOAD_MIMES = frozenset({PDF_MIME, TEXT_MIME, DOCX_MIME, XLSX_MIME, PPTX_MIME})
_EXPECTED_EXTENSIONS = {
    PDF_MIME: frozenset({".pdf"}),
    TEXT_MIME: frozenset({".txt", ".csv", ".log", ".md"}),
    DOCX_MIME: frozenset({".docx"}),
    XLSX_MIME: frozenset({".xlsx"}),
    PPTX_MIME: frozenset({".pptx"}),
}
_EXECUTABLE_MAGICS = (
    b"MZ",
    b"\x7fELF",
    b"\xfe\xed\xfa\xce",
    b"\xce\xfa\xed\xfe",
    b"\xfe\xed\xfa\xcf",
    b"\xcf\xfa\xed\xfe",
)


class BrowserArtifactPolicyError(RuntimeError):
    """A browser evidence artifact violated a bounded admission rule."""


@dataclass(frozen=True, slots=True)
class BrowserArtifactLimits:
    max_screenshots: int = 4
    max_screenshot_bytes: int = 5_000_000
    max_downloads: int = 4
    max_artifact_bytes: int = 5_000_000
    max_total_download_bytes: int = 10_000_000
    max_redirects: int = 3
    request_timeout_seconds: float = 30.0

    def __post_init__(self) -> None:
        if not 1 <= self.max_screenshots <= 16:
            raise ValueError("max_screenshots must be between 1 and 16")
        if not 1 <= self.max_downloads <= 16:
            raise ValueError("max_downloads must be between 1 and 16")
        for field_name in (
            "max_screenshot_bytes",
            "max_artifact_bytes",
            "max_total_download_bytes",
        ):
            if not 1 <= getattr(self, field_name) <= 100_000_000:
                raise ValueError(f"{field_name} must be between 1 and 100000000")
        if self.max_artifact_bytes > self.max_total_download_bytes:
            raise ValueError("max_artifact_bytes cannot exceed aggregate download budget")
        if not 0 <= self.max_redirects <= 10:
            raise ValueError("max_redirects must be between 0 and 10")
        if not 0.1 <= self.request_timeout_seconds <= 120.0:
            raise ValueError("request_timeout_seconds must be between 0.1 and 120")


@dataclass(slots=True)
class BrowserArtifactUsage:
    screenshots_started: int = 0
    downloads_started: int = 0
    download_bytes: int = 0

    def begin_screenshot(self, limits: BrowserArtifactLimits) -> None:
        if self.screenshots_started >= limits.max_screenshots:
            raise BrowserArtifactPolicyError("browser_screenshot_count_budget_exceeded")
        self.screenshots_started += 1

    def admit_screenshot_bytes(self, content: bytes, limits: BrowserArtifactLimits) -> None:
        if not content or len(content) > limits.max_screenshot_bytes:
            raise BrowserArtifactPolicyError("browser_screenshot_byte_budget_exceeded")

    def begin_download(self, limits: BrowserArtifactLimits) -> int:
        if self.downloads_started >= limits.max_downloads:
            raise BrowserArtifactPolicyError("browser_download_count_budget_exceeded")
        remaining = limits.max_total_download_bytes - self.download_bytes
        if remaining <= 0:
            raise BrowserArtifactPolicyError("browser_download_total_byte_budget_exceeded")
        self.downloads_started += 1
        return min(limits.max_artifact_bytes, remaining)

    def admit_download_bytes(self, content: bytes, limits: BrowserArtifactLimits) -> None:
        total = self.download_bytes + len(content)
        if total > limits.max_total_download_bytes:
            raise BrowserArtifactPolicyError("browser_download_total_byte_budget_exceeded")
        self.download_bytes = total


def validate_download_media_type(url: str, reported_mime: str, body: bytes) -> str:
    if not body:
        raise BrowserArtifactPolicyError("browser_download_empty_artifact")
    if any(body.startswith(magic) for magic in _EXECUTABLE_MAGICS):
        raise BrowserArtifactPolicyError("browser_download_executable_denied")
    normalized = reported_mime.split(";", 1)[0].strip().casefold()
    path = urlsplit(url).path
    if normalized == OCTET_STREAM_MIME_TYPE:
        normalized = _detect_octet_stream_type(path, body)
    if normalized not in _ALLOWED_DOWNLOAD_MIMES:
        raise BrowserArtifactPolicyError("browser_download_mime_not_allowed")
    _validate_magic(normalized, body)
    _validate_extension(path, normalized)
    return normalized


def quarantine_suffix(media_type: str) -> str:
    return sorted(_EXPECTED_EXTENSIONS[media_type])[0]


def original_filename(url: str) -> str | None:
    name = PurePosixPath(urlsplit(url).path).name
    return name[:500] or None


def _detect_octet_stream_type(path: str, body: bytes) -> str:
    if body.startswith(b"%PDF-") and path.casefold().endswith(".pdf"):
        return PDF_MIME
    detected = detect_ooxml_mime(body, url_path=path)
    if detected is not None:
        return detected
    raise BrowserArtifactPolicyError("browser_download_octet_stream_type_unknown")


def _validate_magic(media_type: str, body: bytes) -> None:
    if media_type == PDF_MIME and not body.startswith(b"%PDF-"):
        raise BrowserArtifactPolicyError("browser_download_pdf_magic_mismatch")
    if media_type in {DOCX_MIME, XLSX_MIME, PPTX_MIME} and not body.startswith(b"PK"):
        raise BrowserArtifactPolicyError("browser_download_ooxml_magic_mismatch")
    if media_type == TEXT_MIME and b"\x00" in body[:8_192]:
        raise BrowserArtifactPolicyError("browser_download_text_contains_nul")


def _validate_extension(path: str, media_type: str) -> None:
    suffix = PurePosixPath(path).suffix.casefold()
    if not suffix:
        return
    if suffix not in _EXPECTED_EXTENSIONS[media_type]:
        raise BrowserArtifactPolicyError("browser_download_extension_mismatch")
