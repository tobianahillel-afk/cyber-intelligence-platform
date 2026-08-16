from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from urllib.parse import urlsplit

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import Locator, Page, Route, sync_playwright
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from cip.adapters.sources.public_web.collection_policy import (
    PublicWebCollectionDeniedError,
    authorize_public_web_url,
)
from cip.modules.provider_onboarding.application.secrets import SecretValueResolver
from cip.modules.provider_onboarding.domain.browser_login import (
    ProviderLoginChallenge,
    ProviderLoginHttpMethod,
    ProviderLoginProfile,
)
from cip.modules.provider_onboarding.domain.models import SecretReference
from cip.modules.source_governance.application.session_material import (
    MAX_SESSION_MATERIAL_BYTES,
)
from cip.modules.source_governance.domain.models import HttpMethod
from cip.modules.source_governance.infrastructure.registry import SourceRegistryEntry
from cip.shared.kernel.time import require_aware_utc

_BLOCKED_RESOURCE_TYPES = frozenset({"font", "image", "media"})
_MAX_COOKIES = 64
_MAX_ORIGINS = 16
_MAX_LOCAL_STORAGE = 128
_MAX_SESSION_FIELD_CHARS = 16_384


class ProviderLoginRuntimeError(RuntimeError):
    pass


class ProviderLoginPolicyError(ProviderLoginRuntimeError):
    pass


class ProviderSecretUnavailableError(ProviderLoginRuntimeError):
    pass


class ProviderSessionInvalidError(ProviderLoginRuntimeError):
    pass


class ProviderLoginChallengeError(ProviderLoginRuntimeError):
    def __init__(self, challenge: ProviderLoginChallenge) -> None:
        self.challenge = challenge
        super().__init__(f"provider_login_challenge:{challenge.value}")


@dataclass(frozen=True, slots=True)
class ProviderAuthenticatedRuntimeResult:
    final_url: str
    html: bytes
    session_state_json: str = field(repr=False)
    requests_seen: int = 0
    redirects_seen: int = 0


@dataclass(slots=True)
class _NetworkState:
    requests_seen: int = 0
    redirects_seen: int = 0
    denial: str | None = None


def execute_reviewed_provider_login(
    entry: SourceRegistryEntry,
    profile: ProviderLoginProfile,
    *,
    account_identifier: str,
    secret_reference: SecretReference,
    secret_resolver: SecretValueResolver,
    purpose: str,
    now: datetime,
) -> ProviderAuthenticatedRuntimeResult:
    current = _validate_execution(entry, profile, purpose=purpose, now=now)
    state = _NetworkState()
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True, chromium_sandbox=True)
        context = browser.new_context(
            accept_downloads=False,
            bypass_csp=False,
            ignore_https_errors=False,
            java_script_enabled=True,
            service_workers="block",
        )
        try:
            page = context.new_page()
            _install_guard(page, entry, profile, purpose, current, state)
            _goto(page, profile.login_url, profile.timeout_ms, state)
            _raise_challenge(page, profile)
            username = _unique_locator(page, profile.username_selector, "username")
            secret_field = _unique_locator(page, profile.secret_selector, "secret")
            if (secret_field.get_attribute("type") or "").lower() != "password":
                raise ProviderLoginPolicyError("reviewed secret selector is not a password field")
            submit = _unique_locator(page, profile.submit_selector, "submit")
            username.fill(account_identifier, timeout=profile.timeout_ms)
            try:
                secret_value = secret_resolver.resolve(secret_reference)
            except RuntimeError:
                raise ProviderSecretUnavailableError("provider_secret_unavailable") from None
            try:
                secret_field.fill(secret_value, timeout=profile.timeout_ms)
            finally:
                secret_value = ""
            submit.click(timeout=profile.timeout_ms)
            _wait_after_submit(page, profile.timeout_ms, state)
            _raise_challenge(page, profile)
            _require_authenticated(page, profile)
            _goto(page, profile.authenticated_probe_url, profile.timeout_ms, state)
            _raise_challenge(page, profile)
            _require_authenticated(page, profile)
            session_state = _serialize_storage_state(context.storage_state(), profile)
            return ProviderAuthenticatedRuntimeResult(
                final_url=page.url,
                html=page.content().encode("utf-8"),
                session_state_json=session_state,
                requests_seen=state.requests_seen,
                redirects_seen=state.redirects_seen,
            )
        finally:
            context.close()
            browser.close()


