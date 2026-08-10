from __future__ import annotations

from collections.abc import Callable

from cip.adapters.sources.ashby.registry import AshbyBoard
from cip.adapters.sources.recruitee.registry import RecruiteeCareerSite
from cip.adapters.sources.teamtailor.registry import TeamtailorAccount
from cip.modules.collection_orchestration.application.ashby_adapter import AshbyAdapter
from cip.modules.collection_orchestration.application.ports import CollectionAdapter
from cip.modules.collection_orchestration.application.recruitee_adapter import RecruiteeAdapter
from cip.modules.collection_orchestration.application.teamtailor_adapter import TeamtailorAdapter
from cip.modules.source_governance.infrastructure.registry import SourceRegistryEntry


def register_extended_ats_adapters(
    adapters: dict[tuple[str, str], CollectionAdapter],
    entries_by_id: dict[str, SourceRegistryEntry],
    ashby_boards: tuple[AshbyBoard, ...],
    recruitee_sites: tuple[RecruiteeCareerSite, ...],
    teamtailor_accounts: tuple[TeamtailorAccount, ...],
    *,
    teamtailor_token_provider: Callable[[], str | None],
    timeout_seconds: float,
) -> None:
    ashby_entry = entries_by_id.get(AshbyAdapter.source_id)
    if ashby_entry is not None and any(board.enabled for board in ashby_boards):
        _register(
            adapters,
            AshbyAdapter(
                ashby_entry,
                ashby_boards,
                timeout_seconds=timeout_seconds,
            ),
        )
    recruitee_entry = entries_by_id.get(RecruiteeAdapter.source_id)
    if recruitee_entry is not None and any(site.enabled for site in recruitee_sites):
        _register(
            adapters,
            RecruiteeAdapter(
                recruitee_entry,
                recruitee_sites,
                timeout_seconds=timeout_seconds,
            ),
        )
    enabled_accounts = tuple(account for account in teamtailor_accounts if account.enabled)
    teamtailor_entry = entries_by_id.get(TeamtailorAdapter.source_id)
    if teamtailor_entry is not None and enabled_accounts:
        if len(enabled_accounts) != 1:
            raise ValueError("Teamtailor requires exactly one enabled account")
        _register(
            adapters,
            TeamtailorAdapter(
                teamtailor_entry,
                enabled_accounts[0],
                teamtailor_token_provider,
                timeout_seconds=timeout_seconds,
            ),
        )


def _register(
    adapters: dict[tuple[str, str], CollectionAdapter],
    adapter: CollectionAdapter,
) -> None:
    identity = (adapter.source_id, adapter.adapter_id)
    if identity in adapters:
        raise ValueError(f"duplicate runtime adapter: {identity[0]}/{identity[1]}")
    adapters[identity] = adapter
