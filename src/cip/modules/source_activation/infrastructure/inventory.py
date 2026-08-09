from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from cip.modules.source_activation.domain.models import (
    ActivationDisposition,
    ActivationRecord,
    ActivationStage,
)


def load_activation_inventory(path: Path) -> tuple[ActivationRecord, ...]:
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict) or document.get("version") != 1:
        raise ValueError("source activation inventory must declare version: 1")
    raw_sources = document.get("sources")
    if not isinstance(raw_sources, list):
        raise ValueError("source activation inventory requires a sources list")
    return tuple(_record(item) for item in raw_sources)


def _record(value: object) -> ActivationRecord:
    if not isinstance(value, dict):
        raise ValueError("source activation entries must be mappings")
    stages = value.get("stages")
    if not isinstance(stages, list) or not stages:
        raise ValueError("source activation entries require non-empty stages")
    return ActivationRecord(
        source_id=_required_text(value, "source_id"),
        display_name=_required_text(value, "display_name"),
        category=_required_text(value, "category"),
        disposition=ActivationDisposition(_required_text(value, "disposition")),
        stages=frozenset(ActivationStage(_required_stage(stage)) for stage in stages),
        activation_wave=_optional_text(value, "activation_wave"),
        requires_schedule=_optional_bool(value, "requires_schedule", default=True),
        reason=_optional_text(value, "reason"),
        replacement_source_id=_optional_text(value, "replacement_source_id"),
        duplicate_of_source_id=_optional_text(value, "duplicate_of_source_id"),
    )


def _required_text(value: dict[str, Any], key: str) -> str:
    result = _optional_text(value, key)
    if result is None:
        raise ValueError(f"{key} is required")
    return result


def _optional_text(value: dict[str, Any], key: str) -> str | None:
    raw = value.get(key)
    if raw is None:
        return None
    if not isinstance(raw, str):
        raise ValueError(f"{key} must be text")
    normalized = raw.strip()
    return normalized or None


def _optional_bool(value: dict[str, Any], key: str, *, default: bool) -> bool:
    raw = value.get(key, default)
    if not isinstance(raw, bool):
        raise ValueError(f"{key} must be boolean")
    return raw


def _required_stage(value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("activation stages must be non-empty strings")
    return value.strip()
