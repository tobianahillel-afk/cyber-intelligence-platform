from __future__ import annotations

from collections.abc import Callable

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
from cip.modules.collection_orchestration.application.ports import CollectionAdapter
from cip.modules.public_footprint.domain.search import SearchQueryTemplate
from cip.modules.source_governance.infrastructure.registry import SourceRegistryEntry


def register_search_archive_adapters(
    adapters: dict[tuple[str, str], CollectionAdapter],
    entries_by_id: dict[str, SourceRegistryEntry],
    targets: tuple[PublicWebTarget, ...],
    templates: tuple[SearchQueryTemplate, ...],
    *,
    brave_token_provider: Callable[[], str | None],
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


def _register(
    adapters: dict[tuple[str, str], CollectionAdapter],
    adapter: CollectionAdapter,
) -> None:
    adapters[(adapter.source_id, adapter.adapter_id)] = adapter