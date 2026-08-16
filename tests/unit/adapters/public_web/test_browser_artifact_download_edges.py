from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any, cast

import httpx
import pytest

from cip.adapters.sources.public_web import artifact_download
from cip.adapters.sources.public_web.artifact_policy import (
    BrowserArtifactLimits,
    BrowserArtifactPolicyError,
)
from cip.adapters.sources.public_web.client_contract import PublicWebResponseError
from cip.modules.public_footprint.domain.browser_actions import (
    BrowserActionKind,
    BrowserActionStep,
)

NOW = datetime(2026, 8, 16, 20, 30, tzinfo=UTC)
URL = "https://example.com/public/report.txt"


class _SelfLocator:
    def __init__(self, count: int) -> None:
        self._count = count

    def count(self) -> int:
        return self._count


class _Link:
    def __init__(self, *, is_link: bool = True, href: str | None = URL) -> None:
        self.is_link = is_link
        self.href = href

    def locator(self, query: str) -> _SelfLocator:
        assert query == "xpath=self::a"
        return _SelfLocator(int(self.is_link))

    def get_attribute(self, name: str) -> str | None:
        assert name == "href"
        return self.href


def _step(expected: str = URL) -> BrowserActionStep:
    return BrowserActionStep(
        "download",
        BrowserActionKind.DOWNLOAD,
        selector="a#report",
        expected_download_url=expected,
    )


def _context(client: httpx.Client, *, max_redirects: int = 1) -> Any:
    return SimpleNamespace(
        captured_at=NOW,
        download_client=client,
        limits=BrowserArtifactLimits(max_redirects=max_redirects),
    )


def test_download_preflight_denies_non_link_missing_href_and_plan_mismatch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for link, match in (
        (_Link(is_link=False), "must_resolve_to_link"),
        (_Link(href=None), "missing_href"),
        (_Link(href=URL), "does_not_match_plan"),
    ):
        monkeypatch.setattr(
            artifact_download,
            "exact_locator",
            lambda *_args, current_link=link: current_link,
        )
        expected = (
            "https://example.com/public/other.txt"
            if match == "does_not_match_plan"
            else URL
        )
        with pytest.raises(BrowserArtifactPolicyError, match=match):
            artifact_download._preflight_download(
                cast(Any, object()),
                cast(Any, object()),
                cast(Any, object()),
                cast(Any, object()),
                _step(expected),
                cast(Any, SimpleNamespace(captured_at=NOW)),
            )


def test_download_preflight_authorizes_exact_link(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(artifact_download, "exact_locator", lambda *_args: _Link())
    seen: list[str] = []

    def authorize(*_args: object, **_kwargs: object) -> str:
        seen.append(URL)
        return URL

    monkeypatch.setattr(artifact_download, "authorize_browser_action_transition", authorize)
    result = artifact_download._preflight_download(
        cast(Any, object()),
        cast(Any, object()),
        cast(Any, object()),
        cast(Any, object()),
        _step(),
        cast(Any, SimpleNamespace(captured_at=NOW)),
    )
    assert result == URL
    assert seen == [URL]


def test_download_redirect_requires_location(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        artifact_download,
        "authorize_browser_action_transition",
        lambda *_args, **_kwargs: URL,
    )
    client = httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(302, request=request)
        )
    )
    try:
        with pytest.raises(PublicWebResponseError, match="omitted Location"):
            artifact_download._fetch_download(
                cast(Any, SimpleNamespace(max_redirects=1)),
                cast(Any, object()),
                cast(Any, object()),
                URL,
                _context(client),
                max_bytes=100,
                timeout_ms=1_000,
            )
    finally:
        client.close()


def test_download_redirect_budget_is_bounded(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        artifact_download,
        "authorize_browser_action_transition",
        lambda *_args, **_kwargs: URL,
    )
    client = httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                302,
                headers={"location": "/public/report.txt"},
                request=request,
            )
        )
    )
    try:
        with pytest.raises(BrowserArtifactPolicyError, match="redirect_budget"):
            artifact_download._fetch_download(
                cast(Any, SimpleNamespace(max_redirects=1)),
                cast(Any, object()),
                cast(Any, object()),
                URL,
                _context(client, max_redirects=1),
                max_bytes=100,
                timeout_ms=1_000,
            )
    finally:
        client.close()


def test_download_parser_fails_closed_for_unrouted_media_type() -> None:
    with pytest.raises(BrowserArtifactPolicyError, match="parser_unavailable"):
        artifact_download._parse_download(b"payload", media_type="application/x-unknown")
