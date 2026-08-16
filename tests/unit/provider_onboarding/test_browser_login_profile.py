from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from cip.modules.provider_onboarding.domain.browser_login import (
    ProviderLoginChallenge,
    ProviderLoginChallengeSignal,
    ProviderLoginHttpMethod,
    ProviderLoginProfile,
    ProviderLoginTransitionRule,
)

NOW = datetime(2026, 8, 17, tzinfo=UTC)


def _rule() -> ProviderLoginTransitionRule:
    return ProviderLoginTransitionRule(
        host="provider.example",
        path_prefix="/",
        methods=frozenset({ProviderLoginHttpMethod.GET, ProviderLoginHttpMethod.POST}),
    )


def _profile(**changes: object) -> ProviderLoginProfile:
    values: dict[str, object] = {
        "id": "provider-login-v1",
        "source_id": "provider",
        "login_url": "https://provider.example/login",
        "username_selector": "#username",
        "secret_selector": "#password",
        "submit_selector": "button[type=submit]",
        "success_selector": "#authenticated",
        "authenticated_probe_url": "https://provider.example/private",
        "allowed_transitions": (_rule(),),
        "review_reference": "AUTH-L16-PROVIDER",
        "reviewed_at": NOW,
        "logout_url": "https://provider.example/logout",
        "challenge_signals": (
            ProviderLoginChallengeSignal(ProviderLoginChallenge.MFA, "#mfa"),
        ),
    }
    values.update(changes)
    return ProviderLoginProfile(**values)  # type: ignore[arg-type]


def test_profile_is_executable_and_transitions_are_method_scoped() -> None:
    profile = _profile(review_expires_at=NOW + timedelta(days=1))

    assert profile.executable_at(NOW)
    assert profile.allows(
        "https://provider.example/login",
        ProviderLoginHttpMethod.POST,
    )
    assert profile.allows(
        "https://provider.example/login",
        ProviderLoginHttpMethod.GET,
    )
    assert not profile.allows(
        "https://other.example/login",
        ProviderLoginHttpMethod.POST,
    )
    assert not profile.executable_at(NOW + timedelta(days=2))


def test_profile_rejects_unapproved_profile_url() -> None:
    rule = ProviderLoginTransitionRule(
        host="provider.example",
        path_prefix="/login",
        methods=frozenset({ProviderLoginHttpMethod.GET, ProviderLoginHttpMethod.POST}),
    )
    with pytest.raises(ValueError, match="outside allowed login transitions"):
        _profile(allowed_transitions=(rule,))


def test_profile_rejects_duplicate_challenge_kind() -> None:
    signals = (
        ProviderLoginChallengeSignal(ProviderLoginChallenge.MFA, "#mfa"),
        ProviderLoginChallengeSignal(ProviderLoginChallenge.MFA, "#mfa-again"),
    )
    with pytest.raises(ValueError, match="challenge kinds"):
        _profile(challenge_signals=signals)


def test_profile_rejects_expiry_before_review() -> None:
    with pytest.raises(ValueError, match="review expiry"):
        _profile(review_expires_at=NOW)


def test_transition_rule_requires_absolute_path_and_methods() -> None:
    with pytest.raises(ValueError, match="path prefix"):
        ProviderLoginTransitionRule(
            host="provider.example",
            path_prefix="login",
            methods=frozenset({ProviderLoginHttpMethod.GET}),
        )
    with pytest.raises(ValueError, match="at least one"):
        ProviderLoginTransitionRule(
            host="provider.example",
            path_prefix="/",
            methods=frozenset(),
        )
