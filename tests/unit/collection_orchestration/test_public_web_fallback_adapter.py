from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

import httpx
import pytest

from cip.adapters.sources.public_web.browser_fallback import BrowserFallbackPolicy
from cip.adapters.sources.public_web.checkpoint import PublicWebCheckpointError
from cip.adapters.sources.public_web.client import (
    PublicWebPolicyDeniedError,
    PublicWebResponseError,
)
from cip.adapters.sources.public_web.collection_policy import (
    PublicWebCollectionDeniedError,
)
from cip.adapters.sources.public_web.parsing import PublicWebParseError
from cip.adapters.sources.public_web.registry import PublicWebTarget
from cip.modules.collection_orchestration.application import (
    public_web_fallback_adapter,
    public_web_fallback_collection,
    public_web_fallback_execution,
)
from cip.modules.collection_orchestration.application.ports import (
    AdapterCollectionBatch,
    AdapterExecutionError,
)
from cip.modules.collection_orchestration.application.public_web_fallback_adapter import (
    PublicWebFallbackAdapter,
)
from cip.modules.collection_orchestration.application.public_web_fallback_context import (
    PublicWebFallbackRunContext,
)
from cip.modules.source_governance.domain.models import (
    AuthorizationStatus,
    DataCategory,
    SourceAuthorization,
    SourcePolicy,
    SourceStatus,
    SourceType,
)
from cip.modules.source_governance.infrastructure.registry import SourceRegistryEntry

_NOW = datetime(2026, 8, 13, 18, tzinfo=UTC)
_POLICY = BrowserFallbackPolicy(min_static_text_chars=100, max_browser_pages=2)


def test_adapter_validates_governed_inputs() -> None:
    target = _target()
    with pytest.raises(ValueError, match="static source identity"):
        PublicWebFallbackAdapter(
            _entry(SourceType.STATIC_HTTP, "other-static"),
            _entry(SourceType.BROWSER, "browser-source"),
            target,
            fallback_policy=_POLICY,
        )
    with pytest.raises(ValueError, match="explicit browser source policy"):
        PublicWebFallbackAdapter(
            _entry(SourceType.STATIC_HTTP, target.source_id or target.id),
            _entry(SourceType.STATIC_HTTP, "not-browser"),
            target,
            fallback_policy=_POLICY,
        )
    with pytest.raises(ValueError, match="timeout_seconds must be positive"):
        PublicWebFallbackAdapter(
            _entry(SourceType.STATIC_HTTP, target.source_id or target.id),
            _entry(SourceType.BROWSER, "browser-source"),
            target,
            fallback_policy=_POLICY,
            timeout_seconds=0,
        )


def test_adapter_collect_delegates_with_run_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = _target()
    expected = AdapterCollectionBatch(
        observations=(),
        checkpoint_payload={"ok": True},
        not_modified=False,
    )
    captured: dict[str, object] = {}

    def fake_execute(*args: object, **kwargs: object) -> AdapterCollectionBatch:
        captured.update(kwargs)
        return expected

    monkeypatch.setattr(
        public_web_fallback_adapter,
        "execute_public_web_fallback",
        fake_execute,
    )
    adapter = PublicWebFallbackAdapter(
        _entry(SourceType.STATIC_HTTP, target.source_id or target.id),
        _entry(SourceType.BROWSER, "browser-source"),
        target,
        fallback_policy=_POLICY,
        timeout_seconds=7.0,
    )
    job_id = uuid4()
    result = adapter.collect(
        collection_job_id=job_id,
        checkpoint_payload={"pages": {}, "feed_urls": []},
        collected_at=_NOW,
        retention_until=_NOW + timedelta(days=30),
    )

    assert result is expected
    run = captured["run"]
    assert isinstance(run, PublicWebFallbackRunContext)
    assert run.collection_job_id == job_id
    assert run.timeout_seconds == 7.0
    assert run.adapter_id == adapter.adapter_id


