from __future__ import annotations

from datetime import datetime
from uuid import UUID

import httpx

from cip.adapters.sources.public_web.browser_fallback import BrowserFallbackPolicy, FallbackPublicWebClient
from cip.adapters.sources.public_web.collector import PublicWebCheckpoint, PublicWebCollectionBatch, collect_public_web_target
from cip.adapters.sources.public_web.registry import PublicWebTarget
from cip.modules.source_governance.infrastructure.registry import SourceRegistryEntry


def collect_with_browser_fallback(
    static_entry: SourceRegistryEntry,
    browser_entry: SourceRegistryEntry,
    target: PublicWebTarget,
    *,
    policy: BrowserFallbackPolicy,
    collection_job_id: UUID,
    collected_at: datetime,
    retention_until: datetime,
    checkpoint: PublicWebCheckpoint | None,
    timeout_seconds: float,
    transport: httpx.BaseTransport | None,
    adapter_id: str,
) -> PublicWebCollectionBatch:
    with httpx.Client(
        timeout=timeout_seconds,
        follow_redirects=False,
        transport=transport,
    ) as http_client:
        client = FallbackPublicWebClient(
            http_client,
            browser_entry,
            collected_at=collected_at,
            policy=policy,
        )
        return collect_public_web_target(
            client,
            static_entry,
            target,
            collection_job_id=collection_job_id,
            collected_at=collected_at,
            retention_until=retention_until,
            checkpoint=checkpoint,
            adapter_id=adapter_id,
        )
