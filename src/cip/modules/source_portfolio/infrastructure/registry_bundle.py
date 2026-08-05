from __future__ import annotations

from pathlib import Path

from cip.modules.source_portfolio.domain.models import SourceCatalogEntry
from cip.modules.source_portfolio.infrastructure.registry import load_source_portfolio


def load_source_portfolio_bundle(*paths: Path) -> tuple[SourceCatalogEntry, ...]:
    entries: list[SourceCatalogEntry] = []
    source_ids: set[str] = set()
    for path in paths:
        for entry in load_source_portfolio(path):
            if entry.source_id in source_ids:
                raise ValueError(
                    f"duplicate source portfolio source_id across registries: {entry.source_id}"
                )
            source_ids.add(entry.source_id)
            entries.append(entry)
    return tuple(entries)
