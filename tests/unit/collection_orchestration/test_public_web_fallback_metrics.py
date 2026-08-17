from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import cast
from uuid import uuid4

import pytest

from cip.adapters.sources.public_web.browser_fallback import BrowserFallbackPolicy
from cip.adapters.sources.public_web.collector_state import (
    PublicWebCheckpoint,
    PublicWebCollectionBatch,
)
from cip.adapters.sources.public_web.crawl_runtime import CrawlTelemetry
from cip.adapters.sources.public_web.registry import PublicWebTarget
from cip.modules.collection_orchestration.application import public_web_fallback_execution
from cip.modules.collection_orchestration.application.ports import AdapterPartialExecutionError
from cip.modules.collection_orchestration.application.public_web_fallback_context import (
    PublicWebFallbackRunContext,
)
from cip.modules.source_governance.infrastructure.registry import SourceRegistryEntry

_NOW = datetime(2026, 8, 17, 12, tzinfo=UTC)


def test_fallback_exposes_crawl_operational_metrics(monkeypatch: pytest.MonkeyPatch) -> None:
    batch = _batch(deadline_exceeded=False)
    monkeypatch.setattr(
        public_web_fallback_execution,
        "collect_with_browser_fallback",
        lambda *args, **kwargs: batch,
    )

    result = _execute()

    assert result.operational_metrics is not None
    assert result.operational_metrics.namespace == "public_web.crawl.v1"
    assert result.operational_metrics.values["fetched_pages"] == 2
    assert result.operational_metrics.values["browser_fallback_count"] == 1
    assert result.operational_metrics.values["effective_concurrency"] == 2


def test_fallback_preserves_partial_deadline_batch(monkeypatch: pytest.MonkeyPatch) -> None:
    batch = _batch(deadline_exceeded=True)
    monkeypatch.setattr(
        public_web_fallback_execution,
        "collect_with_browser_fallback",
        lambda *args, **kwargs: batch,
    )

    with pytest.raises(AdapterPartialExecutionError) as captured:
        _execute()

    error = captured.value
    assert error.error_code == "crawl_deadline_exceeded"
    assert error.retryable
    assert error.batch.operational_metrics is not None
    assert error.batch.operational_metrics.values["deadline_exceeded"] is True


def _execute():
    run = PublicWebFallbackRunContext(
        collection_job_id=uuid4(),
        collected_at=_NOW,
        retention_until=_NOW + timedelta(days=1),
        timeout_seconds=5.0,
        transport=None,
        adapter_id="public-web-browser-fallback",
    )
    return public_web_fallback_execution.execute_public_web_fallback(
        cast(SourceRegistryEntry, object()),
        cast(SourceRegistryEntry, object()),
        cast(PublicWebTarget, object()),
        policy=cast(BrowserFallbackPolicy, object()),
        checkpoint_payload=None,
        run=run,
    )


def _batch(*, deadline_exceeded: bool) -> PublicWebCollectionBatch:
    return PublicWebCollectionBatch(
        observations=(),
        projections=(),
        checkpoint=PublicWebCheckpoint(pages={}),
        not_modified=False,
        telemetry=CrawlTelemetry(
            attempted_pages=2,
            fetched_pages=2,
            bytes_received=256,
            bytes_accepted=240,
            browser_fallback_count=1,
            elapsed_seconds=0.5,
            deadline_exceeded=deadline_exceeded,
            configured_concurrency=2,
            effective_concurrency=2,
            max_concurrency_used=2,
        ),
    )
