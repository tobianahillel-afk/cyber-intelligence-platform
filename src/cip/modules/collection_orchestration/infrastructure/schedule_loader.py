from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from cip.modules.collection_orchestration.domain.models import RetryPolicy, SourceSchedule


def load_collection_schedules(path: Path) -> tuple[SourceSchedule, ...]:
    payload = _load_yaml_mapping(path)
    if _require_positive_int(payload, "version") != 1:
        raise ValueError("unsupported collection schedule version")
    raw_schedules = payload.get("schedules")
    if not isinstance(raw_schedules, list):
        raise ValueError("schedules must be a list")

    schedules: list[SourceSchedule] = []
    identities: set[tuple[str, str]] = set()
    for raw in raw_schedules:
        if not isinstance(raw, dict):
            raise ValueError("each schedule must be a mapping")
        schedule = _parse_schedule(raw)
        identity = (schedule.source_id, schedule.adapter_id)
        if identity in identities:
            raise ValueError(f"duplicate collection schedule: {identity[0]}/{identity[1]}")
        identities.add(identity)
        schedules.append(schedule)
    return tuple(schedules)


def _parse_schedule(payload: dict[str, Any]) -> SourceSchedule:
    retry = _require_mapping(payload, "retry")
    return SourceSchedule(
        source_id=_require_string(payload, "source_id"),
        adapter_id=_require_string(payload, "adapter_id"),
        interval_seconds=_require_positive_int(payload, "interval_seconds"),
        lease_seconds=_require_positive_int(payload, "lease_seconds"),
        enabled=_require_bool(payload, "enabled"),
        retry_policy=RetryPolicy(
            max_attempts=_require_positive_int(retry, "max_attempts"),
            base_delay_seconds=_require_positive_int(retry, "base_delay_seconds"),
            max_delay_seconds=_require_positive_int(retry, "max_delay_seconds"),
            circuit_failure_threshold=_require_positive_int(
                retry,
                "circuit_failure_threshold",
            ),
            circuit_reset_seconds=_require_positive_int(retry, "circuit_reset_seconds"),
        ),
    )


def _load_yaml_mapping(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(path)
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ValueError("collection schedule root must be a mapping")
    return loaded


def _require_mapping(payload: dict[str, Any], key: str) -> dict[str, Any]:
    value = payload.get(key)
    if not isinstance(value, dict):
        raise ValueError(f"{key} must be a mapping")
    return value


def _require_string(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} must be a non-empty string")
    return value.strip()


def _require_positive_int(payload: dict[str, Any], key: str) -> int:
    value = payload.get(key)
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise ValueError(f"{key} must be a positive integer")
    return value


def _require_bool(payload: dict[str, Any], key: str) -> bool:
    value = payload.get(key)
    if not isinstance(value, bool):
        raise ValueError(f"{key} must be a boolean")
    return value
