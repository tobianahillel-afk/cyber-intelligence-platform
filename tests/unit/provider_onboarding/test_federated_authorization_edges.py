from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest

from cip.modules.provider_onboarding.application.federated_authorization import (
    FederatedAuthorizationCode,
    FederatedAuthorizationMaterial,
    FederatedProviderRejectedError,
    FederatedStateMismatchError,
    create_federated_authorization,
    pkce_s256_challenge,
    validate_federated_callback,
)
from cip.modules.provider_onboarding.domain.browser_login import (
    ProviderLoginHttpMethod,
    ProviderLoginTransitionRule,
)
from cip.modules.provider_onboarding.domain.federated_auth import (
    ProviderFederatedAuthFlow,
    ProviderFederatedAuthProfile,
)

NOW = datetime(2026, 8, 17, tzinfo=UTC)


def _profile(*, oidc: bool = False) -> ProviderFederatedAuthProfile:
    return ProviderFederatedAuthProfile(
        id="profile",
        source_id="provider",
        flow=(
            ProviderFederatedAuthFlow.OIDC_AUTHORIZATION_CODE_PKCE
            if oidc
            else ProviderFederatedAuthFlow.OAUTH2_AUTHORIZATION_CODE_PKCE
        ),
        authorization_url="https://provider.example/oauth/authorize?prompt=consent",
        redirect_uri="http://127.0.0.1/oauth/callback",
        client_id="client",
        token_url="https://provider.example/oauth/token",
        scopes=("read",),
        allowed_transitions=(
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
        ),
        review_reference="AUTH-L17",
        reviewed_at=NOW,
    )


def _material(*, profile_id: str = "profile", nonce: str | None = None):
    return FederatedAuthorizationMaterial(
        profile_id=profile_id,
        state="s" * 48,
        code_verifier="v" * 64,
        nonce=nonce,
    )


@pytest.mark.parametrize(
    ("factory", "match"),
    [
        (
            lambda: FederatedAuthorizationMaterial(
                profile_id="",
                state="s" * 48,
                code_verifier="v" * 64,
            ),
            "profile_id",
        ),
        (
            lambda: FederatedAuthorizationMaterial(
                profile_id="profile",
                state="short",
                code_verifier="v" * 64,
            ),
            "state",
        ),
        (
            lambda: FederatedAuthorizationMaterial(
                profile_id="profile",
                state="s" * 48,
                code_verifier=" padded-verifier-" + "v" * 50 + " ",
            ),
            "code_verifier",
        ),
        (
            lambda: FederatedAuthorizationMaterial(
                profile_id="profile",
                state="s" * 48,
                code_verifier="v" * 64,
                nonce="bad\x00nonce" + "n" * 16,
            ),
            "nonce",
        ),
        (lambda: FederatedAuthorizationCode(""), "authorization code"),
    ],
)
def test_authorization_material_bounds_fail_closed(factory, match: str) -> None:
    with pytest.raises(ValueError, match=match):
        factory()


def test_material_parser_rejects_json_version_types_and_nonce() -> None:
    with pytest.raises(ValueError, match="invalid federated authorization material"):
        FederatedAuthorizationMaterial.from_secret_json("{")
    with pytest.raises(ValueError, match="too large"):
        FederatedAuthorizationMaterial.from_secret_json("x" * 17_000)

    payload = json.loads(_material().to_secret_json())
    payload["version"] = 2
    with pytest.raises(ValueError, match="unsupported"):
        FederatedAuthorizationMaterial.from_secret_json(json.dumps(payload))

    payload = json.loads(_material().to_secret_json())
    payload["state"] = 42
    with pytest.raises(ValueError, match="material fields"):
        FederatedAuthorizationMaterial.from_secret_json(json.dumps(payload))

    payload = json.loads(_material().to_secret_json())
    payload["nonce"] = 42
    with pytest.raises(ValueError, match="authorization nonce"):
        FederatedAuthorizationMaterial.from_secret_json(json.dumps(payload))


def test_oidc_start_adds_nonce_and_existing_safe_query_is_preserved() -> None:
    tokens = iter(("s" * 48, "v" * 64, "n" * 48))
    started = create_federated_authorization(
        _profile(oidc=True),
        token_factory=lambda: next(tokens),
    )
    assert started.material.nonce == "n" * 48
    assert "prompt=consent" in started.authorization_url
    assert "nonce=" in started.authorization_url


def test_non_pkce_profile_cannot_start_authorization_code_flow() -> None:
    transitions = (
        ProviderLoginTransitionRule(
            host="provider.example",
            path_prefix="/sso",
            methods=frozenset({ProviderLoginHttpMethod.GET}),
        ),
    )
    sso = ProviderFederatedAuthProfile(
        id="sso",
        source_id="provider",
        flow=ProviderFederatedAuthFlow.BROWSER_SSO,
        authorization_url="https://provider.example/sso/start",
        redirect_uri="https://provider.example/sso/complete",
        allowed_transitions=transitions,
        review_reference="AUTH-L17",
        reviewed_at=NOW,
    )
    with pytest.raises(ValueError, match="requires an OAuth/OIDC"):
        create_federated_authorization(sso)


def test_callback_rejects_profile_redirect_and_provider_error_edges() -> None:
    profile = _profile()
    with pytest.raises(FederatedStateMismatchError, match="profile_binding"):
        validate_federated_callback(
            profile,
            "http://127.0.0.1/oauth/callback?code=x&state=" + "s" * 48,
            _material(profile_id="other"),
        )
    with pytest.raises(FederatedStateMismatchError, match="redirect_mismatch"):
        validate_federated_callback(
            profile,
            "http://127.0.0.1/other?code=x&state=" + "s" * 48,
            _material(),
        )
    with pytest.raises(FederatedProviderRejectedError, match="invalid_provider_error"):
        validate_federated_callback(
            profile,
            "http://127.0.0.1/oauth/callback?error=&state=" + "s" * 48,
            _material(),
        )
    long_error = "x" * 101
    with pytest.raises(FederatedProviderRejectedError, match="invalid_provider_error"):
        validate_federated_callback(
            profile,
            f"http://127.0.0.1/oauth/callback?error={long_error}&state=" + "s" * 48,
            _material(),
        )


def test_callback_rejects_missing_ambiguous_and_invalid_required_values() -> None:
    profile = _profile()
    material = _material()
    urls = (
        "http://127.0.0.1/oauth/callback?code=x",
        "http://127.0.0.1/oauth/callback?code=x&state=a&state=b",
        "http://127.0.0.1/oauth/callback?code=x&state=",
        "http://127.0.0.1/oauth/callback?state=" + material.state,
        "http://127.0.0.1/oauth/callback?code=&state=" + material.state,
        "http://127.0.0.1/oauth/callback?code=a&code=b&state=" + material.state,
    )
    for url in urls:
        with pytest.raises(FederatedStateMismatchError):
            validate_federated_callback(profile, url, material)

    with pytest.raises(FederatedStateMismatchError, match="error_ambiguous"):
        validate_federated_callback(
            profile,
            "http://127.0.0.1/oauth/callback?error=a&error=b&state=" + material.state,
            material,
        )


def test_pkce_rejects_invalid_verifier_bounds() -> None:
    with pytest.raises(ValueError, match="code_verifier"):
        pkce_s256_challenge("short")
