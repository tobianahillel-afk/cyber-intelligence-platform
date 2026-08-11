from __future__ import annotations

from collections.abc import Mapping

from cip.adapters.sources.organization_identity.registry import OrganizationIdentityTarget
from cip.modules.collection_orchestration.application.bodacc_identity_adapter import (
    BodaccIdentityAdapter,
)
from cip.modules.collection_orchestration.application.brreg_identity_adapter import (
    BrregIdentityAdapter,
)
from cip.modules.collection_orchestration.application.gleif_adapter import GleifAdapter
from cip.modules.collection_orchestration.application.ports import CollectionAdapter
from cip.modules.collection_orchestration.application.recherche_entreprises_adapter import (
    RechercheEntreprisesAdapter,
)
from cip.modules.source_governance.infrastructure.registry import SourceRegistryEntry


def register_identity_adapters(
    adapters: dict[tuple[str, str], CollectionAdapter],
    entries_by_id: Mapping[str, SourceRegistryEntry],
    targets: tuple[OrganizationIdentityTarget, ...],
    *,
    timeout_seconds: float,
) -> None:
    brreg_entry = entries_by_id.get(BrregIdentityAdapter.source_id)
    if brreg_entry is not None:
        _register(
            adapters,
            BrregIdentityAdapter(
                brreg_entry,
                targets,
                timeout_seconds=timeout_seconds,
            ),
        )
    if not any(target.enabled for target in targets):
        return
    recherche_entry = entries_by_id.get(RechercheEntreprisesAdapter.source_id)
    if recherche_entry is not None and any(
        target.enabled and target.country_code == "FR" for target in targets
    ):
        _register(
            adapters,
            RechercheEntreprisesAdapter(
                recherche_entry,
                targets,
                timeout_seconds=timeout_seconds,
            ),
        )
    gleif_entry = entries_by_id.get(GleifAdapter.source_id)
    if gleif_entry is not None and any(target.enabled and target.lei for target in targets):
        _register(
            adapters,
            GleifAdapter(
                gleif_entry,
                targets,
                timeout_seconds=timeout_seconds,
            ),
        )
    bodacc_entry = entries_by_id.get(BodaccIdentityAdapter.source_id)
    if bodacc_entry is not None and any(
        target.enabled and target.country_code == "FR" and target.siren
        for target in targets
    ):
        _register(
            adapters,
            BodaccIdentityAdapter(
                bodacc_entry,
                targets,
                timeout_seconds=timeout_seconds,
            ),
        )


def _register(
    adapters: dict[tuple[str, str], CollectionAdapter],
    adapter: CollectionAdapter,
) -> None:
    adapters[(adapter.source_id, adapter.adapter_id)] = adapter
