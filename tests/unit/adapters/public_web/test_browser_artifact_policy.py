from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from struct import pack
from uuid import uuid4

import httpx
import pytest

from cip.adapters.sources.public_web.artifact_context import BrowserArtifactExecutionContext
from cip.adapters.sources.public_web.artifact_policy import (
    BrowserArtifactLimits,
    BrowserArtifactPolicyError,
    BrowserArtifactUsage,
    original_filename,
    quarantine_suffix,
    validate_download_media_type,
)
from cip.adapters.sources.public_web.artifact_quarantine import quarantined_artifact
from cip.adapters.sources.public_web.artifact_screenshot import png_dimensions
from cip.adapters.sources.public_web.ooxml_parsing import DOCX_MIME

NOW = datetime(2026, 8, 16, 20, 0, tzinfo=UTC)


def test_artifact_limits_validate_cross_budget_constraints() -> None:
    with pytest.raises(ValueError, match="max_artifact_bytes cannot exceed"):
        BrowserArtifactLimits(max_artifact_bytes=10, max_total_download_bytes=9)
    for value in (0, 17):
        with pytest.raises(ValueError, match="max_screenshots"):
            BrowserArtifactLimits(max_screenshots=value)
        with pytest.raises(ValueError, match="max_downloads"):
            BrowserArtifactLimits(max_downloads=value)
    for field_name in (
        "max_screenshot_bytes",
        "max_artifact_bytes",
        "max_total_download_bytes",
    ):
        with pytest.raises(ValueError, match=field_name):
            BrowserArtifactLimits(**{field_name: 0})
    with pytest.raises(ValueError, match="max_redirects"):
        BrowserArtifactLimits(max_redirects=11)
    with pytest.raises(ValueError, match="request_timeout_seconds"):
        BrowserArtifactLimits(request_timeout_seconds=0)


def test_artifact_context_requires_future_retention_deadline() -> None:
    client = httpx.Client(transport=httpx.MockTransport(lambda _request: httpx.Response(500)))
    try:
        with pytest.raises(ValueError, match="retention_until must follow"):
            BrowserArtifactExecutionContext(
                job_id=uuid4(),
                captured_at=NOW,
                retention_until=NOW,
                download_client=client,
            )
        context = BrowserArtifactExecutionContext(
            job_id=uuid4(),
            captured_at=NOW,
            retention_until=NOW + timedelta(days=1),
            download_client=client,
        )
        assert context.captured_at == NOW
    finally:
        client.close()


def test_screenshot_usage_enforces_count_and_bytes() -> None:
    limits = BrowserArtifactLimits(max_screenshots=1, max_screenshot_bytes=3)
    usage = BrowserArtifactUsage()

    usage.begin_screenshot(limits)
    usage.admit_screenshot_bytes(b"png", limits)
    with pytest.raises(BrowserArtifactPolicyError, match="count_budget"):
        usage.begin_screenshot(limits)
    for body in (b"", b"toolarge"):
        with pytest.raises(BrowserArtifactPolicyError, match="byte_budget"):
            usage.admit_screenshot_bytes(body, limits)


def test_png_dimensions_reject_invalid_header_and_bounds() -> None:
    with pytest.raises(BrowserArtifactPolicyError, match="invalid_png"):
        png_dimensions(b"not-a-png")
    zero_width = b"\x89PNG\r\n\x1a\n" + b"\x00\x00\x00\rIHDR" + pack(">II", 0, 10)
    with pytest.raises(BrowserArtifactPolicyError, match="dimensions_invalid"):
        png_dimensions(zero_width)
    too_wide = b"\x89PNG\r\n\x1a\n" + b"\x00\x00\x00\rIHDR" + pack(">II", 20_001, 10)
    with pytest.raises(BrowserArtifactPolicyError, match="dimensions_invalid"):
        png_dimensions(too_wide)


