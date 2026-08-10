from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from cip.adapters.sources.greenhouse.registry import GreenhouseBoard
from cip.adapters.sources.incident_catalogs.sec_registry import SecIncidentTarget
from cip.adapters.sources.lever.registry import LeverSite
from cip.adapters.sources.organization_identity.registry import OrganizationIdentityTarget
from cip.adapters.sources.passive_infrastructure.registry import PassiveInfrastructureTarget
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
from cip.modules.collection_orchestration.application.intelligence_registration import (
    register_intelligence_adapters,
)
from cip.modules.collection_orchestration.application.lever_adapter import LeverAdapter
from cip.modules.collection_orchestration.application.passive_infrastructure_registration import (
    register_passive_infrastructure_adapters,
)
from cip.modules.collection_orchestration.application.ports import CollectionAdapter
from cip.modules.collection_orchestration.application.public_web_adapter import PublicWebAdapter
from cip.modules.collection_orchestration.application.reference_adapter import (
    ReferencePortfolioAdapter,
)
from cip.modules.collection_orchestration.application.search_archive_registration import (
    register_search_archive_adapters,
)
from cip.modules.collection_orchestration.application.smartrecruiters_adapter import (
    SmartRecruitersAdapter,
)
from cip.modules.collection_orchestration.application.ted_adapter import TedSearchAdapter
from cip.modules.collection_orchestration.application.vulnerability_registration import (
    register_vulnerability_adapters,
)
from cip.modules.public_footprint.domain.search import SearchQueryTemplate
from cip.modules.source_governance.infrastructure.registry import SourceRegistryEntry


@dataclass(frozen=True, slots=True)
class AdapterCompositionInputs:
    entries: tuple[SourceRegistryEntry, ...]
    greenhouse_boards: tuple[GreenhouseBoard, ...]
    lever_sites: tuple[LeverSite, ...]
    smartrecruiters_companies: tuple[SmartRecruitersCompany, ...]
    identity_targets: tuple[OrganizationIdentityTarget, ...]
    public_web_targets: tuple[PublicWebTarget, ...]
    search_templates: tuple[SearchQueryTemplate, ...]
    vulnerability_targets: tuple[VulnerabilityQueryTarget, ...]
    passive_infrastructure_targets: tuple[PassiveInfrastructureTarget, ...]
    sec_incident_targets: tuple[SecIncidentTarget, ...]


def build_runtime_adapters(
    inputs: AdapterCompositionInputs,
    *,
    brave_token_provider: Callable[[], str | None],
    certspotter_token_provider: Callable[[], str | None],
    phishtank_token_provider: Callable[[], str | None],
    sec_user_agent: str | None,
    phishtank_user_agent: str | None,
    timeout_seconds: float,
) -> dict[tuple[str, str], CollectionAdapter]:
    entries_by_id = {entry.policy.id: entry for entry in inputs.entries}
    adapters: dict[tuple[str, str], CollectionAdapter] = {}
    _register(adapters, ReferencePortfolioAdapter())
    _register_core_adapters(adapters, entries_by_id, inputs, timeout_seconds)
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
    register_search_archive_adapters(
        adapters,
        entries_by_id,
        inputs.public_web_targets,
        inputs.search_templates,
        brave_token_provider=brave_token_provider,
        timeout_seconds=timeout_seconds,
    )
    register_vulnerability_adapters(
        adapters,
        entries_by_id,
        inputs.vulnerability_targets,
        timeout_seconds=timeout_seconds,
    )
    register_passive_infrastructure_adapters(
        adapters,
        entries_by_id,
        inputs.passive_infrastructure_targets,
        certspotter_token_provider=certspotter_token_provider,
        timeout_seconds=timeout_seconds,
    )
    register_intelligence_adapters(
        adapters,
        entries_by_id,
        inputs.sec_incident_targets,
        phishtank_token_provider=phishtank_token_provider,
        sec_user_agent=sec_user_agent,
        phishtank_user_agent=phishtank_user_agent,
        timeout_seconds=timeout_seconds,
    )
    return adapters


def _register_core_adapters(
    adapters: dict[tuple[str, str], CollectionAdapter],
    entries_by_id: dict[str, SourceRegistryEntry],
    inputs: AdapterCompositionInputs,
    timeout_seconds: float,
) -> None:
    _register_if_present(adapters, entries_by_id, CisaKevAdapter, timeout_seconds)
    _register_if_present(adapters, entries_by_id, TedSearchAdapter, timeout_seconds)
    _register_if_present(adapters, entries_by_id, BoampAdapter, timeout_seconds)
    _register_if_present(adapters, entries_by_id, DecpAdapter, timeout_seconds)

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


def _register_if_present(
    adapters: dict[tuple[str, str], CollectionAdapter],
    entries_by_id: dict[str, SourceRegistryEntry],
    adapter_type: type[CisaKevAdapter]
    | type[TedSearchAdapter]
    | type[BoampAdapter]
    | type[DecpAdapter],
    timeout_seconds: float,
) -> None:
    entry = entries_by_id.get(adapter_type.source_id)
    if entry is None:
        return
    _register(adapters, adapter_type(entry, timeout_seconds=timeout_seconds))


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
            raise ValueError(f"enabled public web target has no source policy: {target.id}")
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
