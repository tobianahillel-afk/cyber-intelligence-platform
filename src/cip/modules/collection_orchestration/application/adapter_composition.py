from __future__ import annotations

from dataclasses import dataclass

from cip.adapters.sources.greenhouse.registry import GreenhouseBoard
from cip.adapters.sources.lever.registry import LeverSite
from cip.adapters.sources.organization_identity.registry import OrganizationIdentityTarget
from cip.adapters.sources.public_web.registry import PublicWebTarget
from cip.adapters.sources.smartrecruiters.registry import SmartRecruitersCompany
from cip.adapters.sources.vulnerability_catalogs.registry import VulnerabilityQueryTarget
from cip.modules.collection_orchestration.application.adapters import CisaKevAdapter
from cip.modules.collection_orchestration.application.boamp_adapter import BoampAdapter
from cip.modules.collection_orchestration.application.decp_adapter import DecpAdapter
from cip.modules.collection_orchestration.application.greenhouse_adapter import GreenhouseAdapter
from cip.modules.collection_orchestration.application.identity_adapters import (
    register_identity_adapters,
)
from cip.modules.collection_orchestration.application.lever_adapter import LeverAdapter
from cip.modules.collection_orchestration.application.ports import CollectionAdapter
from cip.modules.collection_orchestration.application.public_web_adapter import PublicWebAdapter
from cip.modules.collection_orchestration.application.reference_adapter import (
    ReferencePortfolioAdapter,
)
from cip.modules.collection_orchestration.application.smartrecruiters_adapter import (
    SmartRecruitersAdapter,
)
from cip.modules.collection_orchestration.application.ted_adapter import TedSearchAdapter
from cip.modules.collection_orchestration.application.vulnerability_registration import (
    register_vulnerability_adapters,
)
from cip.modules.source_governance.infrastructure.registry import SourceRegistryEntry


@dataclass(frozen=True, slots=True)
class AdapterCompositionInputs:
    entries: tuple[SourceRegistryEntry, ...]
    greenhouse_boards: tuple[GreenhouseBoard, ...]
    lever_sites: tuple[LeverSite, ...]
    smartrecruiters_companies: tuple[SmartRecruitersCompany, ...]
    identity_targets: tuple[OrganizationIdentityTarget, ...]
    public_web_targets: tuple[PublicWebTarget, ...]
    vulnerability_targets: tuple[VulnerabilityQueryTarget, ...]


def build_runtime_adapters(
    inputs: AdapterCompositionInputs,
    *,
    timeout_seconds: float,
) -> dict[tuple[str, str], CollectionAdapter]:
    entries_by_id = {entry.policy.id: entry for entry in inputs.entries}
    adapters: dict[tuple[str, str], CollectionAdapter] = {}
    _register(adapters, ReferencePortfolioAdapter())
    cisa_entry = entries_by_id.get(CisaKevAdapter.source_id)
    if cisa_entry is not None:
        _register(adapters, CisaKevAdapter(cisa_entry, timeout_seconds=timeout_seconds))
    ted_entry = entries_by_id.get(TedSearchAdapter.source_id)
    if ted_entry is not None:
        _register(adapters, TedSearchAdapter(ted_entry, timeout_seconds=timeout_seconds))
    boamp_entry = entries_by_id.get(BoampAdapter.source_id)
    if boamp_entry is not None:
        _register(adapters, BoampAdapter(boamp_entry, timeout_seconds=timeout_seconds))
    decp_entry = entries_by_id.get(DecpAdapter.source_id)
    if decp_entry is not None:
        _register(adapters, DecpAdapter(decp_entry, timeout_seconds=timeout_seconds))
    greenhouse_entry = entries_by_id.get(GreenhouseAdapter.source_id)
    if greenhouse_entry is not None and any(
        board.enabled for board in inputs.greenhouse_boards
    ):
        _register(
            adapters,
            GreenhouseAdapter(
                greenhouse_entry,
                inputs.greenhouse_boards,
                timeout_seconds=timeout_seconds,
            ),
        )
    lever_entry = entries_by_id.get(LeverAdapter.source_id)
    if lever_entry is not None and any(site.enabled for site in inputs.lever_sites):
        _register(
            adapters,
            LeverAdapter(
                lever_entry,
                inputs.lever_sites,
                timeout_seconds=timeout_seconds,
            ),
        )
    smartrecruiters_entry = entries_by_id.get(SmartRecruitersAdapter.source_id)
    if smartrecruiters_entry is not None and any(
        company.enabled for company in inputs.smartrecruiters_companies
    ):
        _register(
            adapters,
            SmartRecruitersAdapter(
                smartrecruiters_entry,
                inputs.smartrecruiters_companies,
                timeout_seconds=timeout_seconds,
            ),
        )
    register_identity_adapters(
        adapters,
        entries_by_id,
        inputs.identity_targets,
        timeout_seconds=timeout_seconds,
    )
    _register_public_web_adapters(
        adapters,
        entries_by_id,
        inputs.public_web_targets,
        timeout_seconds=timeout_seconds,
    )
    register_vulnerability_adapters(
        adapters,
        entries_by_id,
        inputs.vulnerability_targets,
        timeout_seconds=timeout_seconds,
    )
    return adapters


def _register_public_web_adapters(
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
        _register(
            adapters,
            PublicWebAdapter(
                entry,
                target,
                timeout_seconds=timeout_seconds,
            ),
        )


def _register(
    adapters: dict[tuple[str, str], CollectionAdapter],
    adapter: CollectionAdapter,
) -> None:
    adapters[(adapter.source_id, adapter.adapter_id)] = adapter