def execute_reviewed_session_reuse(
    entry: SourceRegistryEntry,
    profile: ProviderLoginProfile,
    *,
    session_reference: SecretReference,
    session_resolver: SecretValueResolver,
    purpose: str,
    now: datetime,
) -> ProviderAuthenticatedRuntimeResult:
    current = _validate_execution(entry, profile, purpose=purpose, now=now)
    try:
        raw_state = session_resolver.resolve(session_reference)
    except RuntimeError:
        raise ProviderSessionInvalidError("delegated_session_unavailable") from None
    storage_state = _parse_storage_state(raw_state, profile)
    raw_state = ""
    state = _NetworkState()
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True, chromium_sandbox=True)
        context = browser.new_context(
            storage_state=storage_state,
            accept_downloads=False,
            bypass_csp=False,
            ignore_https_errors=False,
            java_script_enabled=True,
            service_workers="block",
        )
        try:
            page = context.new_page()
            _install_guard(page, entry, profile, purpose, current, state)
            _goto(page, profile.authenticated_probe_url, profile.timeout_ms, state)
            _raise_challenge(page, profile)
            _require_authenticated(page, profile)
            refreshed = _serialize_storage_state(context.storage_state(), profile)
            return ProviderAuthenticatedRuntimeResult(
                final_url=page.url,
                html=page.content().encode("utf-8"),
                session_state_json=refreshed,
                requests_seen=state.requests_seen,
                redirects_seen=state.redirects_seen,
            )
        finally:
            context.close()
            browser.close()


def execute_reviewed_provider_logout(
    entry: SourceRegistryEntry,
    profile: ProviderLoginProfile,
    *,
    session_reference: SecretReference,
    session_resolver: SecretValueResolver,
    purpose: str,
    now: datetime,
) -> bool:
    if profile.logout_url is None:
        return False
    current = _validate_execution(entry, profile, purpose=purpose, now=now)
    try:
        raw_state = session_resolver.resolve(session_reference)
    except RuntimeError:
        return False
    storage_state = _parse_storage_state(raw_state, profile)
    raw_state = ""
    state = _NetworkState()
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True, chromium_sandbox=True)
        context = browser.new_context(
            storage_state=storage_state,
            accept_downloads=False,
            bypass_csp=False,
            ignore_https_errors=False,
            java_script_enabled=True,
            service_workers="block",
        )
        try:
            page = context.new_page()
            _install_guard(page, entry, profile, purpose, current, state)
            _goto(page, profile.logout_url, profile.timeout_ms, state)
            _raise_challenge(page, profile)
            return True
        finally:
            context.close()
            browser.close()


def _validate_execution(
    entry: SourceRegistryEntry,
    profile: ProviderLoginProfile,
    *,
    purpose: str,
    now: datetime,
) -> datetime:
    current = require_aware_utc(now, field_name="now")
    if profile.source_id != entry.policy.id:
        raise ProviderLoginPolicyError("login profile source mismatch")
    if not profile.executable_at(current):
        raise ProviderLoginPolicyError("login profile review expired")
    authorize_public_web_url(
        entry,
        profile.login_url,
        now=current,
        http_method=HttpMethod.GET,
        purpose=purpose,
    )
    return current


def _install_guard(
    page: Page,
    entry: SourceRegistryEntry,
    profile: ProviderLoginProfile,
    purpose: str,
    now: datetime,
    state: _NetworkState,
) -> None:
    page.route(
        "**/*",
        lambda route: _handle_route(route, entry, profile, purpose, now, state),
    )


