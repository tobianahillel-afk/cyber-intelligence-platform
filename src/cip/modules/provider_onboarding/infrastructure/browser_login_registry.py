from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Protocol

import yaml

from cip.modules.provider_onboarding.domain.browser_login import (
    ProviderLoginChallenge,
    ProviderLoginChallengeSignal,
    ProviderLoginHttpMethod,
    ProviderLoginProfile,
    ProviderLoginTransitionRule,
)
from cip.modules.provider_onboarding.domain.federated_auth import (
    ProviderFederatedAuthFlow,
    ProviderFederatedAuthProfile,
)


class _ProviderProfileIdentity(Protocol):
    id: str
    source_id: str


def load_provider_login_profiles(path: Path) -> tuple[ProviderLoginProfile, ...]:
    raw_profiles = _registry_profiles(path, "provider login")
    profiles = tuple(_profile(item) for item in raw_profiles)
    _unique_profiles(profiles, "provider login")
    return profiles


def load_provider_federated_auth_profiles(
    path: Path,
) -> tuple[ProviderFederatedAuthProfile, ...]:
    raw_profiles = _registry_profiles(path, "provider federated auth")
    profiles = tuple(_federated_profile(item) for item in raw_profiles)
    _unique_profiles(profiles, "provider federated auth")
    return profiles


def _registry_profiles(path: Path, label: str) -> list[object]:
    if not path.exists():
        raise FileNotFoundError(path)
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{label} registry root must be a mapping")
    if payload.get("version") != 1:
        raise ValueError(f"unsupported {label} registry version")
    raw_profiles = payload.get("profiles")
    if not isinstance(raw_profiles, list):
        raise ValueError(f"{label} profiles must be a list")
    return raw_profiles


def _unique_profiles(
    profiles: tuple[_ProviderProfileIdentity, ...],
    label: str,
) -> None:
    ids = [profile.id for profile in profiles]
    if len(ids) != len(set(ids)):
        raise ValueError(f"duplicate {label} profile id")
    sources = [profile.source_id for profile in profiles]
    if len(sources) != len(set(sources)):
        raise ValueError(f"duplicate {label} source_id")


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


def _federated_profile(value: object) -> ProviderFederatedAuthProfile:
    mapping = _mapping(value, "provider federated auth profile")
    review = _mapping(mapping.get("review"), "provider federated auth review")
    budgets = _mapping(mapping.get("budgets", {}), "provider federated auth budgets")
    return ProviderFederatedAuthProfile(
        id=_required_string(mapping, "id"),
        source_id=_required_string(mapping, "source_id"),
        flow=ProviderFederatedAuthFlow(_required_string(mapping, "flow")),
        authorization_url=_required_string(mapping, "authorization_url"),
        redirect_uri=_required_string(mapping, "redirect_uri"),
        client_id=_optional_string(mapping, "client_id"),
        token_url=_optional_string(mapping, "token_url"),
        scopes=tuple(_string_list(mapping, "scopes", required=False)),
        allowed_transitions=tuple(
            _transition(item) for item in _list(mapping, "allowed_transitions")
        ),
        review_reference=_required_string(review, "document_reference"),
        reviewed_at=_datetime(review, "reviewed_at"),
        review_expires_at=_optional_datetime(review, "expires_at"),
        max_requests=_int(budgets, "max_requests", 64),
        max_redirects=_int(budgets, "max_redirects", 8),
        timeout_ms=_int(budgets, "timeout_ms", 30_000),
        material_ttl_seconds=_int(budgets, "material_ttl_seconds", 3_600),
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


def _string_list(
    value: dict[object, object],
    key: str,
    *,
    required: bool = True,
) -> list[str]:
    items = _list(value, key, required=required)
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
