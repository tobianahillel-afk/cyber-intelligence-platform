from __future__ import annotations

from pathlib import Path

from cip.modules.source_governance.infrastructure.registry import (
    SourceRegistryEntry,
    load_source_registry,
)


def load_source_registry_bundle(*paths: Path) -> tuple[SourceRegistryEntry, ...]:
    entries: list[SourceRegistryEntry] = []
    ids: set[str] = set()
    for path in paths:
        for entry in load_source_registry(path):
            source_id = entry.policy.id
            if source_id in ids:
                raise ValueError(f"duplicate source id across registries: {source_id}")
            ids.add(source_id)
            entries.append(entry)
    return tuple(entries)
