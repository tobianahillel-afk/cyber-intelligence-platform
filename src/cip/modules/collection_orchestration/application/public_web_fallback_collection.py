from __future__ import annotations

import httpx

from cip.adapters.sources.public_web.browser_fallback import (
    BrowserFallbackPolicy,
    FallbackPublicWebClient,
)
from cip.adapters.sources.public_web.collector import (
    PublicWebCheckpoint,
    PublicWebCollectionBatch,
    collect_public_web_target,
)
from cip.adapters.sources.public_web.registry import PublicWebTarget
from cip.modules.collection_orchestration.application.public_web_fallback_context import (
    PublicWebFallbackRunContext,
)
from cip.modules.source_governance.infrastructure.registry import SourceRegistryEntry


def collect_with_browser_fallback(
    static_entry: SourceRegistryEntry,
    browser_entry: SourceRegistryEntry,
    target: PublicWebTarget,
    *,
    policy: BrowserFallbackPolicy,
    checkpoint: PublicWebCheckpoint | None,
    run: PublicWebFallbackRunContext,
) -> PublicWebCollectionBatch:
    with httpx.Client(
        timeout=run.timeout_seconds,
        follow_redirects=False,
        transport=run.transport,
    ) as http_client:
        client = FallbackPublicWebClient(
            http_client,
            browser_entry,
            collected_at=run.collected_at,
            policy=policy,
        )
        return collect_public_web_target(
            client,
            static_entry,
            target,
            collection_job_id=run.collection_job_id,
            collected_at=run.collected_at,
            retention_until=run.retention_until,
            checkpoint=checkpoint,
            adapter_id=run.adapter_id,
        )
