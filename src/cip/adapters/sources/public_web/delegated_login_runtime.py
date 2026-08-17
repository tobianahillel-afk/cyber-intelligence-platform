from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import Locator, Page, Route, sync_playwright
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from cip.adapters.sources.public_web.collection_policy import (
    PublicWebCollectionDeniedError,
    authorize_public_web_url,
)
from cip.adapters.sources.public_web.delegated_session_state import (
    ProviderSessionInvalidError,
    parse_storage_state,
    serialize_storage_state,
)
from cip.modules.provider_onboarding.application.secrets import SecretValueResolver
from cip.modules.provider_onboarding.domain.browser_login import (
    ProviderLoginChallenge,
    ProviderLoginHttpMethod,
    ProviderLoginProfile,
)
from cip.modules.provider_onboarding.domain.models import SecretReference
from cip.modules.source_governance.domain.models import HttpMethod
from cip.modules.source_governance.infrastructure.registry import SourceRegistryEntry
from cip.shared.kernel.time import require_aware_utc

_BLOCKED_RESOURCE_TYPES = frozenset({"font", "image", "media"})


class ProviderLoginRuntimeError(RuntimeError):
    pass


class ProviderLoginPolicyError(ProviderLoginRuntimeError):
    pass


class ProviderSecretUnavailableError(ProviderLoginRuntimeError):
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
            session_state = serialize_storage_state(context.storage_state(), profile)
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
    storage_state = parse_storage_state(raw_state, profile)
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
            refreshed = serialize_storage_state(context.storage_state(), profile)
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
    storage_state = parse_storage_state(raw_state, profile)
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


def _raise_network_denial(state: _NetworkState, exc: Exception | None = None) -> None:
    if state.denial is not None:
        if exc is None:
            raise ProviderLoginPolicyError(state.denial)
        raise ProviderLoginPolicyError(state.denial) from exc


def _deny(route: Route, state: _NetworkState, reason: str) -> None:
    state.denial = state.denial or reason
    route.abort()
