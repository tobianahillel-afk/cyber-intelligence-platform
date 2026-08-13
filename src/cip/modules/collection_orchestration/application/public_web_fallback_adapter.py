from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from uuid import UUID

import httpx

from cip.adapters.sources.public_web.browser_fallback import BrowserFallbackPolicy
from cip.adapters.sources.public_web.registry import PublicWebTarget
from cip.modules.collection_orchestration.application.ports import AdapterCollectionBatch
from cip.modules.collection_orchestration.application.public_web_fallback_execution import execute_public_web_fallback
from cip.modules.source_governance.domain.models import DataCategory, SourceType
from cip.modules.source_governance.infrastructure.registry import SourceRegistryEntry


class PublicWebFallbackAdapter:
    adapter_id = "public-web-browser-fallback"
    data_category = DataCategory.OFFICIAL_DOCUMENT_DISCOVERY

    def __init__(
        self,
        static_entry: SourceRegistryEntry,
        browser_entry: SourceRegistryEntry,
        target: PublicWebTarget,
        *,
        fallback_policy: BrowserFallbackPolicy,
        timeout_seconds: float = 30.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        if static_entry.policy.id != target.source_id:
            raise ValueError("fallback adapter requires matching static source identity")
        if browser_entry.policy.source_type is not SourceType.BROWSER:
            raise ValueError("fallback adapter requires an explicit browser source policy")
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        self.source_id = target.id
        self._static_entry = static_entry
        self._browser_entry = browser_entry
        self._target = target
        self._fallback_policy = fallback_policy
        self._timeout_seconds = timeout_seconds
        self._transport = transport

    def collect(
        self,
        *,
        collection_job_id: UUID,
        checkpoint_payload: Mapping[str, object] | None,
        collected_at: datetime,
        retention_until: datetime,
    ) -> AdapterCollectionBatch:
        return execute_public_web_fallback(
            self._static_entry,
            self._browser_entry,
            self._target,
            policy=self._fallback_policy,
            collection_job_id=collection_job_id,
            checkpoint_payload=checkpoint_payload,
            collected_at=collected_at,
            retention_until=retention_until,
            timeout_seconds=self._timeout_seconds,
            transport=self._transport,
            adapter_id=self.adapter_id,
        )
