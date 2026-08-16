from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any, cast
from urllib.parse import urlsplit

from playwright.sync_api import StorageState

from cip.modules.provider_onboarding.domain.browser_login import ProviderLoginProfile
from cip.modules.source_governance.application.session_material import (
    MAX_SESSION_MATERIAL_BYTES,
)

_MAX_COOKIES = 64
_MAX_ORIGINS = 16
_MAX_LOCAL_STORAGE = 128
_MAX_SESSION_FIELD_CHARS = 16_384


class ProviderSessionInvalidError(RuntimeError):
    pass


def serialize_storage_state(value: StorageState, profile: ProviderLoginProfile) -> str:
    validate_storage_state(value, profile)
    serialized = json.dumps(value, sort_keys=True, separators=(",", ":"))
    if len(serialized.encode("utf-8")) > MAX_SESSION_MATERIAL_BYTES:
        raise ProviderSessionInvalidError("provider_session_state_exceeds_budget")
    return serialized


def parse_storage_state(raw: str, profile: ProviderLoginProfile) -> StorageState:
    if not raw or len(raw.encode("utf-8")) > MAX_SESSION_MATERIAL_BYTES:
        raise ProviderSessionInvalidError("delegated_session_size_invalid")
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        raise ProviderSessionInvalidError("delegated_session_json_invalid") from None
    if not isinstance(payload, dict):
        raise ProviderSessionInvalidError("delegated_session_shape_invalid")
    validate_storage_state(payload, profile)
    return cast(StorageState, payload)


def validate_storage_state(
    value: Mapping[str, Any],
    profile: ProviderLoginProfile,
) -> None:
    cookies = value.get("cookies")
    origins = value.get("origins")
    if not isinstance(cookies, list) or not isinstance(origins, list):
        raise ProviderSessionInvalidError("provider_session_shape_invalid")
    if len(cookies) > _MAX_COOKIES or len(origins) > _MAX_ORIGINS:
        raise ProviderSessionInvalidError("provider_session_entry_budget_exceeded")
    allowed_hosts = {rule.host for rule in profile.allowed_transitions}
    for cookie in cookies:
        _validate_cookie(cookie, allowed_hosts)
    for origin in origins:
        _validate_origin(origin, allowed_hosts)


def _validate_cookie(value: object, allowed_hosts: set[str]) -> None:
    if not isinstance(value, dict):
        raise ProviderSessionInvalidError("provider_session_cookie_invalid")
    domain = value.get("domain")
    name = value.get("name")
    cookie_value = value.get("value")
    if not all(isinstance(item, str) for item in (domain, name, cookie_value)):
        raise ProviderSessionInvalidError("provider_session_cookie_invalid")
    assert isinstance(domain, str)
    host = domain.lstrip(".").lower()
    if not _host_allowed(host, allowed_hosts):
        raise ProviderSessionInvalidError("provider_session_cookie_origin_denied")
    _bounded_text(name)
    _bounded_text(cookie_value)


def _validate_origin(value: object, allowed_hosts: set[str]) -> None:
    if not isinstance(value, dict):
        raise ProviderSessionInvalidError("provider_session_origin_invalid")
    origin = value.get("origin")
    storage = value.get("localStorage")
    if not isinstance(origin, str) or not isinstance(storage, list):
        raise ProviderSessionInvalidError("provider_session_origin_invalid")
    host = (urlsplit(origin).hostname or "").lower()
    if not host or not _host_allowed(host, allowed_hosts):
        raise ProviderSessionInvalidError("provider_session_origin_denied")
    if len(storage) > _MAX_LOCAL_STORAGE:
        raise ProviderSessionInvalidError("provider_session_storage_budget_exceeded")
    for item in storage:
        if not isinstance(item, dict):
            raise ProviderSessionInvalidError("provider_session_storage_invalid")
        name = item.get("name")
        stored_value = item.get("value")
        if not isinstance(name, str) or not isinstance(stored_value, str):
            raise ProviderSessionInvalidError("provider_session_storage_invalid")
        _bounded_text(name)
        _bounded_text(stored_value)


def _bounded_text(value: object) -> None:
    if not isinstance(value, str) or len(value) > _MAX_SESSION_FIELD_CHARS:
        raise ProviderSessionInvalidError("provider_session_field_budget_exceeded")


def _host_allowed(host: str, allowed_hosts: set[str]) -> bool:
    return any(host == allowed or host.endswith(f".{allowed}") for allowed in allowed_hosts)
