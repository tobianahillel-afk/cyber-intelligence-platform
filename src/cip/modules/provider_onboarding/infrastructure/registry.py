from __future__ import annotations

from pathlib import Path

import yaml

from cip.modules.provider_onboarding.domain.models import (
    AuthMode,
    HumanAction,
    ProviderProfile,
)


def load_provider_profiles(path: Path) -> tuple[ProviderProfile, ...]:
    if not path.exists():
        raise FileNotFoundError(path)
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("provider onboarding root must be a mapping")
    if payload.get("version") != 1:
        raise ValueError("unsupported provider onboarding registry version")
    raw_profiles = payload.get("providers")
    if not isinstance(raw_profiles, list):
        raise ValueError("providers must be a list")
    profiles = tuple(_profile_from_mapping(item) for item in raw_profiles)
    source_ids = [profile.source_id for profile in profiles]
    if len(source_ids) != len(set(source_ids)):
        raise ValueError("duplicate provider onboarding source_id")
    return profiles


def _profile_from_mapping(value: object) -> ProviderProfile:
    if not isinstance(value, dict):
        raise ValueError("each provider onboarding profile must be a mapping")
    try:
        auth_mode = AuthMode(_required_string(value, "auth_mode"))
        actions = tuple(
            HumanAction(item)
            for item in _string_list(value, "human_actions")
        )
        required_secret_names = tuple(
            _string_list(value, "required_secret_names")
        )
        automatic = value.get("automatic_onboarding")
        if not isinstance(automatic, bool):
            raise ValueError("automatic_onboarding must be a boolean")
        return ProviderProfile(
            source_id=_required_string(value, "source_id"),
            display_name=_required_string(value, "display_name"),
            auth_mode=auth_mode,
            documentation_url=_required_string(value, "documentation_url"),
            signup_url=_optional_string(value, "signup_url"),
            console_url=_optional_string(value, "console_url"),
            required_secret_names=required_secret_names,
            human_actions=actions,
            automatic_onboarding=automatic,
            blocked_reason=_optional_string(value, "blocked_reason"),
        )
    except (KeyError, TypeError) as exc:
        raise ValueError("invalid provider onboarding profile") from exc


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
    return [entry.strip() for entry in item]
