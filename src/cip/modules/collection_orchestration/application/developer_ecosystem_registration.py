from __future__ import annotations

from cip.adapters.sources.developer_ecosystem.registry import DeveloperEcosystemTarget
from cip.modules.collection_orchestration.application.maven_central_adapter import (
    MavenCentralArtifactAdapter,
)
from cip.modules.collection_orchestration.application.npm_adapter import NpmPackageAdapter
from cip.modules.collection_orchestration.application.ports import CollectionAdapter
from cip.modules.collection_orchestration.application.pypi_adapter import PyPiPackageAdapter
from cip.modules.collection_orchestration.application.repository_metadata_adapters import (
    GitHubOrganizationRepositoriesAdapter,
    GitLabGroupProjectsAdapter,
)
from cip.modules.source_governance.infrastructure.registry import SourceRegistryEntry

_ADAPTER_TYPES = (
    GitHubOrganizationRepositoriesAdapter,
    GitLabGroupProjectsAdapter,
    PyPiPackageAdapter,
    NpmPackageAdapter,
    MavenCentralArtifactAdapter,
)


def register_developer_ecosystem_adapters(
    adapters: dict[tuple[str, str], CollectionAdapter],
    entries_by_id: dict[str, SourceRegistryEntry],
    targets: tuple[DeveloperEcosystemTarget, ...],
    *,
    timeout_seconds: float,
) -> None:
    for adapter_type in _ADAPTER_TYPES:
        entry = entries_by_id.get(adapter_type.source_id)
        if entry is None:
            continue
        adapter = adapter_type(entry, targets, timeout_seconds=timeout_seconds)
        adapters[(adapter.source_id, adapter.adapter_id)] = adapter
