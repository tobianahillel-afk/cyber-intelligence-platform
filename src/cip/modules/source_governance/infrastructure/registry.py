from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from cip.modules.source_governance.domain.models import (
    AuthorizationStatus,
    DataCategory,
    HttpMethod,
    SourceAuthorization,
    SourcePolicy,
    SourceStatus,
    SourceType,
)


@dataclass(frozen=True, slots=True)
class SourceRegistryEntry:
    policy: SourcePolicy
    authorization: SourceAuthorization
    economics: dict[str, object]
    notes: str = ""


def load_source_registry(path: Path) -> tuple[SourceRegistryEntry, ...]:
    payload = _load_yaml_mapping(path)
    if payload.get("version") != 1:
        raise ValueError("unsupported source registry version")
    raw_sources = payload.get("sources")
    if not isinstance(raw_sources, list):
        raise ValueError("sources must be a list")
    entries = tuple(_parse_entry(value) for value in raw_sources)
    identifiers = [entry.policy.id for entry in entries]
    if len(set(identifiers)) != len(identifiers):
        raise ValueError("source registry contains duplicate ids")
    return entries


def _parse_entry(value: object) -> SourceRegistryEntry:
    if not isinstance(value, dict):
        raise ValueError("each source must be a mapping")
    authorization_payload = _require_mapping(value, "authorization")
    policy = SourcePolicy(
        id=_require_string(value, "id"),
        name=_require_string(value, "name"),
        base_url=_require_string(value, "base_url"),
        status=SourceStatus(_require_string(value, "status")),
        source_type=SourceType(_require_string(value, "source_type")),
        owner=_require_string(value, "owner"),
        terms_url=_optional_string(value.get("terms_url")),
        licence=_optional_string(value.get("licence")),
        allowed_data_categories=frozenset(
            DataCategory(item) for item in _require_string_list(value, "allowed_data_categories")
        ),
        prohibited_data_categories=frozenset(
            DataCategory(item)
            for item in _require_string_list(value, "prohibited_data_categories")
        ),
        rate_limit_per_minute=_optional_int(value.get("rate_limit_per_minute")),
        retention_days=_optional_int(value.get("retention_days")),
        attribution_required=bool(value.get("attribution_required", False)),
        raw_content_storage=bool(value.get("raw_content_storage", False)),
        human_review_required=bool(value.get("human_review_required", True)),
    )
    authorization = SourceAuthorization(
        status=AuthorizationStatus(_require_string(authorization_payload, "status")),
        document_reference=_optional_string(
            authorization_payload.get("document_reference")
        ),
        reviewed_at=_optional_datetime(authorization_payload.get("reviewed_at")),
        expires_at=_optional_datetime(authorization_payload.get("expires_at")),
        approved_hosts=frozenset(
            _require_string_list(authorization_payload, "approved_hosts")
        ),
        approved_path_prefixes=tuple(
            _require_string_list(authorization_payload, "approved_path_prefixes")
        ),
        approved_purposes=frozenset(
            _require_string_list(authorization_payload, "approved_purposes")
        ),
        approved_http_methods=frozenset(
            HttpMethod(item)
            for item in _optional_string_list(
                authorization_payload.get("approved_http_methods"),
                default=[HttpMethod.GET.value],
            )
        ),
        automated_collection_allowed=bool(
            authorization_payload.get("automated_collection_allowed", False)
        ),
        raw_storage_allowed=bool(authorization_payload.get("raw_storage_allowed", False)),
    )
    economics_value = value.get("economics", {})
    if not isinstance(economics_value, dict):
        raise ValueError("economics must be a mapping")
    return SourceRegistryEntry(
        policy=policy,
        authorization=authorization,
        economics=dict(economics_value),
        notes=str(value.get("notes", "")),
    )


def _load_yaml_mapping(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(path)
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ValueError("source registry root must be a mapping")
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
    return value


def _require_string_list(payload: dict[str, Any], key: str) -> list[str]:
    value = payload.get(key)
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError(f"{key} must be a list of strings")
    return value


def _optional_string_list(value: object, *, default: list[str]) -> list[str]:
    if value is None:
        return list(default)
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError("optional list field must be a list of strings")
    return value


def _optional_string(value: object) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("optional string field has an invalid type")
    return value


def _optional_int(value: object) -> int | None:
    if value is None:
        return None
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("optional integer field has an invalid type")
    return value


def _optional_datetime(value: object) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if not isinstance(value, str):
        raise ValueError("optional datetime field has an invalid type")
    return datetime.fromisoformat(value.replace("Z", "+00:00"))
