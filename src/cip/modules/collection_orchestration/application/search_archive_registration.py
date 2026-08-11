from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from cip.adapters.sources.crossref_publications.registry import CrossrefPublicationTarget
from cip.adapters.sources.developer_ecosystem.registry import DeveloperEcosystemTarget
from cip.adapters.sources.patentsview_patents.registry import PatentsViewPatentTarget
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
from cip.modules.collection_orchestration.application.patentsview_patent_adapter import (
    PatentsViewPatentAdapter,
)
from cip.modules.collection_orchestration.application.ports import CollectionAdapter
from cip.modules.public_footprint.domain.search import SearchQueryTemplate
from cip.modules.source_governance.infrastructure.registry import SourceRegistryEntry


@dataclass(frozen=True, slots=True)
class SearchArchiveRegistrationInputs:
    public_web_targets: tuple[PublicWebTarget, ...]
    search_templates: tuple[SearchQueryTemplate, ...]
    developer_targets: tuple[DeveloperEcosystemTarget, ...]
    github_code_search_templates: tuple[SearchQueryTemplate, ...]
    crossref_publication_targets: tuple[CrossrefPublicationTarget, ...]
    patentsview_patent_targets: tuple[PatentsViewPatentTarget, ...]


def register_search_archive_adapters(
    adapters: dict[tuple[str, str], CollectionAdapter],
    entries_by_id: dict[str, SourceRegistryEntry],
    inputs: SearchArchiveRegistrationInputs,
    *,
    brave_token_provider: Callable[[], str | None],
    github_code_search_token_provider: Callable[[], str | None],
    patentsview_api_key_provider: Callable[[], str | None],
    timeout_seconds: float,
) -> None:
    brave_entry = entries_by_id.get(BraveSearchAdapter.source_id)
    if brave_entry is not None:
        _register(
            adapters,
            BraveSearchAdapter(
                brave_entry,
                inputs.public_web_targets,
                inputs.search_templates,
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
                inputs.public_web_targets,
                timeout_seconds=timeout_seconds,
            ),
        )

    common_crawl_entry = entries_by_id.get(CommonCrawlIndexAdapter.source_id)
    if common_crawl_entry is not None:
        _register(
            adapters,
            CommonCrawlIndexAdapter(
                common_crawl_entry,
                inputs.public_web_targets,
                timeout_seconds=timeout_seconds,
            ),
        )

    github_code_entry = entries_by_id.get(GitHubCodeSearchAdapter.source_id)
    if github_code_entry is not None:
        _register(
            adapters,
            GitHubCodeSearchAdapter(
                github_code_entry,
                inputs.developer_targets,
                inputs.github_code_search_templates,
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
                inputs.crossref_publication_targets,
                timeout_seconds=timeout_seconds,
            ),
        )

    patentsview_entry = entries_by_id.get(PatentsViewPatentAdapter.source_id)
    if patentsview_entry is not None:
        _register(
            adapters,
            PatentsViewPatentAdapter(
                patentsview_entry,
                inputs.patentsview_patent_targets,
                token_provider=patentsview_api_key_provider,
                timeout_seconds=timeout_seconds,
            ),
        )


def _register(
    adapters: dict[tuple[str, str], CollectionAdapter],
    adapter: CollectionAdapter,
) -> None:
    adapters[(adapter.source_id, adapter.adapter_id)] = adapter