def _handle_route(
    route: Route,
    entry: SourceRegistryEntry,
    profile: ProviderLoginProfile,
    purpose: str,
    now: datetime,
    state: _NetworkState,
) -> None:
    request = route.request
    state.requests_seen += 1
    if state.requests_seen > profile.max_requests:
        _deny(route, state, "provider_login_request_budget_exceeded")
        return
    if request.redirected_from is not None:
        state.redirects_seen += 1
        if state.redirects_seen > profile.max_redirects:
            _deny(route, state, "provider_login_redirect_budget_exceeded")
            return
    if request.resource_type in _BLOCKED_RESOURCE_TYPES:
        route.abort()
        return
    try:
        method = ProviderLoginHttpMethod(request.method.upper())
    except ValueError:
        _deny(route, state, "provider_login_http_method_denied")
        return
    if not profile.allows(request.url, method):
        _deny(route, state, "provider_login_transition_denied")
        return
    try:
        authorize_public_web_url(
            entry,
            request.url,
            now=now,
            http_method=HttpMethod(method.value),
            purpose=purpose,
        )
    except PublicWebCollectionDeniedError:
        _deny(route, state, "provider_login_source_policy_denied")
        return
    route.continue_()


def _goto(page: Page, url: str, timeout_ms: int, state: _NetworkState) -> None:
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
    except PlaywrightError as exc:
        _raise_network_denial(state, exc)
        raise ProviderLoginRuntimeError("provider_browser_navigation_failed") from exc
    _raise_network_denial(state)


def _wait_after_submit(page: Page, timeout_ms: int, state: _NetworkState) -> None:
    try:
        page.wait_for_load_state("domcontentloaded", timeout=timeout_ms)
    except PlaywrightTimeoutError:
        pass
    except PlaywrightError as exc:
        _raise_network_denial(state, exc)
        raise ProviderLoginRuntimeError("provider_login_submit_failed") from exc
    _raise_network_denial(state)


def _raise_challenge(page: Page, profile: ProviderLoginProfile) -> None:
    for signal in profile.challenge_signals:
        locator = page.locator(signal.selector)
        if locator.count() > 0 and locator.first.is_visible():
            raise ProviderLoginChallengeError(signal.challenge)


def _require_authenticated(page: Page, profile: ProviderLoginProfile) -> None:
    try:
        page.locator(profile.success_selector).first.wait_for(
            state="visible",
            timeout=profile.timeout_ms,
        )
    except PlaywrightTimeoutError:
        raise ProviderSessionInvalidError("provider_authentication_not_established") from None


def _unique_locator(page: Page, selector: str, label: str) -> Locator:
    locator = page.locator(selector)
    if locator.count() != 1:
        raise ProviderLoginPolicyError(f"reviewed {label} selector did not resolve uniquely")
    return locator.first


def _serialize_storage_state(value: dict[str, Any], profile: ProviderLoginProfile) -> str:
    _validate_storage_state(value, profile)
    serialized = json.dumps(value, sort_keys=True, separators=(",", ":"))
    if len(serialized.encode("utf-8")) > MAX_SESSION_MATERIAL_BYTES:
        raise ProviderSessionInvalidError("provider_session_state_exceeds_budget")
    return serialized


def _parse_storage_state(raw: str, profile: ProviderLoginProfile) -> dict[str, Any]:
    if not raw or len(raw.encode("utf-8")) > MAX_SESSION_MATERIAL_BYTES:
        raise ProviderSessionInvalidError("delegated_session_size_invalid")
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        raise ProviderSessionInvalidError("delegated_session_json_invalid") from None
    if not isinstance(payload, dict):
        raise ProviderSessionInvalidError("delegated_session_shape_invalid")
    _validate_storage_state(payload, profile)
    return payload


def _validate_storage_state(value: dict[str, Any], profile: ProviderLoginProfile) -> None:
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
    _bounded_session_text(name)
    _bounded_session_text(cookie_value)


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
        _bounded_session_text(name)
        _bounded_session_text(stored_value)


def _bounded_session_text(value: object) -> None:
    if not isinstance(value, str) or len(value) > _MAX_SESSION_FIELD_CHARS:
        raise ProviderSessionInvalidError("provider_session_field_budget_exceeded")


def _host_allowed(host: str, allowed_hosts: set[str]) -> bool:
    return any(host == allowed or host.endswith(f".{allowed}") for allowed in allowed_hosts)


def _raise_network_denial(state: _NetworkState, exc: Exception | None = None) -> None:
    if state.denial is not None:
        if exc is None:
            raise ProviderLoginPolicyError(state.denial)
        raise ProviderLoginPolicyError(state.denial) from exc


def _deny(route: Route, state: _NetworkState, reason: str) -> None:
    state.denial = state.denial or reason
    route.abort()
