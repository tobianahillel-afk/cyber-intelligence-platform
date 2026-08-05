from __future__ import annotations

from datetime import datetime
from pathlib import Path

import yaml

from cip.modules.source_portfolio.domain.models import (
    AdapterCapabilityManifest,
    CatalogStatus,
    CollectionMode,
    SourceCatalogEntry,
)


def load_source_portfolio(path: Path) -> tuple[SourceCatalogEntry, ...]:
    if not path.exists():
        raise FileNotFoundError(path)
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("source portfolio root must be a mapping")
    if payload.get("version") != 1:
        raise ValueError("unsupported source portfolio version")
    raw_sources = payload.get("sources")
    if not isinstance(raw_sources, list):
        raise ValueError("source portfolio sources must be a list")
    entries = tuple(_entry(value) for value in raw_sources)
    identities = [entry.source_id for entry in entries]
    if len(identities) != len(set(identities)):
        raise ValueError("duplicate source portfolio source_id")
    return entries


def _entry(value: object) -> SourceCatalogEntry:
    mapping = _mapping(value, "source portfolio entry")
    source_id = _required_string(mapping, "source_id")
    adapter_mapping = mapping.get("adapter")
    adapter = None if adapter_mapping is None else _adapter(source_id, adapter_mapping)
    metadata = mapping.get("metadata", {})
    if not isinstance(metadata, dict):
        raise ValueError("metadata must be a mapping")
    return SourceCatalogEntry(
        source_id=source_id,
        display_name=_required_string(mapping, "display_name"),
        canonical_url=_required_string(mapping, "canonical_url"),
        category=_required_string(mapping, "category"),
        status=CatalogStatus(_required_string(mapping, "status")),
        freshness_max_age_seconds=_positive_int(mapping, "freshness_max_age_seconds"),
        commercial_use_cases=tuple(_string_list(mapping, "commercial_use_cases")),
        adapter=adapter,
        authorization_expires_at=_optional_datetime(mapping, "authorization_expires_at"),
        review_due_at=_optional_datetime(mapping, "review_due_at"),
        candidate_origin=_optional_string(mapping, "candidate_origin"),
        monthly_cost_limit=_optional_non_negative_number(mapping, "monthly_cost_limit"),
        metadata={str(key): item for key, item in metadata.items()},
    )


def _adapter(source_id: str, value: object) -> AdapterCapabilityManifest:
    mapping = _mapping(value, "adapter manifest")
    modes = frozenset(CollectionMode(item) for item in _string_list(mapping, "modes"))
    return AdapterCapabilityManifest(
        source_id=source_id,
        adapter_id=_required_string(mapping, "adapter_id"),
        adapter_version=_required_string(mapping, "adapter_version"),
        provider_schema_version=_required_string(mapping, "provider_schema_version"),
        modes=modes,
        canonical_output_types=tuple(_string_list(mapping, "canonical_output_types")),
        supports_corrections=_boolean(mapping, "supports_corrections", default=False),
        supports_tombstones=_boolean(mapping, "supports_tombstones", default=False),
        supports_retractions=_boolean(mapping, "supports_retractions", default=False),
        max_page_size=_optional_positive_int(mapping, "max_page_size"),
        max_window_days=_optional_positive_int(mapping, "max_window_days"),
        cost_per_request=_non_negative_number(mapping, "cost_per_request", default=0.0),
    )


def _mapping(value: object, label: str) -> dict[object, object]:
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be a mapping")
    return value


def _required_string(value: dict[object, object], key: str) -> str:
    item = value.get(key)
    if not isinstance(item, str) or not item.strip():
        raise ValueError(f"{key} must be a non-empty string")
    return item.strip()


def _optional_string(value: dict[object, object], key: str) -> str | None:
    item = value.get(key)
    if item is None:
        return None
    if not isinstance(item, str) or not item.strip():
        raise ValueError(f"{key} must be null or a non-empty string")
    return item.strip()


def _string_list(value: dict[object, object], key: str) -> list[str]:
    item = value.get(key)
    if not isinstance(item, list) or any(not isinstance(entry, str) for entry in item):
        raise ValueError(f"{key} must be a list of strings")
    result = [entry.strip() for entry in item]
    if any(not entry for entry in result):
        raise ValueError(f"{key} cannot contain empty strings")
    return result


def _positive_int(value: dict[object, object], key: str) -> int:
    item = value.get(key)
    if not isinstance(item, int) or isinstance(item, bool) or item < 1:
        raise ValueError(f"{key} must be a positive integer")
    return item


def _optional_positive_int(value: dict[object, object], key: str) -> int | None:
    item = value.get(key)
    if item is None:
        return None
    if not isinstance(item, int) or isinstance(item, bool) or item < 1:
        raise ValueError(f"{key} must be null or a positive integer")
    return item


def _boolean(value: dict[object, object], key: str, *, default: bool) -> bool:
    item = value.get(key, default)
    if not isinstance(item, bool):
        raise ValueError(f"{key} must be a boolean")
    return item


def _non_negative_number(
    value: dict[object, object], key: str, *, default: float
) -> float:
    item = value.get(key, default)
    if not isinstance(item, int | float) or isinstance(item, bool) or item < 0:
        raise ValueError(f"{key} must be a non-negative number")
    return float(item)


def _optional_non_negative_number(
    value: dict[object, object], key: str
) -> float | None:
    item = value.get(key)
    if item is None:
        return None
    if not isinstance(item, int | float) or isinstance(item, bool) or item < 0:
        raise ValueError(f"{key} must be null or a non-negative number")
    return float(item)


def _optional_datetime(value: dict[object, object], key: str) -> datetime | None:
    item = value.get(key)
    if item is None:
        return None
    if isinstance(item, datetime):
        return item
    if isinstance(item, str):
        return datetime.fromisoformat(item.replace("Z", "+00:00"))
    raise ValueError(f"{key} must be null or an ISO-8601 datetime")
