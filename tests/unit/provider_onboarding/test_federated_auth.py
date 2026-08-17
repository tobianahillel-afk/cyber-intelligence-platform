from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from cip.modules.provider_onboarding.domain.browser_login import (
    ProviderLoginHttpMethod,
    ProviderLoginTransitionRule,
)
from cip.modules.provider_onboarding.domain.federated_auth import (
    ProviderFederatedAuthFlow,
    ProviderFederatedAuthProfile,
)

NOW = datetime(2026, 8, 17, tzinfo=UTC)


def _transitions() -> tuple[ProviderLoginTransitionRule, ...]:
    return (
        ProviderLoginTransitionRule(
            host="provider.example",
            path_prefix="/oauth/authorize",
            methods=frozenset({ProviderLoginHttpMethod.GET}),
        ),
        ProviderLoginTransitionRule(
            host="provider.example",
            path_prefix="/oauth/token",
            methods=frozenset({ProviderLoginHttpMethod.POST}),
        ),
        ProviderLoginTransitionRule(
            host="127.0.0.1",
            path_prefix="/oauth/callback",
            methods=frozenset({ProviderLoginHttpMethod.GET}),
        ),
    )


def _oauth(**changes: object) -> ProviderFederatedAuthProfile:
    values: dict[str, object] = {
        "id": "provider-oauth-v1",
        "source_id": "provider",
        "flow": ProviderFederatedAuthFlow.OAUTH2_AUTHORIZATION_CODE_PKCE,
        "authorization_url": "https://provider.example/oauth/authorize",
        "redirect_uri": "http://127.0.0.1/oauth/callback",
        "client_id": "controlled-public-client",
        "token_url": "https://provider.example/oauth/token",
        "scopes": ("read",),
        "allowed_transitions": _transitions(),
        "review_reference": "AUTH-L17",
        "reviewed_at": NOW,
    }
    values.update(changes)
    return ProviderFederatedAuthProfile(**values)  # type: ignore[arg-type]


def test_oauth_profile_requires_pkce_and_matches_exact_callback() -> None:
    profile = _oauth()

    assert profile.requires_pkce
    assert not profile.requires_nonce
    assert profile.callback_matches("http://127.0.0.1/oauth/callback?code=x&state=y")
    assert not profile.callback_matches("http://127.0.0.1/other?code=x&state=y")
    assert not profile.callback_matches("http://localhost/oauth/callback?code=x&state=y")
    assert profile.allows(
        "https://provider.example/oauth/token",
        ProviderLoginHttpMethod.POST,
    )


def test_oidc_profile_requires_nonce_and_review_expiry_is_fail_closed() -> None:
    profile = _oauth(
        flow=ProviderFederatedAuthFlow.OIDC_AUTHORIZATION_CODE_PKCE,
        review_expires_at=NOW + timedelta(minutes=1),
    )

    assert profile.requires_pkce
    assert profile.requires_nonce
    assert profile.executable_at(NOW)
    assert not profile.executable_at(NOW + timedelta(minutes=1))


def test_browser_sso_cannot_smuggle_oauth_material() -> None:
    transitions = (
        ProviderLoginTransitionRule(
            host="provider.example",
            path_prefix="/sso/start",
            methods=frozenset({ProviderLoginHttpMethod.GET}),
        ),
        ProviderLoginTransitionRule(
            host="provider.example",
            path_prefix="/sso/complete",
            methods=frozenset({ProviderLoginHttpMethod.GET}),
        ),
    )
    profile = ProviderFederatedAuthProfile(
        id="provider-sso-v1",
        source_id="provider",
        flow=ProviderFederatedAuthFlow.BROWSER_SSO,
        authorization_url="https://provider.example/sso/start",
        redirect_uri="https://provider.example/sso/complete",
        allowed_transitions=transitions,
        review_reference="AUTH-L17",
        reviewed_at=NOW,
    )
    assert not profile.requires_pkce
    assert not profile.requires_nonce

    with pytest.raises(ValueError, match="cannot define OAuth"):
        ProviderFederatedAuthProfile(
            id="provider-sso-v2",
            source_id="provider",
            flow=ProviderFederatedAuthFlow.BROWSER_SSO,
            authorization_url="https://provider.example/sso/start",
            redirect_uri="https://provider.example/sso/complete",
            allowed_transitions=transitions,
            review_reference="AUTH-L17",
            reviewed_at=NOW,
            client_id="smuggled-client",
        )


def test_oauth_profile_rejects_missing_contract_and_unsafe_redirects() -> None:
    with pytest.raises(ValueError, match="requires client_id"):
        _oauth(client_id=None)
    with pytest.raises(ValueError, match="requires token_url"):
        _oauth(token_url=None)
    with pytest.raises(ValueError, match="at least one scope"):
        _oauth(scopes=())
    with pytest.raises(ValueError, match="non-loopback redirect_uri"):
        _oauth(redirect_uri="http://callback.example/oauth/callback")
    with pytest.raises(ValueError, match="cannot contain a query"):
        _oauth(redirect_uri="http://127.0.0.1/oauth/callback?fixed=1")


def test_profile_rejects_unreviewed_transition_methods_and_duplicate_scopes() -> None:
    bad_token_transition = (
        *_transitions()[:1],
        ProviderLoginTransitionRule(
            host="provider.example",
            path_prefix="/oauth/token",
            methods=frozenset({ProviderLoginHttpMethod.GET}),
        ),
        *_transitions()[2:],
    )
    with pytest.raises(ValueError, match="token URL is outside reviewed POST"):
        _oauth(allowed_transitions=bad_token_transition)
    with pytest.raises(ValueError, match="unique"):
        _oauth(scopes=("read", "read"))
    with pytest.raises(ValueError, match="whitespace"):
        _oauth(scopes=("read profile",))
