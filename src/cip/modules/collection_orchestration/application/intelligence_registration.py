from __future__ import annotations

from collections.abc import Callable

from cip.adapters.sources.incident_catalogs.sec_registry import SecIncidentTarget
from cip.modules.collection_orchestration.application.phishtank_adapter import PhishTankAdapter
from cip.modules.collection_orchestration.application.ports import CollectionAdapter
from cip.modules.collection_orchestration.application.sec_incident_adapter import (
    SecCyberDisclosureAdapter,
)
from cip.modules.source_governance.infrastructure.registry import SourceRegistryEntry


def register_intelligence_adapters(
    adapters: dict[tuple[str, str], CollectionAdapter],
    entries_by_id: dict[str, SourceRegistryEntry],
    sec_targets: tuple[SecIncidentTarget, ...],
    *,
    phishtank_token_provider: Callable[[], str | None],
    sec_user_agent: str | None,
    phishtank_user_agent: str | None,
    timeout_seconds: float,
) -> None:
    sec_entry = entries_by_id.get(SecCyberDisclosureAdapter.source_id)
    if sec_entry is not None:
        _register(
            adapters,
            SecCyberDisclosureAdapter(
                sec_entry,
                sec_targets,
                user_agent=sec_user_agent,
                timeout_seconds=timeout_seconds,
            ),
        )

    phishtank_entry = entries_by_id.get(PhishTankAdapter.source_id)
    if phishtank_entry is not None:
        _register(
            adapters,
            PhishTankAdapter(
                phishtank_entry,
                token_provider=phishtank_token_provider,
                user_agent=phishtank_user_agent,
                timeout_seconds=timeout_seconds,
            ),
        )


def _register(
    adapters: dict[tuple[str, str], CollectionAdapter],
    adapter: CollectionAdapter,
) -> None:
    adapters[(adapter.source_id, adapter.adapter_id)] = adapter
