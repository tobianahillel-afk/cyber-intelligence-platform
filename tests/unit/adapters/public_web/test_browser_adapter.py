from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import httpx
import pytest

from cip.adapters.sources.public_web.checkpoint import PublicWebCheckpoint
from cip.adapters.sources.public_web.client import (
    PublicWebPolicyDeniedError,
    PublicWebResponseError,
)
from cip.adapters.sources.public_web.collection_policy import PublicWebCollectionDeniedError
from cip.adapters.sources.public_web.collector import PublicWebCollectionBatch
from cip.adapters.sources.public_web.parsing import PublicWebParseError
from cip.adapters.sources.public_web.registry import PublicWebTarget
from cip.modules.collection_orchestration.application import public_web_browser_adapter as subject
from cip.modules.collection_orchestration.application.ports import AdapterExecutionError
from cip.modules.source_governance.domain.models import (
    AuthorizationStatus,
    DataCategory,
    SourceAuthorization,
    SourcePolicy,
    SourceStatus,
    SourceType,
)
from cip.modules.source_governance.infrastructure.registry import SourceRegistryEntry

_NOW = datetime(2026, 8, 13, 12, tzinfo=UTC)


def test_adapter_requires_matching_browser_policy_and_positive_timeout() -> None:
    target = _target()
    with pytest.raises(ValueError, match="matching source"):
        subject.PublicWebBrowserAdapter(_entry(source_id="other"), target)
    with pytest.raises(ValueError, match="browser source policy"):
        subject.PublicWebBrowserAdapter(_entry(source_type=SourceType.STATIC_HTTP), target)
    with pytest.raises(ValueError, match="timeout_seconds"):
        subject.PublicWebBrowserAdapter(_entry(), target, timeout_seconds=0)


def test_adapter_returns_canonical_batch_and_browser_provenance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: dict[str, object] = {}
    expected = PublicWebCollectionBatch(
        observations=(),
        projections=(),
        checkpoint=PublicWebCheckpoint(pages={}),
        not_modified=True,
    )

    def fake_collect(*_args: object, **kwargs: object) -> PublicWebCollectionBatch:
        seen.update(kwargs)
        return expected

    monkeypatch.setattr(subject, "collect_public_web_target", fake_collect)
    result = _collect(subject.PublicWebBrowserAdapter(_entry(), _target()))

    assert result.observations == ()
    assert result.public_footprint_projections == ()
    assert result.not_modified
    assert result.checkpoint_payload == {"pages": {}, "feed_urls": []}
    assert seen["adapter_id"] == "public-web-browser"


def test_adapter_maps_invalid_checkpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    def invalid(_payload: object) -> PublicWebCheckpoint:
        raise subject.PublicWebCheckpointError("bad checkpoint")

    monkeypatch.setattr(subject, "load_checkpoint", invalid)
    error = _collect_error(subject.PublicWebBrowserAdapter(_entry(), _target()))
    assert (error.error_code, error.retryable) == ("invalid_checkpoint", False)


@pytest.mark.parametrize(
    ("exc", "code", "retryable"),
    [
        (PublicWebCollectionDeniedError("denied"), "source_policy_denied", False),
        (PublicWebPolicyDeniedError("denied"), "source_policy_denied", False),
        (PublicWebParseError("schema"), "source_schema_drift", False),
        (PublicWebResponseError("unsafe"), "unsafe_source_response", True),
        (
            httpx.ConnectError(
                "offline",
                request=httpx.Request("GET", "https://example.com/app"),
            ),
            "source_transport_error",
            True,
        ),
    ],
)
def test_adapter_maps_collection_errors(
    monkeypatch: pytest.MonkeyPatch,
    exc: Exception,
    code: str,
    retryable: bool,
) -> None:
    monkeypatch.setattr(subject, "collect_public_web_target", _raiser(exc))
    error = _collect_error(subject.PublicWebBrowserAdapter(_entry(), _target()))
    assert (error.error_code, error.retryable) == (code, retryable)


@pytest.mark.parametrize(("status", "retryable"), [(400, False), (429, True), (503, True)])
def test_adapter_maps_http_status_retryability(
    monkeypatch: pytest.MonkeyPatch,
    status: int,
    retryable: bool,
) -> None:
    request = httpx.Request("GET", "https://example.com/app")
    response = httpx.Response(status, request=request)
    monkeypatch.setattr(
        subject,
        "collect_public_web_target",
        _raiser(httpx.HTTPStatusError("status", request=request, response=response)),
    )
    error = _collect_error(subject.PublicWebBrowserAdapter(_entry(), _target()))
    assert (error.error_code, error.retryable) == (f"http_{status}", retryable)


def _collect(adapter: subject.PublicWebBrowserAdapter):
    return adapter.collect(
        collection_job_id=uuid4(),
        checkpoint_payload=None,
        collected_at=_NOW,
        retention_until=_NOW + timedelta(days=30),
    )


def _collect_error(adapter: subject.PublicWebBrowserAdapter) -> AdapterExecutionError:
    with pytest.raises(AdapterExecutionError) as raised:
        _collect(adapter)
    return raised.value


def _raiser(exc: Exception):
    def raise_error(*_args: object, **_kwargs: object) -> PublicWebCollectionBatch:
        raise exc

    return raise_error


def _target() -> PublicWebTarget:
    return PublicWebTarget(
        id="browser-test",
        organization_id=uuid4(),
        canonical_name="Browser Test",
        base_url="https://example.com/",
        seed_urls=("https://example.com/app",),
        sitemap_urls=(),
        feed_urls=(),
        discover_security_txt=False,
        discover_sitemaps=False,
        discover_feeds=False,
        allowed_path_prefixes=("/",),
        enabled=True,
        authorization_reference="browser-test-approval",
        authorization_reviewed_at=_NOW,
        max_link_depth=0,
        max_pages=1,
        max_total_bytes=20_000,
        max_resource_bytes=10_000,
        max_redirects=2,
    )


def _entry(
    *,
    source_id: str = "browser-test",
    source_type: SourceType = SourceType.BROWSER,
) -> SourceRegistryEntry:
    return SourceRegistryEntry(
        policy=SourcePolicy(
            id=source_id,
            name="Browser Test",
            base_url="https://example.com/",
            status=SourceStatus.ENABLED,
            source_type=source_type,
            owner="tests",
            licence="Controlled browser test source",
            allowed_data_categories=frozenset(
                {
                    DataCategory.OFFICIAL_DOCUMENT_DISCOVERY,
                    DataCategory.TECHNOLOGY_OBSERVATION,
                }
            ),
            retention_days=30,
            raw_content_storage=False,
            human_review_required=False,
        ),
        authorization=SourceAuthorization(
            status=AuthorizationStatus.APPROVED,
            document_reference="browser-test-approval",
            reviewed_at=_NOW,
            approved_hosts=frozenset({"example.com"}),
            approved_path_prefixes=("/",),
            approved_purposes=frozenset({"corporate-public-footprint"}),
            automated_collection_allowed=True,
            raw_storage_allowed=False,
        ),
        economics={"monthly_cost": 0},
    )
