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


def test_raw_retention_requires_policy_storage_and_deadline() -> None:
    with pytest.raises(ValueError, match="retention is not allowed"):
        _screenshot_artifact(raw_retained=True, storage_uri="s3://bucket/object")
    with pytest.raises(ValueError, match="storage_uri and retention_until"):
        _screenshot_artifact(raw_retention_allowed=True, raw_retained=True)

    retained = _screenshot_artifact(
        raw_retention_allowed=True,
        raw_retained=True,
        storage_uri="s3://bucket/object",
        retention_until=NOW + timedelta(days=7),
    )
    assert retained.raw_retained is True


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


def test_download_artifact_rejects_screenshot_fields() -> None:
    with pytest.raises(ValueError, match="download artifact cannot declare screenshot fields"):
        _screenshot_artifact(kind=BrowserArtifactKind.DOWNLOAD, media_type="application/pdf")
