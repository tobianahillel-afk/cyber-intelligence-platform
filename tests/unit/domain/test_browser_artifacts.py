from __future__ import annotations

from datetime import UTC, datetime, timedelta
from hashlib import sha256
from uuid import uuid4

import pytest

from cip.modules.public_footprint.domain.artifacts import (
    BrowserArtifactKind,
    BrowserArtifactState,
    BrowserEvidenceArtifact,
    BrowserScreenshotMode,
)
from cip.modules.public_footprint.domain.browser_actions import (
    BrowserActionKind,
    BrowserActionStep,
    BrowserStepReplayPolicy,
)

NOW = datetime(2026, 8, 16, 18, 0, tzinfo=UTC)
DIGEST = sha256(b"artifact").hexdigest()


def _screenshot_artifact(**overrides: object) -> BrowserEvidenceArtifact:
    values: dict[str, object] = {
        "source_id": "public-web",
        "provider_id": "fixture-provider",
        "target_id": "fixture-target",
        "job_id": uuid4(),
        "plan_id": uuid4(),
        "plan_version": 1,
        "step_id": "shot",
        "kind": BrowserArtifactKind.SCREENSHOT,
        "state": BrowserArtifactState.PROCESSED,
        "page_url": "https://example.com/public",
        "source_url": "https://example.com/public",
        "captured_at": NOW,
        "content_hash_sha256": DIGEST,
        "byte_size": 123,
        "media_type": "image/png",
        "source_locator": "browser-action:plan:1:shot",
        "raw_retention_allowed": False,
        "screenshot_mode": BrowserScreenshotMode.VIEWPORT,
        "viewport_width": 800,
        "viewport_height": 600,
    }
    values.update(overrides)
    return BrowserEvidenceArtifact(**values)  # type: ignore[arg-type]


def _download_artifact(**overrides: object) -> BrowserEvidenceArtifact:
    values: dict[str, object] = {
        "source_id": "public-web",
        "provider_id": "fixture-provider",
        "target_id": "fixture-target",
        "job_id": uuid4(),
        "plan_id": uuid4(),
        "plan_version": 1,
        "step_id": "download",
        "kind": BrowserArtifactKind.DOWNLOAD,
        "state": BrowserArtifactState.PROCESSED,
        "page_url": "https://example.com/public",
        "source_url": "https://example.com/public/report.txt",
        "captured_at": NOW,
        "content_hash_sha256": DIGEST,
        "byte_size": 123,
        "media_type": "text/plain",
        "source_locator": "browser-action:plan:1:download",
        "raw_retention_allowed": False,
        "original_filename": "report.txt",
        "extracted_text_hash_sha256": sha256(b"text").hexdigest(),
        "excerpt": "public text",
    }
    values.update(overrides)
    return BrowserEvidenceArtifact(**values)  # type: ignore[arg-type]


def test_screenshot_action_shapes_are_typed() -> None:
    viewport = BrowserActionStep(
        "shot",
        BrowserActionKind.SCREENSHOT,
        screenshot_mode=BrowserScreenshotMode.VIEWPORT,
    )
    element = BrowserActionStep(
        "element-shot",
        BrowserActionKind.SCREENSHOT,
        selector="#evidence",
        screenshot_mode=BrowserScreenshotMode.ELEMENT,
        retain_raw_artifact=True,
    )

    assert viewport.selector is None
    assert element.selector == "#evidence"
    assert element.retain_raw_artifact is True


def test_screenshot_action_rejects_invalid_scope_shape() -> None:
    with pytest.raises(ValueError, match="element screenshot requires selector"):
        BrowserActionStep(
            "shot",
            BrowserActionKind.SCREENSHOT,
            screenshot_mode=BrowserScreenshotMode.ELEMENT,
        )
    with pytest.raises(ValueError, match="viewport screenshot cannot declare selector"):
        BrowserActionStep(
            "shot",
            BrowserActionKind.SCREENSHOT,
            selector="#x",
            screenshot_mode=BrowserScreenshotMode.VIEWPORT,
        )


def test_download_action_requires_expected_url_and_safe_replay() -> None:
    step = BrowserActionStep(
        "download",
        BrowserActionKind.DOWNLOAD,
        selector="a#report",
        expected_download_url="https://example.com/public/report.pdf",
        retain_raw_artifact=True,
    )

    assert step.expected_download_url.endswith("report.pdf")
    with pytest.raises(ValueError, match="expected_download_url"):
        BrowserActionStep("download", BrowserActionKind.DOWNLOAD, selector="a#report")
    with pytest.raises(ValueError, match="safe replay"):
        BrowserActionStep(
            "download",
            BrowserActionKind.DOWNLOAD,
            selector="a#report",
            expected_download_url="https://example.com/public/report.pdf",
            replay_policy=BrowserStepReplayPolicy.VERIFY_BEFORE_REPLAY,
        )


