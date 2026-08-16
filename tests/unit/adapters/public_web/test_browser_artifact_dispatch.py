from __future__ import annotations

from typing import Any, cast

import pytest

from cip.adapters.sources.public_web import artifact_runtime
from cip.adapters.sources.public_web.artifact_policy import BrowserArtifactPolicyError
from cip.adapters.sources.public_web.artifact_runtime import (
    BrowserArtifactRuntimeState,
    execute_artifact_step,
)
from cip.modules.public_footprint.domain.artifacts import BrowserScreenshotMode
from cip.modules.public_footprint.domain.browser_actions import (
    BrowserActionKind,
    BrowserActionStep,
)


def _shot() -> BrowserActionStep:
    return BrowserActionStep(
        "shot",
        BrowserActionKind.SCREENSHOT,
        screenshot_mode=BrowserScreenshotMode.VIEWPORT,
    )


def _download() -> BrowserActionStep:
    return BrowserActionStep(
        "download",
        BrowserActionKind.DOWNLOAD,
        selector="a#report",
        expected_download_url="https://example.com/public/report.txt",
    )


def test_artifact_dispatch_requires_execution_context() -> None:
    with pytest.raises(BrowserArtifactPolicyError, match="context_required"):
        execute_artifact_step(
            cast(Any, object()),
            cast(Any, object()),
            cast(Any, object()),
            cast(Any, object()),
            _shot(),
            None,
            BrowserArtifactRuntimeState(),
            timeout_ms=1_000,
        )


def test_artifact_dispatch_appends_screenshot(monkeypatch: pytest.MonkeyPatch) -> None:
    artifact = cast(Any, object())
    monkeypatch.setattr(
        artifact_runtime,
        "capture_governed_screenshot",
        lambda *args, **kwargs: artifact,
    )
    state = BrowserArtifactRuntimeState()

    execute_artifact_step(
        cast(Any, object()),
        cast(Any, object()),
        cast(Any, object()),
        cast(Any, object()),
        _shot(),
        cast(Any, object()),
        state,
        timeout_ms=1_000,
    )

    assert state.artifacts == [artifact]
    assert state.projections == []


def test_artifact_dispatch_appends_download_projection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    artifact = cast(Any, object())
    projection = cast(Any, object())
    monkeypatch.setattr(
        artifact_runtime,
        "collect_governed_download",
        lambda *args, **kwargs: (artifact, projection),
    )
    state = BrowserArtifactRuntimeState()

    execute_artifact_step(
        cast(Any, object()),
        cast(Any, object()),
        cast(Any, object()),
        cast(Any, object()),
        _download(),
        cast(Any, object()),
        state,
        timeout_ms=987,
    )

    assert state.artifacts == [artifact]
    assert state.projections == [projection]


def test_artifact_dispatch_rejects_non_artifact_kind() -> None:
    step = cast(Any, type("Step", (), {"kind": BrowserActionKind.CLICK})())
    with pytest.raises(BrowserArtifactPolicyError, match="action_kind_invalid"):
        execute_artifact_step(
            cast(Any, object()),
            cast(Any, object()),
            cast(Any, object()),
            cast(Any, object()),
            step,
            cast(Any, object()),
            BrowserArtifactRuntimeState(),
            timeout_ms=1_000,
        )
