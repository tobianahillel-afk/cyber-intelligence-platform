from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

import pytest

from cip.adapters.sources.public_web import delegated_login_runtime as login_runtime
from cip.modules.provider_onboarding.domain.browser_login import (
    ProviderLoginChallenge,
    ProviderLoginChallengeSignal,
    ProviderLoginHttpMethod,
    ProviderLoginProfile,
    ProviderLoginTransitionRule,
)
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


def _profile(**changes: object) -> ProviderLoginProfile:
    values: dict[str, object] = {
        "id": "controlled-login-v1",
        "source_id": "controlled-provider",
        "login_url": "https://provider.example/login",
        "username_selector": "#username",
        "secret_selector": "#password",
        "submit_selector": "button[type=submit]",
        "success_selector": "#authenticated",
        "authenticated_probe_url": "https://provider.example/private",
        "logout_url": "https://provider.example/logout",
        "allowed_transitions": (
            ProviderLoginTransitionRule(
                host="provider.example",
                path_prefix="/",
                methods=frozenset(
                    {ProviderLoginHttpMethod.GET, ProviderLoginHttpMethod.POST}
                ),
            ),
        ),
        "challenge_signals": (
            ProviderLoginChallengeSignal(ProviderLoginChallenge.MFA, "#mfa"),
        ),
        "review_reference": "AUTH-L16-CONTROLLED",
        "reviewed_at": NOW,
    }
    values.update(changes)
    return ProviderLoginProfile(**values)  # type: ignore[arg-type]


def _entry(*, approved_hosts: frozenset[str] | None = None) -> SourceRegistryEntry:
    policy = SourcePolicy(
        id="controlled-provider",
        name="Controlled provider",
        base_url="https://provider.example/",
        status=SourceStatus.ENABLED,
        source_type=SourceType.BROWSER,
        owner="CIP tests",
        licence="Controlled L16 fixture",
        allowed_data_categories=frozenset({DataCategory.OFFICIAL_DOCUMENT_DISCOVERY}),
        human_review_required=False,
    )
    authorization = SourceAuthorization(
        status=AuthorizationStatus.APPROVED,
        document_reference="AUTH-L16-CONTROLLED",
        reviewed_at=NOW,
        approved_hosts=approved_hosts or frozenset({"provider.example"}),
        approved_path_prefixes=("/",),
        approved_purposes=frozenset({PURPOSE}),
        approved_http_methods=frozenset({HttpMethod.GET, HttpMethod.POST}),
        automated_collection_allowed=True,
    )
    return SourceRegistryEntry(policy, authorization, {})


class _Request:
    def __init__(
        self,
        *,
        url: str = "https://provider.example/private",
        method: str = "GET",
        resource_type: str = "document",
        redirected: bool = False,
    ) -> None:
        self.url = url
        self.method = method
        self.resource_type = resource_type
        self.redirected_from = object() if redirected else None


class _Route:
    def __init__(self, request: _Request) -> None:
        self.request = request
        self.aborted = False
        self.continued = False

    def abort(self) -> None:
        self.aborted = True

    def continue_(self) -> None:
        self.continued = True


class _Locator:
    def __init__(self, *, count: int, visible: bool) -> None:
        self._count = count
        self._visible = visible
        self.first = self

    def count(self) -> int:
        return self._count

    def is_visible(self) -> bool:
        return self._visible


class _Page:
    def __init__(self, visible_selectors: set[str]) -> None:
        self._visible_selectors = visible_selectors

    def locator(self, selector: str) -> _Locator:
        visible = selector in self._visible_selectors
        return _Locator(count=1 if visible else 0, visible=visible)


def test_route_guard_allows_reviewed_get_and_post() -> None:
    for method in ("GET", "POST"):
        route = _Route(_Request(method=method))
        state = login_runtime._NetworkState()

        login_runtime._handle_route(
            route,  # type: ignore[arg-type]
            _entry(),
            _profile(),
            PURPOSE,
            NOW,
            state,
        )

        assert route.continued
        assert not route.aborted
        assert state.denial is None


def test_route_guard_denies_unreviewed_transition_and_method() -> None:
    route = _Route(_Request(url="https://other.example/private"))
    state = login_runtime._NetworkState()
    login_runtime._handle_route(
        route,  # type: ignore[arg-type]
        _entry(),
        _profile(),
        PURPOSE,
        NOW,
        state,
    )
    assert route.aborted
    assert state.denial == "provider_login_transition_denied"

    route = _Route(_Request(method="PUT"))
    state = login_runtime._NetworkState()
    login_runtime._handle_route(
        route,  # type: ignore[arg-type]
        _entry(),
        _profile(),
        PURPOSE,
        NOW,
        state,
    )
    assert route.aborted
    assert state.denial == "provider_login_http_method_denied"


