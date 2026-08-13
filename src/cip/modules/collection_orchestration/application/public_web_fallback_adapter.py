from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from uuid import UUID

import httpx

from cip.adapters.sources.public_web.browser_fallback import (
    BrowserFallbackPolicy,
    FallbackPublicWebClient,
)
from cip.adapters.sources.public_web.checkpoint import (
    PublicWebCheckpointError,
    dump_checkpoint,
    load_checkpoint,
)
from cip.adapters.sources.public_web.client import (
    PublicWebPolicyDeniedError,
    PublicWebResponseError,
)
from cip.adapters.sources.public_web.collection_policy import PublicWebCollectionDeniedError
from cip.adapters.sources.public_web.collector import collect_public_web_target
from cip.adapters.sources.public_web.parsing import PublicWebParseError
from cip.adapters.sources.public_web.registry import PublicWebTarget
from cip.modules.collection_orchestration.application.ports import (
    AdapterCollectionBatch,
    AdapterExecutionError,
)
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
