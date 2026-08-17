from __future__ import annotations

from datetime import UTC, datetime
from urllib.parse import parse_qs, urlsplit

import pytest

from cip.modules.provider_onboarding.application.federated_authorization import (
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


def _profile(*, oidc: bool = False, authorization_url: str | None = None):
    return ProviderFederatedAuthProfile(
        id="controlled-auth-v1",
        source_id="provider",
        flow=(
            ProviderFederatedAuthFlow.OIDC_AUTHORIZATION_CODE_PKCE
            if oidc
            else ProviderFederatedAuthFlow.OAUTH2_AUTHORIZATION_CODE_PKCE
        ),
        authorization_url=authorization_url or "https://provider.example/oauth/authorize",
        redirect_uri="http://127.0.0.1/oauth/callback",
        client_id="controlled-client",
        token_url="https://provider.example/oauth/token",
        scopes=("read", "profile"),
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


def _tokens(values: list[str]):
    iterator = iter(values)
    return lambda: next(iterator)


def test_oauth_start_builds_state_and_pkce_without_repr_leakage() -> None:
    state = "s" * 48
    verifier = "v" * 64
    started = create_federated_authorization(
        _profile(),
        token_factory=_tokens([state, verifier]),
    )

    query = parse_qs(urlsplit(started.authorization_url).query)
    assert query["response_type"] == ["code"]
    assert query["client_id"] == ["controlled-client"]
    assert query["redirect_uri"] == ["http://127.0.0.1/oauth/callback"]
    assert query["scope"] == ["read profile"]
    assert query["state"] == [state]
    assert query["code_challenge"] == [pkce_s256_challenge(verifier)]
    assert query["code_challenge_method"] == ["S256"]
    assert state not in repr(started)
    assert verifier not in repr(started)


def test_oidc_start_adds_nonce_and_secret_material_round_trips() -> None:
    started = create_federated_authorization(
        _profile(oidc=True),
        token_factory=_tokens(["s" * 48, "v" * 64, "n" * 48]),
    )
    query = parse_qs(urlsplit(started.authorization_url).query)
    assert query["nonce"] == ["n" * 48]

    raw = started.material.to_secret_json()
    restored = FederatedAuthorizationMaterial.from_secret_json(raw)
    assert restored == started.material
    assert "v" * 64 not in repr(restored)


def test_callback_requires_exact_redirect_state_and_single_code() -> None:
    started = create_federated_authorization(
        _profile(),
        token_factory=_tokens(["s" * 48, "v" * 64]),
    )
    accepted = validate_federated_callback(
        _profile(),
        f"http://127.0.0.1/oauth/callback?code=abc&state={'s' * 48}",
        started.material,
    )
    assert "abc" not in repr(accepted)

    with pytest.raises(FederatedStateMismatchError, match="state_mismatch"):
        validate_federated_callback(
            _profile(),
            f"http://127.0.0.1/oauth/callback?code=abc&state={'x' * 48}",
            started.material,
        )
    with pytest.raises(FederatedStateMismatchError, match="redirect_mismatch"):
        validate_federated_callback(
            _profile(),
            f"http://127.0.0.1/wrong?code=abc&state={'s' * 48}",
            started.material,
        )
    with pytest.raises(FederatedStateMismatchError, match="code_missing_or_ambiguous"):
        validate_federated_callback(
            _profile(),
            f"http://127.0.0.1/oauth/callback?state={'s' * 48}",
            started.material,
        )


def test_callback_provider_error_is_typed_without_description() -> None:
    started = create_federated_authorization(
        _profile(),
        token_factory=_tokens(["s" * 48, "v" * 64]),
    )
    with pytest.raises(FederatedProviderRejectedError) as captured:
        validate_federated_callback(
            _profile(),
            "http://127.0.0.1/oauth/callback?error=access_denied&error_description=private",
            started.material,
        )
    assert captured.value.error_code == "access_denied"
    assert "private" not in str(captured.value)


def test_authorization_url_cannot_preseed_reserved_oauth_parameters() -> None:
    with pytest.raises(ValueError, match="reserved OAuth"):
        create_federated_authorization(
            _profile(
                authorization_url="https://provider.example/oauth/authorize?state=fixed"
            ),
            token_factory=_tokens(["s" * 48, "v" * 64]),
        )


def test_secret_material_parser_rejects_unknown_or_oversized_shapes() -> None:
    with pytest.raises(ValueError, match="shape"):
        FederatedAuthorizationMaterial.from_secret_json(
            '{"version":1,"profile_id":"x","state":"x","code_verifier":"x","nonce":null,"extra":1}'
        )
    with pytest.raises(ValueError, match="too large"):
        FederatedAuthorizationMaterial.from_secret_json("x" * 20_000)