def test_non_artifact_action_cannot_request_raw_retention() -> None:
    with pytest.raises(ValueError, match="retain_raw_artifact"):
        BrowserActionStep(
            "click",
            BrowserActionKind.CLICK,
            selector="button",
            retain_raw_artifact=True,
        )


def test_processed_screenshot_has_deterministic_identity() -> None:
    plan_id = uuid4()
    first = _screenshot_artifact(plan_id=plan_id)
    second = _screenshot_artifact(plan_id=plan_id, job_id=uuid4())

    assert first.identity_key == second.identity_key
    assert first.media_type == "image/png"


def test_artifact_core_identity_hash_size_and_media_guards() -> None:
    for field_name in ("source_id", "provider_id", "target_id", "step_id"):
        with pytest.raises(ValueError, match=field_name):
            _screenshot_artifact(**{field_name: " "})
    with pytest.raises(ValueError, match="plan_version"):
        _screenshot_artifact(plan_version=0)
    with pytest.raises(ValueError, match="content_hash_sha256"):
        _screenshot_artifact(content_hash_sha256="bad")
    with pytest.raises(ValueError, match="extracted_text_hash_sha256"):
        _download_artifact(extracted_text_hash_sha256="bad")
    with pytest.raises(ValueError, match="byte_size"):
        _screenshot_artifact(byte_size=0)
    with pytest.raises(ValueError, match="media_type"):
        _screenshot_artifact(media_type="invalid")
    with pytest.raises(ValueError, match="source_locator"):
        _screenshot_artifact(source_locator="")


def test_artifact_optional_strings_and_retention_time_are_bounded() -> None:
    with pytest.raises(ValueError, match="storage_uri"):
        _screenshot_artifact(storage_uri=" ")
    with pytest.raises(ValueError, match="element_selector"):
        _screenshot_artifact(element_selector=" ")
    with pytest.raises(ValueError, match="original_filename"):
        _download_artifact(original_filename="x" * 501)
    with pytest.raises(ValueError, match="excerpt"):
        _download_artifact(excerpt="x" * 1_001)
    with pytest.raises(ValueError, match="retention_until"):
        _screenshot_artifact(retention_until=NOW)


def test_raw_retention_requires_policy_storage_and_deadline() -> None:
    with pytest.raises(ValueError, match="retention is not allowed"):
        _screenshot_artifact(raw_retained=True, storage_uri="s3://bucket/object")
    with pytest.raises(ValueError, match="storage_uri and retention_until"):
        _screenshot_artifact(raw_retention_allowed=True, raw_retained=True)
    with pytest.raises(ValueError, match="storage_uri requires"):
        _screenshot_artifact(storage_uri="s3://bucket/unretained")

    retained = _screenshot_artifact(
        raw_retention_allowed=True,
        raw_retained=True,
        storage_uri="s3://bucket/object",
        retention_until=NOW + timedelta(days=7),
    )
    assert retained.raw_retained is True


def test_screenshot_artifact_shape_is_strict() -> None:
    with pytest.raises(ValueError, match="PNG media type"):
        _screenshot_artifact(media_type="text/plain")
    with pytest.raises(ValueError, match="positive dimensions"):
        _screenshot_artifact(viewport_width=0)
    with pytest.raises(ValueError, match="element_selector"):
        _screenshot_artifact(
            screenshot_mode=BrowserScreenshotMode.ELEMENT,
            element_selector=None,
        )
    with pytest.raises(ValueError, match="cannot declare element_selector"):
        _screenshot_artifact(element_selector="#unexpected")
    with pytest.raises(ValueError, match="cannot declare download fields"):
        _screenshot_artifact(original_filename="shot.png")


def test_rejected_artifact_cannot_retain_raw_bytes() -> None:
    with pytest.raises(ValueError, match="rejection_reason"):
        _screenshot_artifact(state=BrowserArtifactState.REJECTED)
    with pytest.raises(ValueError, match="cannot retain raw bytes"):
        _screenshot_artifact(
            state=BrowserArtifactState.REJECTED,
            rejection_reason="unsafe",
            raw_retention_allowed=True,
            raw_retained=True,
            storage_uri="s3://bucket/object",
            retention_until=NOW + timedelta(days=1),
        )
    with pytest.raises(ValueError, match="processed artifact"):
        _screenshot_artifact(rejection_reason="not allowed for processed")


def test_download_artifact_rejects_screenshot_fields() -> None:
    with pytest.raises(ValueError, match="download artifact cannot declare screenshot fields"):
        _screenshot_artifact(kind=BrowserArtifactKind.DOWNLOAD, media_type="application/pdf")
    with pytest.raises(ValueError, match="download artifact cannot declare screenshot fields"):
        _download_artifact(element_selector="#wrong")
