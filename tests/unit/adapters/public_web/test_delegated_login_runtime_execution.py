from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from cip.adapters.sources.public_web import delegated_login_runtime as runtime
from cip.modules.provider_onboarding.domain.browser_login import (
    ProviderLoginHttpMethod,
    ProviderLoginProfile,
    ProviderLoginTransitionRule,
)
from cip.modules.provider_onboarding.domain.models import SecretReference
from cip.modules.source_governance.domain.models import (
    AuthorizationStatus,
    DataCategory,
    HttpMethod,
    SourceAuthorization,
    SourcePolicy,
    SourceStatus,
    SourceType,
)
from cip.modules.source_governance.infrastructure.registry import SourceRegistryEntry

NOW = datetime(2026, 8, 17, tzinfo=UTC)
PURPOSE = "authenticated-provider-research"


def _profile(*, logout: bool = True) -> ProviderLoginProfile:
    return ProviderLoginProfile(
        id="controlled-login-v1",
        source_id="controlled-provider",
        login_url="https://provider.example/login",
        username_selector="#username",
        secret_selector="#password",
        submit_selector="button[type=submit]",
        success_selector="#authenticated",
        authenticated_probe_url="https://provider.example/private",
        logout_url="https://provider.example/logout" if logout else None,
        allowed_transitions=(
            ProviderLoginTransitionRule(
                host="provider.example",
                path_prefix="/",
                methods=frozenset(
                    {ProviderLoginHttpMethod.GET, ProviderLoginHttpMethod.POST}
                ),
            ),
        ),
        review_reference="AUTH-L16-CONTROLLED",
        reviewed_at=NOW,
    )


def _entry() -> SourceRegistryEntry:
    return SourceRegistryEntry(
        SourcePolicy(
            id="controlled-provider",
            name="Controlled provider",
            base_url="https://provider.example/",
            status=SourceStatus.ENABLED,
            source_type=SourceType.BROWSER,
            owner="CIP tests",
            licence="controlled",
            allowed_data_categories=frozenset(
                {DataCategory.OFFICIAL_DOCUMENT_DISCOVERY}
            ),
            human_review_required=False,
        ),
        SourceAuthorization(
            status=AuthorizationStatus.APPROVED,
            document_reference="AUTH-L16-CONTROLLED",
            reviewed_at=NOW,
            approved_hosts=frozenset({"provider.example"}),
            approved_path_prefixes=("/",),
            approved_purposes=frozenset({PURPOSE}),
            approved_http_methods=frozenset({HttpMethod.GET, HttpMethod.POST}),
            automated_collection_allowed=True,
        ),
        {},
    )


class _SecretResolver:
    def __init__(self, value: str = "controlled-password", *, fail: bool = False) -> None:
        self.value = value
        self.fail = fail

    def resolve(self, _reference: SecretReference) -> str:
        if self.fail:
            raise RuntimeError("backend unavailable")
        return self.value


class _Locator:
    def __init__(
        self,
        selector: str,
        *,
        password_type: bool = True,
        unique: bool = True,
        fail_wait: bool = False,
    ) -> None:
        self.selector = selector
        self.password_type = password_type
        self.unique = unique
        self.fail_wait = fail_wait
        self.first = self
        self.filled: list[str] = []
        self.clicks = 0

    def count(self) -> int:
        if self.selector == "#challenge-never":
            return 0
        return 1 if self.unique else 2

    def is_visible(self) -> bool:
        return False

    def get_attribute(self, name: str) -> str | None:
        if name == "type" and self.selector == "#password":
            return "password" if self.password_type else "text"
        return None

    def fill(self, value: str, *, timeout: int) -> None:
        del timeout
        self.filled.append(value)

    def click(self, *, timeout: int) -> None:
        del timeout
        self.clicks += 1

    def wait_for(self, *, state: str, timeout: int) -> None:
        del state, timeout
        if self.fail_wait:
            raise runtime.PlaywrightTimeoutError("not visible")


class _Page:
    def __init__(
        self,
        *,
        password_type: bool = True,
        unique_username: bool = True,
        fail_success: bool = False,
    ) -> None:
        self.url = "about:blank"
        self.password_type = password_type
        self.unique_username = unique_username
        self.fail_success = fail_success
        self.routes: list[object] = []

    def route(self, pattern: str, callback) -> None:
        self.routes.append((pattern, callback))

    def goto(self, url: str, *, wait_until: str, timeout: int) -> None:
        del wait_until, timeout
        self.url = url

    def wait_for_load_state(self, state: str, *, timeout: int) -> None:
        del state, timeout

    def locator(self, selector: str) -> _Locator:
        if selector == "#username":
            return _Locator(selector, unique=self.unique_username)
        if selector == "#password":
            return _Locator(selector, password_type=self.password_type)
        if selector == "#authenticated":
            return _Locator(selector, fail_wait=self.fail_success)
        return _Locator("#challenge-never")

    def content(self) -> str:
        return "<div id='authenticated'>ok</div>"


class _Context:
    def __init__(self, page: _Page, storage_state=None) -> None:
        self.page = page
        self.initial_storage_state = storage_state
        self.closed = False

    def new_page(self) -> _Page:
        return self.page

    def storage_state(self):
        return {
            "cookies": [
                {
                    "name": "sid",
                    "value": "opaque-session",
                    "domain": "provider.example",
                    "path": "/",
                    "expires": -1,
                    "httpOnly": True,
                    "secure": True,
                    "sameSite": "Lax",
                }
            ],
            "origins": [],
        }

    def close(self) -> None:
        self.closed = True


