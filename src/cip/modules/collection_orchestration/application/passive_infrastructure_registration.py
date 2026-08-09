from __future__ import annotations

from collections.abc import Callable

from cip.adapters.sources.passive_infrastructure.registry import PassiveInfrastructureTarget
from cip.modules.collection_orchestration.application.certspotter_adapter import (
    CertSpotterAdapter,
)
from cip.modules.collection_orchestration.application.cloudflare_dns_adapter import (
    CloudflareDnsAdapter,
)
from cip.modules.collection_orchestration.application.ports import CollectionAdapter
from cip.modules.source_governance.infrastructure.registry import SourceRegistryEntry


def register_passive_infrastructure_adapters(
    adapters: dict[tuple[str, str], CollectionAdapter],
    entries_by_id: dict[str, SourceRegistryEntry],
    targets: tuple[PassiveInfrastructureTarget, ...],
    *,
    certspotter_token_provider: Callable[[], str | None],
    timeout_seconds: float,
) -> None:
    cloudflare_entry = entries_by_id.get(CloudflareDnsAdapter.source_id)
    if cloudflare_entry is not None:
        _register(
            adapters,
            CloudflareDnsAdapter(
                cloudflare_entry,
                targets,
                timeout_seconds=timeout_seconds,
            ),
        )

    certspotter_entry = entries_by_id.get(CertSpotterAdapter.source_id)
    if certspotter_entry is not None:
        _register(
            adapters,
            CertSpotterAdapter(
                certspotter_entry,
                targets,
                token_provider=certspotter_token_provider,
                timeout_seconds=timeout_seconds,
            ),
        )


def _register(
    adapters: dict[tuple[str, str], CollectionAdapter],
    adapter: CollectionAdapter,
) -> None:
    adapters[(adapter.source_id, adapter.adapter_id)] = adapter
