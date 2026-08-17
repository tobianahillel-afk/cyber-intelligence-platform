from __future__ import annotations

from datetime import UTC, datetime

import httpx
import pytest

from cip.adapters.sources.public_web.federated_token_runtime import (
    FederatedTokenExchangeError,
    FederatedTokenExchangeUncertainError,
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

NOW = datetime(2026, 8, 17, tzinfo=UTC)
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


def _profile(*, oidc: bool = False) -> ProviderFederatedAuthProfile:
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


def _material(*, oidc: bool = False) -> FederatedAuthorizationMaterial:
    return FederatedAuthorizationMaterial(
        profile_id="profile",
        state="s" * 48,
        code_verifier="v" * 64,
        nonce="n" * 48 if oidc else None,
    )


def _exchange(
    transport: httpx.BaseTransport,
    *,
    oidc: bool = False,
    verifier=None,
):
    with httpx.Client(transport=transport) as client:
        return exchange_federated_authorization_code(
            _entry(),
            _profile(oidc=oidc),
            FederatedAuthorizationCode("authorization-code"),
            _material(oidc=oidc),
            purpose=PURPOSE,
            now=NOW,
            client=client,
            oidc_verifier=verifier,
        )


def test_token_exchange_uses_exact_post_and_keeps_tokens_out_of_repr() -> None:
    captured: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["method"] = request.method
        captured["url"] = str(request.url)
        captured["body"] = request.content.decode("utf-8")
        return httpx.Response(
            200,
            headers={"Content-Type": "application/json"},
            json={
                "access_token": "opaque-access",
                "token_type": "Bearer",
                "scope": "read profile",
                "expires_in": 3600,
                "refresh_token": "opaque-refresh",
            },
        )

    token = _exchange(httpx.MockTransport(handler))

    assert captured["method"] == "POST"
    assert captured["url"] == "https://provider.example/oauth/token"
    assert "code=authorization-code" in captured["body"]
    assert "code_verifier=" + "v" * 64 in captured["body"]
    assert token.scopes == ("read", "profile")
    assert "opaque-access" not in repr(token)
    assert "opaque-refresh" not in repr(token)


def test_token_exchange_rejects_redirect_status_body_and_scope_escalation() -> None:
    cases = (
        (httpx.Response(302, headers={"Location": "https://evil.example/"}), "redirect_denied"),
        (httpx.Response(401, text="private provider body"), "provider_status:401"),
        (httpx.Response(200, headers={"Content-Type": "text/html"}, text="no"), "content_type_invalid"),
        (
            httpx.Response(
                200,
                headers={"Content-Type": "application/json"},
                json={"access_token": "opaque", "token_type": "Bearer", "scope": "admin"},
            ),
            "scope_escalation",
        ),
    )
    for response, match in cases:
        with pytest.raises(FederatedTokenExchangeError, match=match):
            _exchange(httpx.MockTransport(lambda _request, result=response: result))


def test_transport_failure_is_uncertain_and_not_automatically_retried() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection lost", request=request)

    with pytest.raises(FederatedTokenExchangeUncertainError, match="uncertain"):
        _exchange(httpx.MockTransport(handler))


def test_oidc_requires_injected_signature_nonce_verifier() -> None:
    response = httpx.Response(
        200,
        headers={"Content-Type": "application/json"},
        json={
            "access_token": "opaque",
            "token_type": "Bearer",
            "id_token": "signed-id-token",
        },
    )
    with pytest.raises(FederatedTokenExchangeError, match="verifier_not_configured"):
        _exchange(httpx.MockTransport(lambda _request: response), oidc=True)

    class Verifier:
        def __init__(self) -> None:
            self.seen: tuple[str, str, str] | None = None

        def verify(self, id_token: str, *, expected_nonce: str, client_id: str) -> None:
            self.seen = (id_token, expected_nonce, client_id)

    verifier = Verifier()
    token = _exchange(
        httpx.MockTransport(
            lambda _request: httpx.Response(
                200,
                headers={"Content-Type": "application/json"},
                json={
                    "access_token": "opaque",
                    "token_type": "Bearer",
                    "id_token": "signed-id-token",
                },
            )
        ),
        oidc=True,
        verifier=verifier,
    )
    assert token.id_token is not None
    assert verifier.seen == ("signed-id-token", "n" * 48, "client")
