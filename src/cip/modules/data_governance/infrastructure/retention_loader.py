from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from cip.modules.data_governance.domain.retention import RetentionPolicy, RetentionRule
from cip.modules.source_governance.domain.models import DataCategory


def load_retention_policy(path: Path) -> RetentionPolicy:
    payload = _load_yaml_mapping(path)
    raw_rules = _require_mapping(payload, "rules")
    rules = {
        DataCategory(name): RetentionRule(
            retention_days=_require_positive_int(value, "retention_days"),
            review_interval_days=_require_positive_int(value, "review_interval_days"),
        )
        for name, value in raw_rules.items()
    }
    suppression = _require_mapping(payload, "suppression")
    backups = _require_mapping(payload, "backups")
    prohibited = frozenset(
        DataCategory(value) for value in payload.get("prohibited_categories", [])
    )
    return RetentionPolicy(
        version=_require_positive_int(payload, "version"),
        rules=rules,
        prohibited_categories=prohibited,
        suppression_minimum_days=_require_positive_int(
            suppression,
            "minimum_retention_days",
        ),
        backup_deletion_propagation_max_days=_require_positive_int(
            backups,
            "deletion_propagation_max_days",
        ),
        restoration_requires_suppressions=bool(
            backups.get("restoration_requires_reapplication_of_suppressions", False)
        ),
    )


def _load_yaml_mapping(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(path)
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ValueError("retention policy root must be a mapping")
    return loaded


def _require_mapping(payload: dict[str, Any], key: str) -> dict[str, Any]:
    value = payload.get(key)
    if not isinstance(value, dict):
        raise ValueError(f"{key} must be a mapping")
    return value


def _require_positive_int(payload: dict[str, Any], key: str) -> int:
    value = payload.get(key)
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise ValueError(f"{key} must be a positive integer")
    return value