class _Browser:
    def __init__(self, page: _Page) -> None:
        self.page = page
        self.contexts: list[_Context] = []
        self.closed = False

    def new_context(self, **kwargs) -> _Context:
        context = _Context(self.page, kwargs.get("storage_state"))
        self.contexts.append(context)
        return context

    def close(self) -> None:
        self.closed = True


class _PlaywrightManager:
    def __init__(self, page: _Page) -> None:
        self.browser = _Browser(page)
        self.playwright = SimpleNamespace(
            chromium=SimpleNamespace(launch=lambda **kwargs: self.browser)
        )

    def __enter__(self):
        return self.playwright

    def __exit__(self, *_args) -> None:
        return None


def _install_fake(monkeypatch: pytest.MonkeyPatch, page: _Page) -> _PlaywrightManager:
    manager = _PlaywrightManager(page)
    monkeypatch.setattr(runtime, "sync_playwright", lambda: manager)
    return manager


def test_full_login_path_resolves_secret_once_and_serializes_session(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    page = _Page()
    manager = _install_fake(monkeypatch, page)

    result = runtime.execute_reviewed_provider_login(
        _entry(),
        _profile(),
        account_identifier="controlled-user",
        secret_reference=SecretReference("env://CIP_TEST_LOGIN"),
        secret_resolver=_SecretResolver(),
        purpose=PURPOSE,
        now=NOW,
    )

    assert result.final_url == "https://provider.example/private"
    assert "opaque-session" not in repr(result)
    assert "opaque-session" in result.session_state_json
    assert manager.browser.closed
    assert manager.browser.contexts[0].closed


def test_full_session_reuse_and_logout_paths(monkeypatch: pytest.MonkeyPatch) -> None:
    page = _Page()
    manager = _install_fake(monkeypatch, page)
    session_json = (
        '{"cookies":[{"name":"sid","value":"opaque","domain":"provider.example"}],'
        '"origins":[]}'
    )
    resolver = _SecretResolver(session_json)
    reference = SecretReference("file-secret:///run/secrets/session.json")

    reused = runtime.execute_reviewed_session_reuse(
        _entry(),
        _profile(),
        session_reference=reference,
        session_resolver=resolver,
        purpose=PURPOSE,
        now=NOW,
    )
    assert reused.final_url == "https://provider.example/private"
    assert manager.browser.contexts[0].initial_storage_state is not None

    _install_fake(monkeypatch, _Page())
    assert runtime.execute_reviewed_provider_logout(
        _entry(),
        _profile(),
        session_reference=reference,
        session_resolver=resolver,
        purpose=PURPOSE,
        now=NOW,
    )


def test_login_fails_closed_for_secret_backend_field_shape_and_sentinel(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reference = SecretReference("env://CIP_TEST_LOGIN")
    _install_fake(monkeypatch, _Page())
    with pytest.raises(runtime.ProviderSecretUnavailableError):
        runtime.execute_reviewed_provider_login(
            _entry(),
            _profile(),
            account_identifier="controlled-user",
            secret_reference=reference,
            secret_resolver=_SecretResolver(fail=True),
            purpose=PURPOSE,
            now=NOW,
        )

    _install_fake(monkeypatch, _Page(password_type=False))
    with pytest.raises(runtime.ProviderLoginPolicyError, match="password field"):
        runtime.execute_reviewed_provider_login(
            _entry(),
            _profile(),
            account_identifier="controlled-user",
            secret_reference=reference,
            secret_resolver=_SecretResolver(),
            purpose=PURPOSE,
            now=NOW,
        )

    _install_fake(monkeypatch, _Page(unique_username=False))
    with pytest.raises(runtime.ProviderLoginPolicyError, match="uniquely"):
        runtime.execute_reviewed_provider_login(
            _entry(),
            _profile(),
            account_identifier="controlled-user",
            secret_reference=reference,
            secret_resolver=_SecretResolver(),
            purpose=PURPOSE,
            now=NOW,
        )

    _install_fake(monkeypatch, _Page(fail_success=True))
    with pytest.raises(runtime.ProviderSessionInvalidError, match="not_established"):
        runtime.execute_reviewed_provider_login(
            _entry(),
            _profile(),
            account_identifier="controlled-user",
            secret_reference=reference,
            secret_resolver=_SecretResolver(),
            purpose=PURPOSE,
            now=NOW,
        )


def test_reuse_and_logout_fail_closed_when_session_backend_is_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_fake(monkeypatch, _Page())
    reference = SecretReference("file-secret:///run/secrets/session.json")
    resolver = _SecretResolver(fail=True)

    with pytest.raises(runtime.ProviderSessionInvalidError, match="unavailable"):
        runtime.execute_reviewed_session_reuse(
            _entry(),
            _profile(),
            session_reference=reference,
            session_resolver=resolver,
            purpose=PURPOSE,
            now=NOW,
        )

    assert not runtime.execute_reviewed_provider_logout(
        _entry(),
        _profile(),
        session_reference=reference,
        session_resolver=resolver,
        purpose=PURPOSE,
        now=NOW,
    )
    assert not runtime.execute_reviewed_provider_logout(
        _entry(),
        _profile(logout=False),
        session_reference=reference,
        session_resolver=_SecretResolver("{}"),
        purpose=PURPOSE,
        now=NOW,
    )
