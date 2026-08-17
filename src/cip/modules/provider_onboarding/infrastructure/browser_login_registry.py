from __future__ import annotations

from datetime import datetime
from pathlib import Path

import yaml

from cip.modules.provider_onboarding.domain.browser_login import (
    ProviderLoginChallenge,
    ProviderLoginChallengeSignal,
    ProviderLoginHttpMethod,
    ProviderLoginProfile,
    ProviderLoginTransitionRule,
)


def load_provider_login_profiles(path: Path) -> tuple[ProviderLoginProfile, ...]:
    if not path.exists():
        raise FileNotFoundError(path)
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("provider login registry root must be a mapping")
    if payload.get("version") != 1:
        raise ValueError("unsupported provider login registry version")
    raw_profiles = payload.get("profiles")
    if not isinstance(raw_profiles, list):
        raise ValueError("provider login profiles must be a list")
    profiles = tuple(_profile(item) for item in raw_profiles)
    ids = [profile.id for profile in profiles]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate provider login profile id")
    sources = [profile.source_id for profile in profiles]
    if len(sources) != len(set(sources)):
        raise ValueError("duplicate provider login source_id")
    return profiles


def _profile(value: object) -> ProviderLoginProfile:
    mapping = _mapping(value, "provider login profile")
    review = _mapping(mapping.get("review"), "provider login review")
    budgets = _mapping(mapping.get("budgets", {}), "provider login budgets")
    transitions = tuple(
        _transition(item) for item in _list(mapping, "allowed_transitions")
    )
    signals = tuple(
        _challenge(item) for item in _list(mapping, "challenge_signals", required=False)
    )
    return ProviderLoginProfile(
        id=_required_string(mapping, "id"),
        source_id=_required_string(mapping, "source_id"),
        login_url=_required_string(mapping, "login_url"),
        username_selector=_required_string(mapping, "username_selector"),
        secret_selector=_required_string(mapping, "secret_selector"),
        submit_selector=_required_string(mapping, "submit_selector"),
        success_selector=_required_string(mapping, "success_selector"),
        authenticated_probe_url=_required_string(mapping, "authenticated_probe_url"),
        logout_url=_optional_string(mapping, "logout_url"),
        allowed_transitions=transitions,
        challenge_signals=signals,
        review_reference=_required_string(review, "document_reference"),
        reviewed_at=_datetime(review, "reviewed_at"),
        review_expires_at=_optional_datetime(review, "expires_at"),
        max_requests=_int(budgets, "max_requests", 32),
        max_redirects=_int(budgets, "max_redirects", 4),
        timeout_ms=_int(budgets, "timeout_ms", 15_000),
        session_ttl_seconds=_int(budgets, "session_ttl_seconds", 3_600),
    )


def _transition(value: object) -> ProviderLoginTransitionRule:
    mapping = _mapping(value, "provider login transition")
    methods = frozenset(
        ProviderLoginHttpMethod(item) for item in _string_list(mapping, "methods")
    )
    return ProviderLoginTransitionRule(
        host=_required_string(mapping, "host"),
        path_prefix=_required_string(mapping, "path_prefix"),
        methods=methods,
    )


def _challenge(value: object) -> ProviderLoginChallengeSignal:
    mapping = _mapping(value, "provider login challenge signal")
    return ProviderLoginChallengeSignal(
        challenge=ProviderLoginChallenge(_required_string(mapping, "challenge")),
        selector=_required_string(mapping, "selector"),
    )


def _mapping(value: object, label: str) -> dict[object, object]:
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be a mapping")
    return value


def _list(
    value: dict[object, object],
    key: str,
    *,
    required: bool = True,
) -> list[object]:
    item = value.get(key)
    if item is None and not required:
        return []
    if not isinstance(item, list):
        raise ValueError(f"{key} must be a list")
    return item


def _string_list(value: dict[object, object], key: str) -> list[str]:
    items = _list(value, key)
    if any(not isinstance(item, str) or not item.strip() for item in items):
        raise ValueError(f"{key} must be a list of non-empty strings")
    return [str(item).strip() for item in items]


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


def _datetime(value: dict[object, object], key: str) -> datetime:
    item = value.get(key)
    if isinstance(item, datetime):
        return item
    if not isinstance(item, str):
        raise ValueError(f"{key} must be an ISO-8601 datetime")
    normalized = item.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise ValueError(f"{key} must be an ISO-8601 datetime") from exc


def _optional_datetime(value: dict[object, object], key: str) -> datetime | None:
    if value.get(key) is None:
        return None
    return _datetime(value, key)


def _int(value: dict[object, object], key: str, default: int) -> int:
    item = value.get(key, default)
    if not isinstance(item, int) or isinstance(item, bool):
        raise ValueError(f"{key} must be an integer")
    return item
