from __future__ import annotations

from pathlib import Path

import pytest

from cip.adapters.sources.public_web.artifact_policy import (
    BrowserArtifactLimits,
    BrowserArtifactPolicyError,
    BrowserArtifactUsage,
    original_filename,
    quarantine_suffix,
    validate_download_media_type,
)
from cip.adapters.sources.public_web.artifact_quarantine import quarantined_artifact


def test_artifact_limits_validate_cross_budget_constraints() -> None:
    with pytest.raises(ValueError, match="max_artifact_bytes cannot exceed"):
        BrowserArtifactLimits(max_artifact_bytes=10, max_total_download_bytes=9)
    with pytest.raises(ValueError, match="max_screenshots"):
        BrowserArtifactLimits(max_screenshots=0)
    with pytest.raises(ValueError, match="max_redirects"):
        BrowserArtifactLimits(max_redirects=11)
    with pytest.raises(ValueError, match="request_timeout_seconds"):
        BrowserArtifactLimits(request_timeout_seconds=0)


def test_screenshot_usage_enforces_count_and_bytes() -> None:
    limits = BrowserArtifactLimits(max_screenshots=1, max_screenshot_bytes=3)
    usage = BrowserArtifactUsage()

    usage.begin_screenshot(limits)
    usage.admit_screenshot_bytes(b"png", limits)
    with pytest.raises(BrowserArtifactPolicyError, match="count_budget"):
        usage.begin_screenshot(limits)
    with pytest.raises(BrowserArtifactPolicyError, match="byte_budget"):
        usage.admit_screenshot_bytes(b"toolarge", limits)


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


def test_executable_and_unapproved_types_are_denied() -> None:
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
    with pytest.raises(RuntimeError, match="parse failed"):
        with quarantined_artifact(b"unsafe bytes", suffix=".bin") as path:
            retained_path = path
            raise RuntimeError("parse failed")
    assert retained_path is not None
    assert not retained_path.exists()


def test_quarantine_rejects_empty_or_unsafe_suffix() -> None:
    with pytest.raises(ValueError, match="cannot be empty"):
        with quarantined_artifact(b"", suffix=".bin"):
            pass
    with pytest.raises(ValueError, match="suffix"):
        with quarantined_artifact(b"x", suffix="../bad"):
            pass
