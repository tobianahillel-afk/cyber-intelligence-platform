from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import httpx
import pytest

from cip.adapters.sources.public_web.artifact_context import BrowserArtifactExecutionContext
from cip.adapters.sources.public_web.artifact_policy import BrowserArtifactPolicyError
from cip.adapters.sources.public_web.artifact_retention import retain_artifact_if_requested
from cip.modules.public_footprint.domain.artifacts import BrowserScreenshotMode
from cip.modules.public_footprint.domain.browser_actions import (
    BrowserActionKind,
    BrowserActionPlan,
    BrowserActionStep,
    BrowserHttpMethod,
    BrowserTransitionRule,
)
from cip.modules.source_governance.domain.models import (
    AuthorizationStatus,
    DataCategory,
    HttpMethod,
    SourceAuthorization,
    SourcePolicy,
    SourceStatus,
    SourceType,
)
from cip.modules.source_governance.infrastructure.registry import SourceRegistryEntry

NOW = datetime(2026, 8, 16, 19, 0, tzinfo=UTC)
URL = "https://example.com/public/page"


class _Store:
    def __init__(self, uri: str = "s3://evidence/object") -> None:
        self.uri = uri
        self.calls: list[tuple[str, bytes, str]] = []

    def put(self, *, object_key: str, content: bytes, media_type: str) -> str:
        self.calls.append((object_key, content, media_type))
        return self.uri


def _entry(*, raw_allowed: bool) -> SourceRegistryEntry:
    return SourceRegistryEntry(
        policy=SourcePolicy(
            id="public-web",
            name="Public Web",
            base_url="https://example.com/",
            status=SourceStatus.ENABLED,
            source_type=SourceType.BROWSER,
            owner="tests",
            licence="controlled fixture",
            allowed_data_categories=frozenset({DataCategory.OFFICIAL_DOCUMENT_DISCOVERY}),
            human_review_required=False,
            raw_content_storage=raw_allowed,
        ),
        authorization=SourceAuthorization(
            status=AuthorizationStatus.APPROVED,
            document_reference="L14-test-approval",
            reviewed_at=NOW,
            approved_hosts=frozenset({"example.com"}),
            approved_path_prefixes=("/public",),
            approved_purposes=frozenset({"corporate-public-footprint"}),
            approved_http_methods=frozenset({HttpMethod.GET}),
            automated_collection_allowed=True,
            raw_storage_allowed=raw_allowed,
        ),
        economics={"monthly_cost": 0},
    )


def _plan(*, retain: bool) -> tuple[BrowserActionPlan, BrowserActionStep]:
    step = BrowserActionStep(
        "shot",
        BrowserActionKind.SCREENSHOT,
        screenshot_mode=BrowserScreenshotMode.VIEWPORT,
        retain_raw_artifact=retain,
    )
    plan = BrowserActionPlan(
        plan_id=uuid4(),
        version=1,
        source_id="public-web",
        provider_id="fixture",
        target_id="public-web",
        purpose="corporate-public-footprint",
        steps=(step,),
        allowed_transitions=(
            BrowserTransitionRule(
                host="example.com",
                path_prefix="/public",
                methods=frozenset({BrowserHttpMethod.GET}),
            ),
        ),
        max_actions=1,
        max_total_value_chars=0,
    )
    return plan, step


def _context(store: _Store | None) -> BrowserArtifactExecutionContext:
    transport = httpx.MockTransport(lambda _request: httpx.Response(500))
    return BrowserArtifactExecutionContext(
        job_id=uuid4(),
        captured_at=NOW,
        retention_until=NOW + timedelta(days=7),
        download_client=httpx.Client(transport=transport),
        store=store,
    )


def test_raw_retention_allowed_and_requested_uses_store() -> None:
    store = _Store()
    plan, step = _plan(retain=True)
    context = _context(store)
    try:
        result = retain_artifact_if_requested(
            b"png",
            media_type="image/png",
            source_url=URL,
            entry=_entry(raw_allowed=True),
            plan=plan,
            step=step,
            context=context,
        )
    finally:
        context.download_client.close()

    assert result.allowed is True
    assert result.retained is True
    assert result.storage_uri == "s3://evidence/object"
    assert len(store.calls) == 1
    assert store.calls[0][0].startswith("browser-artifacts/public-web/")


def test_raw_retention_not_requested_remains_ephemeral() -> None:
    store = _Store()
    plan, step = _plan(retain=False)
    context = _context(store)
    try:
        result = retain_artifact_if_requested(
            b"png",
            media_type="image/png",
            source_url=URL,
            entry=_entry(raw_allowed=True),
            plan=plan,
            step=step,
            context=context,
        )
    finally:
        context.download_client.close()

    assert result.allowed is True
    assert result.retained is False
    assert store.calls == []


def test_raw_retention_request_fails_closed_when_policy_denies() -> None:
    plan, step = _plan(retain=True)
    context = _context(_Store())
    try:
        with pytest.raises(BrowserArtifactPolicyError, match="raw_retention_denied"):
            retain_artifact_if_requested(
                b"png",
                media_type="image/png",
                source_url=URL,
                entry=_entry(raw_allowed=False),
                plan=plan,
                step=step,
                context=context,
            )
    finally:
        context.download_client.close()


def test_raw_retention_request_requires_deployment_store() -> None:
    plan, step = _plan(retain=True)
    context = _context(None)
    try:
        with pytest.raises(BrowserArtifactPolicyError, match="store_unavailable"):
            retain_artifact_if_requested(
                b"png",
                media_type="image/png",
                source_url=URL,
                entry=_entry(raw_allowed=True),
                plan=plan,
                step=step,
                context=context,
            )
    finally:
        context.download_client.close()


def test_store_must_return_non_empty_uri() -> None:
    plan, step = _plan(retain=True)
    context = _context(_Store("  "))
    try:
        with pytest.raises(BrowserArtifactPolicyError, match="empty_uri"):
            retain_artifact_if_requested(
                b"png",
                media_type="image/png",
                source_url=URL,
                entry=_entry(raw_allowed=True),
                plan=plan,
                step=step,
                context=context,
            )
    finally:
        context.download_client.close()
