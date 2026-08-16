from __future__ import annotations

from pathlib import Path

import pytest

from cip.modules.provider_onboarding.domain.browser_login import ProviderLoginChallenge
from cip.modules.provider_onboarding.infrastructure.browser_login_registry import (
    load_provider_login_profiles,
)

_VALID = """\
version: 1
profiles:
  - id: controlled-login-v1
    source_id: controlled-provider
    login_url: https://provider.example/login
    username_selector: '#username'
    secret_selector: '#password'
    submit_selector: 'button[type=submit]'
    success_selector: '#authenticated'
    authenticated_probe_url: https://provider.example/private
    logout_url: https://provider.example/logout
    allowed_transitions:
      - host: provider.example
        path_prefix: /
        methods: [GET, POST]
    challenge_signals:
      - challenge: mfa
        selector: '#mfa'
    review:
      document_reference: AUTH-L16-CONTROLLED
      reviewed_at: '2026-08-17T00:00:00+00:00'
      expires_at: '2026-09-17T00:00:00+00:00'
    budgets:
      max_requests: 24
      max_redirects: 3
      timeout_ms: 5000
      session_ttl_seconds: 1800
"""


def test_login_registry_loads_reviewed_profile(tmp_path: Path) -> None:
    path = tmp_path / "login.yml"
    path.write_text(_VALID, encoding="utf-8")

    profile = load_provider_login_profiles(path)[0]

    assert profile.id == "controlled-login-v1"
    assert profile.source_id == "controlled-provider"
    assert profile.max_requests == 24
    assert profile.challenge_signals[0].challenge is ProviderLoginChallenge.MFA


def test_login_registry_rejects_duplicate_source(tmp_path: Path) -> None:
    path = tmp_path / "login.yml"
    duplicate_profile = _VALID.split("profiles:\n", 1)[1]
    path.write_text(_VALID + duplicate_profile, encoding="utf-8")

    with pytest.raises(ValueError, match="duplicate"):
        load_provider_login_profiles(path)


def test_login_registry_rejects_unknown_version(tmp_path: Path) -> None:
    path = tmp_path / "login.yml"
    path.write_text(_VALID.replace("version: 1", "version: 2"), encoding="utf-8")

    with pytest.raises(ValueError, match="unsupported"):
        load_provider_login_profiles(path)
