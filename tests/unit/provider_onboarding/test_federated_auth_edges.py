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


def _profile(**changes: object) -> ProviderFederatedAuthProfile:
    values: dict[str, object] = {
        "id": "profile",
        "source_id": "provider",
        "flow": ProviderFederatedAuthFlow.OAUTH2_AUTHORIZATION_CODE_PKCE,
        "authorization_url": "https://provider.example/oauth/authorize",
        "redirect_uri": "http://127.0.0.1/oauth/callback",
        "client_id": "client",
        "token_url": "https://provider.example/oauth/token",
        "scopes": ("read",),
        "allowed_transitions": _transitions(),
        "review_reference": "AUTH-L17",
        "reviewed_at": NOW,
    }
    values.update(changes)
    return ProviderFederatedAuthProfile(**values)  # type: ignore[arg-type]


def test_review_expiry_must_follow_review_time() -> None:
    with pytest.raises(ValueError, match="expiry must follow"):
        _profile(review_expires_at=NOW)


@pytest.mark.parametrize(
    ("changes", "match"),
    [
        ({"allowed_transitions": ()}, "transitions"),
        ({"allowed_transitions": _transitions() * 11}, "transitions"),
        ({"scopes": tuple(f"s{i}" for i in range(33))}, "scopes"),
        ({"max_requests": 0}, "max_requests"),
        ({"max_requests": 257}, "max_requests"),
        ({"max_redirects": -1}, "max_redirects"),
        ({"max_redirects": 17}, "max_redirects"),
        ({"timeout_ms": 499}, "timeout_ms"),
        ({"timeout_ms": 120_001}, "timeout_ms"),
        ({"material_ttl_seconds": 59}, "material_ttl_seconds"),
        ({"material_ttl_seconds": 86_401}, "material_ttl_seconds"),
    ],
)
def test_profile_budgets_and_cardinality_are_bounded(
    changes: dict[str, object],
    match: str,
) -> None:
    with pytest.raises(ValueError, match=match):
        _profile(**changes)


def test_authorization_and_redirect_transitions_must_be_reviewed() -> None:
    with pytest.raises(ValueError, match="authorization URL"):
        _profile(allowed_transitions=_transitions()[1:])
    with pytest.raises(ValueError, match="redirect URI"):
        _profile(allowed_transitions=_transitions()[:2])


@pytest.mark.parametrize(
    ("field", "value", "match"),
    [
        ("id", " ", "profile id"),
        ("source_id", "bad\x00source", "source id"),
        ("review_reference", "x" * 501, "review_reference"),
        ("authorization_url", "ftp://provider.example/x", "absolute HTTP"),
        ("authorization_url", "https:///missing-host", "absolute HTTP"),
        ("authorization_url", "https://user@provider.example/x", "user info"),
        ("authorization_url", "https://provider.example/x#fragment", "fragment"),
        ("authorization_url", "https://provider.example/" + "x" * 2000, "2000"),
    ],
)
def test_profile_rejects_invalid_identity_and_urls(
    field: str,
    value: str,
    match: str,
) -> None:
    with pytest.raises(ValueError, match=match):
        _profile(**{field: value})


def test_callback_rejects_user_info_fragment_port_and_accepts_default_port() -> None:
    profile = _profile()
    assert profile.callback_matches(
        "http://127.0.0.1:80/oauth/callback?code=x&state=y"
    )
    assert not profile.callback_matches(
        "http://user@127.0.0.1/oauth/callback?code=x&state=y"
    )
    assert not profile.callback_matches(
        "http://127.0.0.1:81/oauth/callback?code=x&state=y"
    )
    assert not profile.callback_matches(
        "http://127.0.0.1/oauth/callback?code=x#fragment"
    )


def test_transition_path_matching_is_segment_bounded() -> None:
    profile = _profile()
    assert profile.allows(
        "https://provider.example/oauth/authorize/consent",
        ProviderLoginHttpMethod.GET,
    )
    assert not profile.allows(
        "https://provider.example/oauth/authorize-evil",
        ProviderLoginHttpMethod.GET,
    )
    assert not profile.allows(
        "https://provider.example/oauth/token",
        ProviderLoginHttpMethod.GET,
    )


def test_https_redirect_default_port_and_no_expiry_are_executable() -> None:
    transitions = (
        ProviderLoginTransitionRule(
            host="provider.example",
            path_prefix="/sso",
            methods=frozenset({ProviderLoginHttpMethod.GET}),
        ),
    )
    profile = ProviderFederatedAuthProfile(
        id="sso",
        source_id="provider",
        flow=ProviderFederatedAuthFlow.BROWSER_SSO,
        authorization_url="https://provider.example/sso/start",
        redirect_uri="https://provider.example/sso/complete",
        allowed_transitions=transitions,
        review_reference="AUTH-L17",
        reviewed_at=NOW,
    )
    assert profile.executable_at(NOW + timedelta(days=365))
    assert profile.callback_matches("https://provider.example:443/sso/complete?ok=1")
