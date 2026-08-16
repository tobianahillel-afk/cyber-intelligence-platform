from __future__ import annotations

from typing import Any, cast

import pytest

from cip.adapters.sources.public_web import artifact_screenshot
from cip.adapters.sources.public_web.artifact_policy import BrowserArtifactPolicyError
from cip.modules.public_footprint.domain.artifacts import BrowserScreenshotMode
from cip.modules.public_footprint.domain.browser_actions import (
    BrowserActionKind,
    BrowserActionStep,
)


class _Locator:
    def __init__(
        self,
        *,
        count: int = 1,
        kind: str = "div",
        attributes: dict[str, str] | None = None,
        descendants: int = 0,
    ) -> None:
        self._count = count
        self.kind = kind
        self.attributes = attributes or {}
        self.descendants = descendants
        self.screenshot_called = False

    def count(self) -> int:
        return self._count

    def get_attribute(self, name: str) -> str | None:
        return self.attributes.get(name)

    def locator(self, query: str) -> _Locator:
        if query == "xpath=self::input":
            return _Locator(count=int(self.kind == "input"), kind="input")
        if query == "xpath=self::iframe":
            return _Locator(count=int(self.kind == "iframe"), kind="iframe")
        return _Locator(count=self.descendants)

    def screenshot(self, *, type: str) -> bytes:
        assert type == "png"
        self.screenshot_called = True
        return b"element"


class _Page:
    def __init__(self, root: _Locator) -> None:
        self.root = root
        self.page_screenshot_called = False

    def locator(self, selector: str) -> _Locator:
        assert selector == "html"
        return self.root

    def screenshot(self, *, type: str, full_page: bool) -> bytes:
        assert type == "png"
        assert full_page is False
        self.page_screenshot_called = True
        return b"viewport"


def _viewport() -> BrowserActionStep:
    return BrowserActionStep(
        "shot",
        BrowserActionKind.SCREENSHOT,
        screenshot_mode=BrowserScreenshotMode.VIEWPORT,
    )


def _element() -> BrowserActionStep:
    return BrowserActionStep(
        "shot",
        BrowserActionKind.SCREENSHOT,
        selector="#evidence",
        screenshot_mode=BrowserScreenshotMode.ELEMENT,
    )


def test_capture_scope_rejects_invalid_mode_and_document_root() -> None:
    invalid = cast(Any, type("Step", (), {"screenshot_mode": None})())
    with pytest.raises(BrowserArtifactPolicyError, match="mode_invalid"):
        artifact_screenshot._capture_scope(cast(Any, _Page(_Locator())), invalid)

    with pytest.raises(BrowserArtifactPolicyError, match="document_root_invalid"):
        artifact_screenshot._capture_scope(
            cast(Any, _Page(_Locator(count=0))),
            _viewport(),
        )


def test_capture_png_uses_element_or_viewport_path() -> None:
    locator = _Locator()
    page = _Page(_Locator())

    assert artifact_screenshot._capture_png(
        cast(Any, page),
        cast(Any, locator),
        _element(),
    ) == b"element"
    assert locator.screenshot_called

    assert artifact_screenshot._capture_png(
        cast(Any, page),
        cast(Any, locator),
        _viewport(),
    ) == b"viewport"
    assert page.page_screenshot_called


@pytest.mark.parametrize(
    ("kind", "attributes"),
    [
        ("div", {"data-captcha": "1"}),
        ("div", {"data-sensitive": "TRUE"}),
        ("input", {"type": "file"}),
        ("input", {"type": "password"}),
        ("input", {"autocomplete": "one-time-code"}),
        ("input", {"name": "public_OTP_code"}),
        ("iframe", {"src": "/public/captcha/challenge"}),
        ("iframe", {"title": "Captcha challenge"}),
    ],
)
def test_sensitive_root_shapes_are_denied(
    kind: str,
    attributes: dict[str, str],
) -> None:
    locator = _Locator(kind=kind, attributes=attributes)
    assert artifact_screenshot._scope_itself_is_sensitive(cast(Any, locator)) is True
    with pytest.raises(BrowserArtifactPolicyError, match="sensitive_surface_denied"):
        artifact_screenshot._deny_sensitive_capture(cast(Any, locator))


def test_non_sensitive_root_is_allowed_but_sensitive_descendant_is_denied() -> None:
    normal = _Locator(kind="input", attributes={"type": "text", "name": "query"})
    assert artifact_screenshot._scope_itself_is_sensitive(cast(Any, normal)) is False
    artifact_screenshot._deny_sensitive_capture(cast(Any, normal))

    descendant = _Locator(descendants=1)
    with pytest.raises(BrowserArtifactPolicyError, match="sensitive_surface_denied"):
        artifact_screenshot._deny_sensitive_capture(cast(Any, descendant))