def test_execution_returns_canonical_batch(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(public_web_fallback_execution, "load_checkpoint", lambda payload: None)
    monkeypatch.setattr(
        public_web_fallback_execution,
        "collect_with_browser_fallback",
        lambda *args, **kwargs: SimpleNamespace(
            observations=(),
            checkpoint=object(),
            not_modified=True,
            projections=(),
        ),
    )
    monkeypatch.setattr(
        public_web_fallback_execution,
        "dump_checkpoint",
        lambda checkpoint: {"dumped": True},
    )
    batch = _execute()
    assert batch.observations == ()
    assert batch.not_modified is True
    assert batch.checkpoint_payload == {"dumped": True}
    assert batch.public_footprint_projections == ()


def test_execution_maps_invalid_checkpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    def bad_checkpoint(payload: object) -> None:
        raise PublicWebCheckpointError("bad checkpoint")

    monkeypatch.setattr(public_web_fallback_execution, "load_checkpoint", bad_checkpoint)
    error = _raised_execution_error()
    assert error.error_code == "invalid_checkpoint"
    assert error.retryable is False


@pytest.mark.parametrize(
    ("source_error", "error_code", "retryable"),
    [
        (PublicWebCollectionDeniedError("denied"), "source_policy_denied", False),
        (PublicWebPolicyDeniedError("robots"), "source_policy_denied", False),
        (PublicWebParseError("schema"), "source_schema_drift", False),
        (PublicWebResponseError("unsafe"), "unsafe_source_response", True),
        (httpx.ReadTimeout("timeout"), "source_transport_error", True),
    ],
)
def test_execution_maps_source_errors(
    monkeypatch: pytest.MonkeyPatch,
    source_error: Exception,
    error_code: str,
    retryable: bool,
) -> None:
    _raise_from_collection(monkeypatch, source_error)
    error = _raised_execution_error()
    assert error.error_code == error_code
    assert error.retryable is retryable


@pytest.mark.parametrize(("status", "retryable"), [(404, False), (429, True), (503, True)])
def test_execution_maps_http_status(
    monkeypatch: pytest.MonkeyPatch,
    status: int,
    retryable: bool,
) -> None:
    request = httpx.Request("GET", "https://example.com/")
    response = httpx.Response(status, request=request)
    _raise_from_collection(
        monkeypatch,
        httpx.HTTPStatusError("status", request=request, response=response),
    )
    error = _raised_execution_error()
    assert error.error_code == f"http_{status}"
    assert error.retryable is retryable


def test_collection_helper_uses_fallback_client_and_collector(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = _target()
    static_entry = _entry(SourceType.STATIC_HTTP, target.source_id or target.id)
    browser_entry = _entry(SourceType.BROWSER, "browser-source")
    run = _run()
    sentinel = object()
    seen: dict[str, object] = {}

    class FakeFallbackClient:
        def __init__(
            self,
            client: httpx.Client,
            entry: SourceRegistryEntry,
            **kwargs: object,
        ) -> None:
            seen["entry"] = entry
            seen["client"] = client

    def fake_collect(
        client: object,
        entry: object,
        actual_target: object,
        **kwargs: object,
    ):
        seen["adapter_id"] = kwargs["adapter_id"]
        seen["target"] = actual_target
        return sentinel

    monkeypatch.setattr(
        public_web_fallback_collection,
        "FallbackPublicWebClient",
        FakeFallbackClient,
    )
    monkeypatch.setattr(
        public_web_fallback_collection,
        "collect_public_web_target",
        fake_collect,
    )
    result = public_web_fallback_collection.collect_with_browser_fallback(
        static_entry,
        browser_entry,
        target,
        policy=_POLICY,
        checkpoint=None,
        run=run,
    )
    assert result is sentinel
    assert seen["entry"] is browser_entry
    assert seen["target"] is target
    assert seen["adapter_id"] == run.adapter_id


def _raise_from_collection(monkeypatch: pytest.MonkeyPatch, error: Exception) -> None:
    monkeypatch.setattr(public_web_fallback_execution, "load_checkpoint", lambda payload: None)

    def raising(*args: object, **kwargs: object) -> None:
        raise error

    monkeypatch.setattr(
        public_web_fallback_execution,
        "collect_with_browser_fallback",
        raising,
    )


def _raised_execution_error() -> AdapterExecutionError:
    with pytest.raises(AdapterExecutionError) as caught:
        _execute()
    return caught.value


def _execute() -> AdapterCollectionBatch:
    target = _target()
    return public_web_fallback_execution.execute_public_web_fallback(
        _entry(SourceType.STATIC_HTTP, target.source_id or target.id),
        _entry(SourceType.BROWSER, "browser-source"),
        target,
        policy=_POLICY,
        checkpoint_payload=None,
        run=_run(),
    )


def _run() -> PublicWebFallbackRunContext:
    return PublicWebFallbackRunContext(
        collection_job_id=uuid4(),
        collected_at=_NOW,
        retention_until=_NOW + timedelta(days=30),
        timeout_seconds=5.0,
        transport=httpx.MockTransport(lambda request: httpx.Response(200, request=request)),
        adapter_id="public-web-browser-fallback",
    )


def _target() -> PublicWebTarget:
    return PublicWebTarget(
        id="fallback-target",
        source_id="static-source",
        organization_id=uuid4(),
        canonical_name="Fallback Test",
        base_url="https://example.com/",
        seed_urls=("https://example.com/",),
        sitemap_urls=(),
        feed_urls=(),
        discover_security_txt=False,
        discover_sitemaps=False,
        discover_feeds=False,
        allowed_path_prefixes=("/",),
        enabled=True,
        authorization_reference="static-approval",
        authorization_reviewed_at=_NOW,
        max_link_depth=0,
        max_pages=3,
        max_total_bytes=1_000_000,
        max_resource_bytes=100_000,
        max_redirects=1,
    )


def _entry(source_type: SourceType, source_id: str) -> SourceRegistryEntry:
    return SourceRegistryEntry(
        policy=SourcePolicy(
            id=source_id,
            name="Fallback Test",
            base_url="https://example.com/",
            status=SourceStatus.ENABLED,
            source_type=source_type,
            owner="tests",
            licence="Controlled test source",
            allowed_data_categories=frozenset(
                {DataCategory.OFFICIAL_DOCUMENT_DISCOVERY}
            ),
            retention_days=30,
            raw_content_storage=False,
            human_review_required=False,
        ),
        authorization=SourceAuthorization(
            status=AuthorizationStatus.APPROVED,
            document_reference="approval",
            reviewed_at=_NOW,
            approved_hosts=frozenset({"example.com"}),
            approved_path_prefixes=("/",),
            approved_purposes=frozenset({"corporate-public-footprint"}),
            automated_collection_allowed=True,
            raw_storage_allowed=False,
        ),
        economics={"monthly_cost": 0},
    )
