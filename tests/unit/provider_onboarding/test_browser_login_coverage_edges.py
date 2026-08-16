from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from cip.modules.provider_onboarding.domain.browser_login import (
    ProviderLoginChallenge,
    ProviderLoginChallengeSignal,
    ProviderLoginHttpMethod,
    ProviderLoginProfile,
    ProviderLoginTransitionRule,
)
from cip.modules.provider_onboarding.infrastructure.browser_login_registry import (
    load_provider_login_profiles,
)

NOW = datetime(2026, 8, 17, tzinfo=UTC)


def _rule(**changes: object) -> ProviderLoginTransitionRule:
    values: dict[str, object] = {
        "host": "provider.example",
        "path_prefix": "/",
        "methods": frozenset({ProviderLoginHttpMethod.GET, ProviderLoginHttpMethod.POST}),
    }
    values.update(changes)
    return ProviderLoginTransitionRule(**values)  # type: ignore[arg-type]


def _profile(**changes: object) -> ProviderLoginProfile:
    values: dict[str, object] = {
        "id": "provider-login-v1",
        "source_id": "provider",
        "login_url": "https://provider.example/login",
        "username_selector": "#username",
        "secret_selector": "#password",
        "submit_selector": "#submit",
        "success_selector": "#ok",
        "authenticated_probe_url": "https://provider.example/private",
        "allowed_transitions": (_rule(),),
        "review_reference": "AUTH-L16",
        "reviewed_at": NOW,
    }
    values.update(changes)
    return ProviderLoginProfile(**values)  # type: ignore[arg-type]


def test_transition_rule_rejects_invalid_host_path_and_empty_methods() -> None:
    with pytest.raises(ValueError, match="host"):
        _rule(host="bad host")
    with pytest.raises(ValueError, match="path prefix"):
        _rule(path_prefix="relative")
    with pytest.raises(ValueError, match="at least one"):
        _rule(methods=frozenset())


def test_profile_rejects_invalid_urls_selectors_and_review_reference() -> None:
    for changes, match in (
        ({"login_url": "ftp://provider.example/login"}, "absolute HTTP"),
        ({"login_url": "https://user@provider.example/login"}, "user info"),
        ({"login_url": "https://provider.example/login#fragment"}, "fragment"),
        ({"username_selector": ""}, "username_selector"),
        ({"secret_selector": "x\x00y"}, "secret_selector"),
        ({"review_reference": ""}, "review_reference"),
    ):
        with pytest.raises(ValueError, match=match):
            _profile(**changes)


def test_profile_rejects_invalid_transition_challenge_and_budget_counts() -> None:
    with pytest.raises(ValueError, match="transition rules"):
        _profile(allowed_transitions=())
    with pytest.raises(ValueError, match="transition rules"):
        _profile(allowed_transitions=tuple(_rule() for _ in range(33)))
    with pytest.raises(ValueError, match="challenge signals"):
        _profile(
            challenge_signals=tuple(
                ProviderLoginChallengeSignal(
                    challenge=ProviderLoginChallenge.MFA,
                    selector=f"#challenge-{index}",
                )
                for index in range(33)
            )
        )
    for changes, match in (
        ({"max_requests": 0}, "max_requests"),
        ({"max_requests": 257}, "max_requests"),
        ({"max_redirects": 11}, "max_redirects"),
        ({"timeout_ms": 499}, "timeout_ms"),
        ({"session_ttl_seconds": 59}, "session_ttl_seconds"),
        ({"session_ttl_seconds": 86_401}, "session_ttl_seconds"),
    ):
        with pytest.raises(ValueError, match=match):
            _profile(**changes)


def test_profile_review_expiry_and_path_matching_are_fail_closed() -> None:
    profile = _profile(review_expires_at=NOW + timedelta(seconds=1))
    assert profile.executable_at(NOW)
    assert not profile.executable_at(NOW + timedelta(seconds=1))
    assert profile.allows(
        "https://provider.example/deep/path",
        ProviderLoginHttpMethod.GET,
    )
    assert not profile.allows(
        "https://provider.example/deep/path",
        ProviderLoginHttpMethod("POST"),
    ) is True


def test_registry_rejects_missing_file_root_shape_and_profile_list(tmp_path: Path) -> None:
    missing = tmp_path / "missing.yml"
    with pytest.raises(FileNotFoundError):
        load_provider_login_profiles(missing)

    path = tmp_path / "registry.yml"
    path.write_text("- not-a-mapping\n", encoding="utf-8")
    with pytest.raises(ValueError, match="root"):
        load_provider_login_profiles(path)

    path.write_text("version: 1\nprofiles: {}\n", encoding="utf-8")
    with pytest.raises(ValueError, match="profiles must be a list"):
        load_provider_login_profiles(path)


def test_registry_rejects_invalid_nested_shapes_and_values(tmp_path: Path) -> None:
    base = """\
version: 1
profiles:
  - id: p
    source_id: provider
    login_url: https://provider.example/login
    username_selector: '#u'
    secret_selector: '#p'
    submit_selector: '#s'
    success_selector: '#ok'
    authenticated_probe_url: https://provider.example/private
    allowed_transitions:
      - host: provider.example
        path_prefix: /
        methods: [GET, POST]
    review:
      document_reference: AUTH
      reviewed_at: '2026-08-17T00:00:00+00:00'
"""
    path = tmp_path / "registry.yml"
    cases = (
        (base.replace("methods: [GET, POST]", "methods: GET"), "methods must be a list"),
        (base.replace("methods: [GET, POST]", "methods: [GET, '']"), "non-empty strings"),
        (base.replace("reviewed_at: '2026-08-17T00:00:00+00:00'", "reviewed_at: nope"), "ISO-8601"),
        (base.replace("id: p", "id: ''"), "non-empty string"),
        (base.replace("review:\n", "review: []\n"), "review must be a mapping"),
    )
    for payload, match in cases:
        path.write_text(payload, encoding="utf-8")
        with pytest.raises(ValueError, match=match):
            load_provider_login_profiles(path)