def test_route_guard_enforces_request_and_redirect_budgets() -> None:
    profile = _profile(max_requests=1, max_redirects=0)
    state = login_runtime._NetworkState()
    first = _Route(_Request())
    login_runtime._handle_route(
        first,  # type: ignore[arg-type]
        _entry(),
        profile,
        PURPOSE,
        NOW,
        state,
    )
    assert first.continued

    second = _Route(_Request())
    login_runtime._handle_route(
        second,  # type: ignore[arg-type]
        _entry(),
        profile,
        PURPOSE,
        NOW,
        state,
    )
    assert second.aborted
    assert state.denial == "provider_login_request_budget_exceeded"

    redirect = _Route(_Request(redirected=True))
    redirect_state = login_runtime._NetworkState()
    login_runtime._handle_route(
        redirect,  # type: ignore[arg-type]
        _entry(),
        profile,
        PURPOSE,
        NOW,
        redirect_state,
    )
    assert redirect.aborted
    assert redirect_state.denial == "provider_login_redirect_budget_exceeded"


def test_route_guard_enforces_source_policy_and_blocks_passive_resources() -> None:
    route = _Route(_Request())
    state = login_runtime._NetworkState()
    login_runtime._handle_route(
        route,  # type: ignore[arg-type]
        _entry(approved_hosts=frozenset({"different.example"})),
        _profile(),
        PURPOSE,
        NOW,
        state,
    )
    assert route.aborted
    assert state.denial == "provider_login_source_policy_denied"

    image = _Route(_Request(resource_type="image"))
    image_state = login_runtime._NetworkState()
    login_runtime._handle_route(
        image,  # type: ignore[arg-type]
        _entry(),
        _profile(),
        PURPOSE,
        NOW,
        image_state,
    )
    assert image.aborted
    assert image_state.denial is None


def test_storage_state_accepts_only_profile_hosts() -> None:
    profile = _profile()
    raw = json.dumps(
        {
            "cookies": [
                {"name": "sid", "value": "opaque", "domain": ".provider.example"}
            ],
            "origins": [
                {
                    "origin": "https://provider.example",
                    "localStorage": [{"name": "state", "value": "opaque"}],
                }
            ],
        }
    )

    parsed = login_runtime._parse_storage_state(raw, profile)

    assert parsed["cookies"][0]["name"] == "sid"


def test_storage_state_rejects_off_scope_cookie_origin_and_bad_json() -> None:
    profile = _profile()
    cookie = json.dumps(
        {
            "cookies": [{"name": "sid", "value": "x", "domain": "evil.example"}],
            "origins": [],
        }
    )
    with pytest.raises(login_runtime.ProviderSessionInvalidError, match="cookie_origin_denied"):
        login_runtime._parse_storage_state(cookie, profile)

    origin = json.dumps(
        {
            "cookies": [],
            "origins": [{"origin": "https://evil.example", "localStorage": []}],
        }
    )
    with pytest.raises(login_runtime.ProviderSessionInvalidError, match="origin_denied"):
        login_runtime._parse_storage_state(origin, profile)

    with pytest.raises(login_runtime.ProviderSessionInvalidError, match="json_invalid"):
        login_runtime._parse_storage_state("{broken", profile)


def test_challenge_signal_stops_login() -> None:
    with pytest.raises(login_runtime.ProviderLoginChallengeError) as exc_info:
        login_runtime._raise_challenge(
            _Page({"#mfa"}),  # type: ignore[arg-type]
            _profile(),
        )

    assert exc_info.value.challenge is ProviderLoginChallenge.MFA


def test_execution_rejects_profile_source_mismatch_and_expired_review() -> None:
    with pytest.raises(login_runtime.ProviderLoginPolicyError, match="source mismatch"):
        login_runtime._validate_execution(
            _entry(),
            _profile(source_id="other-provider"),
            purpose=PURPOSE,
            now=NOW,
        )

    with pytest.raises(login_runtime.ProviderLoginPolicyError, match="review expired"):
        login_runtime._validate_execution(
            _entry(),
            _profile(review_expires_at=NOW + timedelta(seconds=1)),
            purpose=PURPOSE,
            now=NOW + timedelta(seconds=2),
        )
