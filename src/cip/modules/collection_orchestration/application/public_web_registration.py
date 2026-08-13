from __future__ import annotations

from cip.adapters.sources.public_web.registry import PublicWebTarget
from cip.modules.collection_orchestration.application.ports import CollectionAdapter
from cip.modules.collection_orchestration.application.public_web_adapter import PublicWebAdapter
from cip.modules.collection_orchestration.application.public_web_browser_adapter import (
    PublicWebBrowserAdapter,
)
from cip.modules.source_governance.domain.models import SourceType
from cip.modules.source_governance.infrastructure.registry import SourceRegistryEntry


def register_public_web_adapters(
    adapters: dict[tuple[str, str], CollectionAdapter],
    entries_by_id: dict[str, SourceRegistryEntry],
    targets: tuple[PublicWebTarget, ...],
    *,
    timeout_seconds: float,
) -> None:
    for target in targets:
        if not target.enabled:
            continue
        entry = entries_by_id.get(target.id)
        if entry is None:
            raise ValueError(
                f"enabled public web target has no source policy: {target.id}"
            )
        if entry.policy.source_type is SourceType.STATIC_HTTP:
            adapter: CollectionAdapter = PublicWebAdapter(
                entry,
                target,
                timeout_seconds=timeout_seconds,
            )
        elif entry.policy.source_type is SourceType.BROWSER:
            adapter = PublicWebBrowserAdapter(
                entry,
                target,
                timeout_seconds=timeout_seconds,
            )
        else:
            raise ValueError(
                f"public web target {target.id} has unsupported source type "
                f"{entry.policy.source_type.value}"
            )
        adapters[(adapter.source_id, adapter.adapter_id)] = adapter
