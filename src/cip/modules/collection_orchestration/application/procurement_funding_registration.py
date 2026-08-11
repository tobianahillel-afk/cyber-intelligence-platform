from __future__ import annotations

from cip.modules.collection_orchestration.application.ademe_funding_adapter import (
    AdemeFundingAdapter,
)
from cip.modules.collection_orchestration.application.place_awards_adapter import (
    PlaceAwardsAdapter,
)
from cip.modules.collection_orchestration.application.ports import CollectionAdapter
from cip.modules.source_governance.infrastructure.registry import SourceRegistryEntry


def register_procurement_funding_adapters(
    adapters: dict[tuple[str, str], CollectionAdapter],
    entries_by_id: dict[str, SourceRegistryEntry],
    *,
    timeout_seconds: float,
) -> None:
    for adapter_type in (PlaceAwardsAdapter, AdemeFundingAdapter):
        entry = entries_by_id.get(adapter_type.source_id)
        if entry is None:
            continue
        adapter = adapter_type(entry, timeout_seconds=timeout_seconds)
        identity = (adapter.source_id, adapter.adapter_id)
        if identity in adapters:
            raise ValueError(f"duplicate runtime adapter: {identity[0]}/{identity[1]}")
        adapters[identity] = adapter
