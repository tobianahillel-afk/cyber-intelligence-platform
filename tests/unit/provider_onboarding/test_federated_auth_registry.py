from __future__ import annotations

from pathlib import Path

import pytest

from cip.modules.provider_onboarding.domain.federated_auth import (
    ProviderFederatedAuthFlow,
)
from cip.modules.provider_onboarding.infrastructure.browser_login_registry import (
    load_provider_federated_auth_profiles,
)

FIXTURE = Path("tests/fixtures/sa16_l17_federated_auth_profiles.yml")


def test_loads_reviewed_controlled_oauth_profile() -> None:
    profiles = load_provider_federated_auth_profiles(FIXTURE)

    assert len(profiles) == 1
    profile = profiles[0]
    assert profile.id == "controlled-oauth-v1"
    assert profile.source_id == "sa16-l17-controlled-provider"
    assert profile.flow is ProviderFederatedAuthFlow.OAUTH2_AUTHORIZATION_CODE_PKCE
    assert profile.client_id == "cip-controlled-public-client"
    assert profile.scopes == ("read",)
    assert profile.requires_pkce


def test_federated_registry_rejects_duplicate_ids_and_sources(tmp_path: Path) -> None:
    payload = FIXTURE.read_text(encoding="utf-8")
    profile = payload.split("profiles:\n", 1)[1]
    path = tmp_path / "duplicate.yml"
    path.write_text(payload + profile, encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate provider federated auth profile id"):
        load_provider_federated_auth_profiles(path)

    second_source_same_id = profile.replace(
        "source_id: sa16-l17-controlled-provider",
        "source_id: another-provider",
    ).replace("id: controlled-oauth-v1", "id: controlled-oauth-v2")
    path.write_text(payload + second_source_same_id, encoding="utf-8")
    load_provider_federated_auth_profiles(path)

    same_source_new_id = profile.replace(
        "id: controlled-oauth-v1",
        "id: controlled-oauth-v2",
    )
    path.write_text(payload + same_source_new_id, encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate provider federated auth source_id"):
        load_provider_federated_auth_profiles(path)


def test_federated_registry_rejects_invalid_shapes(tmp_path: Path) -> None:
    base = FIXTURE.read_text(encoding="utf-8")
    path = tmp_path / "invalid.yml"
    cases = (
        (base.replace("scopes: [read]", "scopes: read"), "scopes must be a list"),
        (
            base.replace(
                "flow: oauth2_authorization_code_pkce",
                "flow: browser_sso",
            ),
            "cannot define OAuth",
        ),
        (
            base.replace("methods: [POST]", "methods: POST"),
            "methods must be a list",
        ),
        (
            base.replace("max_requests: 32", "max_requests: true"),
            "max_requests must be an integer",
        ),
    )
    for payload, match in cases:
        path.write_text(payload, encoding="utf-8")
        with pytest.raises((ValueError, TypeError), match=match):
            load_provider_federated_auth_profiles(path)