def test_download_usage_enforces_count_and_aggregate_bytes() -> None:
    limits = BrowserArtifactLimits(
        max_downloads=2,
        max_artifact_bytes=4,
        max_total_download_bytes=5,
    )
    usage = BrowserArtifactUsage()

    assert usage.begin_download(limits) == 4
    usage.admit_download_bytes(b"1234", limits)
    assert usage.begin_download(limits) == 1
    usage.admit_download_bytes(b"5", limits)
    with pytest.raises(BrowserArtifactPolicyError, match="count_budget"):
        usage.begin_download(limits)

    exhausted = BrowserArtifactUsage(download_bytes=5)
    with pytest.raises(BrowserArtifactPolicyError, match="total_byte_budget"):
        exhausted.begin_download(limits)
    with pytest.raises(BrowserArtifactPolicyError, match="total_byte_budget"):
        BrowserArtifactUsage(download_bytes=4).admit_download_bytes(b"12", limits)


def test_pdf_type_requires_magic_and_consistent_extension() -> None:
    assert (
        validate_download_media_type(
            "https://example.com/report.pdf",
            "application/pdf; charset=binary",
            b"%PDF-1.7\nbody",
        )
        == "application/pdf"
    )
    with pytest.raises(BrowserArtifactPolicyError, match="pdf_magic_mismatch"):
        validate_download_media_type(
            "https://example.com/report.pdf",
            "application/pdf",
            b"not-pdf",
        )
    with pytest.raises(BrowserArtifactPolicyError, match="extension_mismatch"):
        validate_download_media_type(
            "https://example.com/report.exe",
            "application/pdf",
            b"%PDF-1.7\nbody",
        )


def test_octet_stream_requires_safe_detectable_type() -> None:
    assert (
        validate_download_media_type(
            "https://example.com/report.pdf",
            "application/octet-stream",
            b"%PDF-1.7\nbody",
        )
        == "application/pdf"
    )
    with pytest.raises(BrowserArtifactPolicyError, match="type_unknown"):
        validate_download_media_type(
            "https://example.com/download",
            "application/octet-stream",
            b"opaque",
        )


def test_empty_ooxml_magic_executable_and_unapproved_types_are_denied() -> None:
    with pytest.raises(BrowserArtifactPolicyError, match="empty_artifact"):
        validate_download_media_type("https://example.com/report.txt", "text/plain", b"")
    with pytest.raises(BrowserArtifactPolicyError, match="ooxml_magic_mismatch"):
        validate_download_media_type(
            "https://example.com/report.docx",
            DOCX_MIME,
            b"not-a-zip",
        )
    with pytest.raises(BrowserArtifactPolicyError, match="executable_denied"):
        validate_download_media_type(
            "https://example.com/report.txt",
            "text/plain",
            b"MZbinary",
        )
    with pytest.raises(BrowserArtifactPolicyError, match="mime_not_allowed"):
        validate_download_media_type(
            "https://example.com/image.png",
            "image/png",
            b"image",
        )
    with pytest.raises(BrowserArtifactPolicyError, match="text_contains_nul"):
        validate_download_media_type(
            "https://example.com/report.txt",
            "text/plain",
            b"hello\x00world",
        )
    assert (
        validate_download_media_type(
            "https://example.com/public/download",
            "text/plain",
            b"plain text",
        )
        == "text/plain"
    )


def test_filename_and_quarantine_suffix_are_bounded() -> None:
    assert original_filename("https://example.com/path/report.pdf?x=1") == "report.pdf"
    assert original_filename("https://example.com/") is None
    assert quarantine_suffix("application/pdf") == ".pdf"


def test_quarantine_is_private_and_removed_after_success() -> None:
    retained_path: Path | None = None
    with quarantined_artifact(b"safe bytes", suffix=".bin") as path:
        retained_path = path
        assert path.read_bytes() == b"safe bytes"
        assert path.exists()
        assert path.stat().st_mode & 0o777 == 0o600
    assert retained_path is not None
    assert not retained_path.exists()


def test_quarantine_is_removed_after_parser_failure() -> None:
    retained_path: Path | None = None
    with (
        pytest.raises(RuntimeError, match="parse failed"),
        quarantined_artifact(b"unsafe bytes", suffix=".bin") as path,
    ):
        retained_path = path
        raise RuntimeError("parse failed")
    assert retained_path is not None
    assert not retained_path.exists()


def test_quarantine_rejects_empty_or_unsafe_suffix() -> None:
    with (
        pytest.raises(ValueError, match="cannot be empty"),
        quarantined_artifact(b"", suffix=".bin"),
    ):
        pass
    with (
        pytest.raises(ValueError, match="suffix"),
        quarantined_artifact(b"x", suffix="../bad"),
    ):
        pass
