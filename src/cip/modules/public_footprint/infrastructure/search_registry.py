from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from cip.modules.public_footprint.domain import SearchQueryTemplate


def load_search_query_templates(path: Path) -> tuple[SearchQueryTemplate, ...]:
    payload = _load_yaml_mapping(path)
    if _positive_int(payload, "version") != 1:
        raise ValueError("unsupported search query template registry version")
    raw_templates = payload.get("templates")
    if not isinstance(raw_templates, list):
        raise ValueError("search query templates must be a list")
    if len(raw_templates) > 100:
        raise ValueError("search query template registry cannot exceed 100 entries")
    templates: list[SearchQueryTemplate] = []
    identities: set[tuple[str, int]] = set()
    for raw in raw_templates:
        if not isinstance(raw, dict):
            raise ValueError("each search query template must be a mapping")
        template = _parse_template(raw)
        identity = (template.id, template.version)
        if identity in identities:
            raise ValueError("duplicate search query template id and version")
        identities.add(identity)
        templates.append(template)
    return tuple(templates)


def _parse_template(payload: dict[str, Any]) -> SearchQueryTemplate:
    return SearchQueryTemplate(
        id=_required_string(payload, "id"),
        version=_positive_int(payload, "version"),
        query_pattern=_required_string(payload, "query_pattern"),
        purpose=_required_string(payload, "purpose"),
        enabled=_required_bool(payload, "enabled"),
    )


def _load_yaml_mapping(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(path)
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ValueError("search query template registry root must be a mapping")
    return loaded


def _required_string(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} must be a non-empty string")
    return value


def _required_bool(payload: dict[str, Any], key: str) -> bool:
    value = payload.get(key)
    if not isinstance(value, bool):
        raise ValueError(f"{key} must be a boolean")
    return value


def _positive_int(payload: dict[str, Any], key: str) -> int:
    value = payload.get(key)
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise ValueError(f"{key} must be a positive integer")
    return value
