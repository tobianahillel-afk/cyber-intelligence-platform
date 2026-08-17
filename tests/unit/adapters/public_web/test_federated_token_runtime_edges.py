from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime, timedelta

import httpx
import pytest

from cip.adapters.sources.public_web.federated_token_runtime import (
    FederatedTokenExchangeError,
    FederatedTokenMaterial,
    exchange_federated_authorization_code,
)
from cip.modules.provider_onboarding.application.federated_authorization import (
    FederatedAuthorizationCode,
    FederatedAuthorizationMaterial,
)
from cip.modules.provider_onboarding.domain.browser_login import (
    ProviderLoginHttpMethod,
    ProviderLoginTransitionRule,
)
from cip.modules.provider_onboarding.domain.federated_auth import (
    ProviderFederatedAuthFlow,
    ProviderFederatedAuthProfile,
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

NOW = datetime(2026, 8, 17, 10, 0, tzinfo=UTC)
PURPOSE = "authenticated-provider-research"


def _entry() -> SourceRegistryEntry:
    return SourceRegistryEntry(
        SourcePolicy(
            id="provider",
            name="Provider",
            base_url="https://provider.example/",
            status=SourceStatus.ENABLED,
            source_type=SourceType.BROWSER,
            owner="tests",
            licence="controlled",
            allowed_data_categories=frozenset(
                {DataCategory.OFFICIAL_DOCUMENT_DISCOVERY}
            ),
            human_review_required=False,
        ),
        SourceAuthorization(
            status=AuthorizationStatus.APPROVED,
            document_reference="AUTH-L17",
            reviewed_at=NOW,
            approved_hosts=frozenset({"provider.example", "127.0.0.1"}),
            approved_path_prefixes=("/",),
            approved_purposes=frozenset({PURPOSE}),
            approved_http_methods=frozenset({HttpMethod.GET, HttpMethod.POST}),
            automated_collection_allowed=True,
        ),
        {},
    )


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


def _profile(
    *,
    oidc: bool = False,
    review_expires_at: datetime | None = None,
) -> ProviderFederatedAuthProfile:
    return ProviderFederatedAuthProfile(
        id="profile",
        source_id="provider",
        flow=(
            ProviderFederatedAuthFlow.OIDC_AUTHORIZATION_CODE_PKCE
            if oidc
            else ProviderFederatedAuthFlow.OAUTH2_AUTHORIZATION_CODE_PKCE
        ),
        authorization_url="https://provider.example/oauth/authorize",
        redirect_uri="http://127.0.0.1/oauth/callback",
        client_id="client",
        token_url="https://provider.example/oauth/token",
        scopes=("read", "profile"),
        allowed_transitions=_transitions(),
        review_reference="AUTH-L17",
        reviewed_at=NOW,
        review_expires_at=review_expires_at,
    )


def _material(*, profile_id: str = "profile", nonce: str | None = None):
    return FederatedAuthorizationMaterial(
        profile_id=profile_id,
        state="s" * 48,
        code_verifier="v" * 64,
        nonce=nonce,
    )


def _exchange_response(
    response: httpx.Response,
    *,
    profile: ProviderFederatedAuthProfile | None = None,
    material: FederatedAuthorizationMaterial | None = None,
    now: datetime = NOW,
):
    with httpx.Client(transport=httpx.MockTransport(lambda _request: response)) as client:
        return exchange_federated_authorization_code(
            _entry(),
            profile or _profile(),
            FederatedAuthorizationCode("code"),
            material or _material(),
            purpose=PURPOSE,
            now=now,
            client=client,
        )


@pytest.mark.parametrize(
    ("factory", "match"),
    [
        (lambda: FederatedTokenMaterial(access_token=""), "access_token"),
        (
            lambda: FederatedTokenMaterial(access_token="opaque", token_type="Basic"),
            "token_type",
        ),
        (
            lambda: FederatedTokenMaterial(
                access_token="opaque",
                scopes=("read", "read"),
            ),
            "scopes",
        ),
        (
            lambda: FederatedTokenMaterial(access_token="opaque", expires_in=0),
            "expires_in",
        ),
        (
            lambda: FederatedTokenMaterial(access_token="opaque", refresh_token=""),
            "refresh_token",
        ),
        (
            lambda: FederatedTokenMaterial(access_token="opaque", id_token="bad\x00id"),
            "id_token",
        ),
    ],
)
def test_token_material_invariants_fail_closed(
    factory: Callable[[], FederatedTokenMaterial],
    match: str,
) -> None:
    with pytest.raises(ValueError, match=match):
        factory()


def test_exchange_rejects_binding_expiry_incomplete_and_transition_before_network() -> None:
    def forbidden(request: httpx.Request) -> httpx.Response:
        raise AssertionError(f"unexpected network request: {request.url}")

    cases: list[
        tuple[ProviderFederatedAuthProfile, FederatedAuthorizationMaterial, datetime, str]
    ] = []
    cases.append((_profile(), _material(profile_id="other"), NOW, "binding_mismatch"))
    expiring = _profile(review_expires_at=NOW + timedelta(seconds=1))
    cases.append((expiring, _material(), NOW + timedelta(seconds=2), "not_executable"))

    incomplete = _profile()
    object.__setattr__(incomplete, "token_url", None)
    cases.append((incomplete, _material(), NOW, "profile_incomplete"))

    denied = _profile()
    object.__setattr__(denied, "allowed_transitions", denied.allowed_transitions[:1])
    cases.append((denied, _material(), NOW, "transition_denied"))

    with httpx.Client(transport=httpx.MockTransport(forbidden)) as client:
        for profile, material, current, match in cases:
            with pytest.raises(FederatedTokenExchangeError, match=match):
                exchange_federated_authorization_code(
                    _entry(),
                    profile,
                    FederatedAuthorizationCode("code"),
                    material,
                    purpose=PURPOSE,
                    now=current,
                    client=client,
                )


def test_exchange_rejects_oversize_and_invalid_json_shapes() -> None:
    oversize = httpx.Response(
        200,
        headers={"Content-Type": "application/json"},
        content=b"x" * 1_048_577,
    )
    with pytest.raises(FederatedTokenExchangeError, match="response_too_large"):
        _exchange_response(oversize)

    invalid_json = httpx.Response(
        200,
        headers={"Content-Type": "application/json"},
        content=b"{",
    )
    with pytest.raises(FederatedTokenExchangeError, match="json_invalid"):
        _exchange_response(invalid_json)

    wrong_shape = httpx.Response(
        200,
        headers={"Content-Type": "application/json"},
        json=["not", "a", "mapping"],
    )
    with pytest.raises(FederatedTokenExchangeError, match="shape_invalid"):
        _exchange_response(wrong_shape)


@pytest.mark.parametrize(
    ("payload", "match"),
    [
        ({"access_token": 1}, "required_fields_invalid"),
        ({"access_token": "x", "token_type": 1}, "required_fields_invalid"),
        ({"access_token": "x", "refresh_token": 1}, "refresh_token_invalid"),
        ({"access_token": "x", "id_token": 1}, "id_token_invalid"),
        ({"access_token": "x", "expires_in": True}, "expires_in_invalid"),
        ({"access_token": "x", "scope": ["read"]}, "scope_invalid"),
        ({"access_token": "x", "scope": ""}, "scope_escalation"),
    ],
)
def test_exchange_rejects_malformed_token_fields(
    payload: dict[str, object],
    match: str,
) -> None:
    response = httpx.Response(
        200,
        headers={"Content-Type": "application/json"},
        json=payload,
    )
    with pytest.raises(FederatedTokenExchangeError, match=match):
        _exchange_response(response)


def test_exchange_uses_profile_scopes_when_provider_omits_scope() -> None:
    token = _exchange_response(
        httpx.Response(
            200,
            headers={"Content-Type": "application/json"},
            json={"access_token": "opaque", "token_type": "Bearer"},
        )
    )
    assert token.scopes == ("read", "profile")


def test_oidc_missing_nonce_or_id_token_fails_closed() -> None:
    response = httpx.Response(
        200,
        headers={"Content-Type": "application/json"},
        json={"access_token": "opaque", "id_token": "signed"},
    )
    with pytest.raises(FederatedTokenExchangeError, match="required_material_missing"):
        _exchange_response(response, profile=_profile(oidc=True), material=_material())

    response = httpx.Response(
        200,
        headers={"Content-Type": "application/json"},
        json={"access_token": "opaque"},
    )
    with pytest.raises(FederatedTokenExchangeError, match="required_material_missing"):
        _exchange_response(
            response,
            profile=_profile(oidc=True),
            material=_material(nonce="n" * 48),
        )
