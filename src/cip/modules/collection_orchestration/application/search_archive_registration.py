from __future__ import annotations

from collections.abc import Callable

from cip.adapters.sources.crossref_publications.registry import CrossrefPublicationTarget
from cip.adapters.sources.developer_ecosystem.registry import DeveloperEcosystemTarget
from cip.adapters.sources.public_web.registry import PublicWebTarget
from cip.modules.collection_orchestration.application.archive_cdx_adapter import (
    InternetArchiveCdxAdapter,
)
from cip.modules.collection_orchestration.application.brave_search_adapter import (
    BraveSearchAdapter,
)
from cip.modules.collection_orchestration.application.common_crawl_adapter import (
    CommonCrawlIndexAdapter,
)
from cip.modules.collection_orchestration.application.crossref_publication_adapter import (
    CrossrefPublicationAdapter,
)
from cip.modules.collection_orchestration.application.github_code_search_adapter import (
    GitHubCodeSearchAdapter,
)
from cip.modules.collection_orchestration.application.ports import CollectionAdapter
from cip.modules.public_footprint.domain.search import SearchQueryTemplate
from cip.modules.source_governance.infrastructure.registry import SourceRegistryEntry


def register_search_archive_adapters(
    adapters: dict[tuple[str, str], CollectionAdapter],
    entries_by_id: dict[str, SourceRegistryEntry],
    targets: tuple[PublicWebTarget, ...],
    templates: tuple[SearchQueryTemplate, ...],
    developer_targets: tuple[DeveloperEcosystemTarget, ...],
    github_code_search_templates: tuple[SearchQueryTemplate, ...],
    crossref_publication_targets: tuple[CrossrefPublicationTarget, ...],
    *,
    brave_token_provider: Callable[[], str | None],
    github_code_search_token_provider: Callable[[], str | None],
    timeout_seconds: float,
) -> None:
    brave_entry = entries_by_id.get(BraveSearchAdapter.source_id)
    if brave_entry is not None:
        _register(
            adapters,
            BraveSearchAdapter(
                brave_entry,
                targets,
                templates,
                token_provider=brave_token_provider,
                timeout_seconds=timeout_seconds,
            ),
        )

    archive_entry = entries_by_id.get(InternetArchiveCdxAdapter.source_id)
    if archive_entry is not None:
        _register(
            adapters,
            InternetArchiveCdxAdapter(
                archive_entry,
                targets,
                timeout_seconds=timeout_seconds,
            ),
        )

    common_crawl_entry = entries_by_id.get(CommonCrawlIndexAdapter.source_id)
    if common_crawl_entry is not None:
        _register(
            adapters,
            CommonCrawlIndexAdapter(
                common_crawl_entry,
                targets,
                timeout_seconds=timeout_seconds,
            ),
        )

    github_code_entry = entries_by_id.get(GitHubCodeSearchAdapter.source_id)
    if github_code_entry is not None:
        _register(
            adapters,
            GitHubCodeSearchAdapter(
                github_code_entry,
                developer_targets,
                github_code_search_templates,
                token_provider=github_code_search_token_provider,
                timeout_seconds=timeout_seconds,
            ),
        )

    crossref_entry = entries_by_id.get(CrossrefPublicationAdapter.source_id)
    if crossref_entry is not None:
        _register(
            adapters,
            CrossrefPublicationAdapter(
                crossref_entry,
                crossref_publication_targets,
                timeout_seconds=timeout_seconds,
            ),
        )


def _register(
    adapters: dict[tuple[str, str], CollectionAdapter],
    adapter: CollectionAdapter,
) -> None:
    adapters[(adapter.source_id, adapter.adapter_id)] = adapter
