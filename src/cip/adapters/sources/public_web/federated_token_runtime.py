from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol

import httpx

from cip.adapters.sources.public_web.collection_policy import authorize_public_web_url
from cip.modules.provider_onboarding.application.federated_authorization import (
    FederatedAuthorizationCode,
    FederatedAuthorizationMaterial,
)
from cip.modules.provider_onboarding.domain.browser_login import ProviderLoginHttpMethod
from cip.modules.provider_onboarding.domain.federated_auth import (
    ProviderFederatedAuthProfile,
)
from cip.modules.source_governance.domain.models import HttpMethod
from cip.modules.source_governance.infrastructure.registry import SourceRegistryEntry
from cip.shared.kernel.time import require_aware_utc

_MAX_TOKEN_RESPONSE_BYTES = 1_048_576


class FederatedTokenExchangeError(RuntimeError):
    pass


class FederatedTokenExchangeUncertainError(FederatedTokenExchangeError):
    pass


class OidcIdTokenVerifier(Protocol):
    def verify(self, id_token: str, *, expected_nonce: str, client_id: str) -> None: ...


@dataclass(frozen=True, slots=True)
class FederatedTokenMaterial:
    access_token: str = field(repr=False)
    token_type: str = "Bearer"
    scopes: tuple[str, ...] = ()
    expires_in: int | None = None
    refresh_token: str | None = field(default=None, repr=False)
    id_token: str | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        _token(self.access_token, "access_token")
        if self.token_type.lower() != "bearer":
            raise ValueError("unsupported federated token_type")
        if len(self.scopes) > 32 or len(set(self.scopes)) != len(self.scopes):
            raise ValueError("federated token scopes are invalid")
        if self.expires_in is not None and not 0 < self.expires_in <= 31_536_000:
            raise ValueError("federated token expires_in is invalid")
        if self.refresh_token is not None:
            _token(self.refresh_token, "refresh_token")
        if self.id_token is not None:
            _token(self.id_token, "id_token", maximum=131_072)

    def to_secret_json(self) -> str:
        return json.dumps(
            {
                "version": 1,
                "access_token": self.access_token,
                "token_type": self.token_type,
                "scopes": list(self.scopes),
                "expires_in": self.expires_in,
                "refresh_token": self.refresh_token,
                "id_token": self.id_token,
            },
            separators=(",", ":"),
            sort_keys=True,
        )


def exchange_federated_authorization_code(
    entry: SourceRegistryEntry,
    profile: ProviderFederatedAuthProfile,
    code: FederatedAuthorizationCode,
    material: FederatedAuthorizationMaterial,
    *,
    purpose: str,
    now: datetime,
    client: httpx.Client,
    oidc_verifier: OidcIdTokenVerifier | None = None,
) -> FederatedTokenMaterial:
    current = require_aware_utc(now, field_name="now")
    _validate_exchange(entry, profile, material, purpose=purpose, now=current)
    assert profile.token_url is not None
    assert profile.client_id is not None
    try:
        response = client.post(
            profile.token_url,
            data={
                "grant_type": "authorization_code",
                "code": code.code,
                "redirect_uri": profile.redirect_uri,
                "client_id": profile.client_id,
                "code_verifier": material.code_verifier,
            },
            headers={"Accept": "application/json"},
            follow_redirects=False,
            timeout=profile.timeout_ms / 1000,
        )
    except httpx.TransportError as exc:
        raise FederatedTokenExchangeUncertainError("federated_token_exchange_uncertain") from exc
    if 300 <= response.status_code < 400:
        raise FederatedTokenExchangeError("federated_token_redirect_denied")
    if response.status_code >= 400:
        raise FederatedTokenExchangeError(f"federated_token_provider_status:{response.status_code}")
    if len(response.content) > _MAX_TOKEN_RESPONSE_BYTES:
        raise FederatedTokenExchangeError("federated_token_response_too_large")
    content_type = response.headers.get("content-type", "").split(";", 1)[0].strip().lower()
    if content_type != "application/json":
        raise FederatedTokenExchangeError("federated_token_content_type_invalid")
    token = _parse_token_response(response, profile)
    _verify_oidc(profile, material, token, oidc_verifier)
    return token


def _validate_exchange(
    entry: SourceRegistryEntry,
    profile: ProviderFederatedAuthProfile,
    material: FederatedAuthorizationMaterial,
    *,
    purpose: str,
    now: datetime,
) -> None:
    if profile.source_id != entry.policy.id or material.profile_id != profile.id:
        raise FederatedTokenExchangeError("federated_token_binding_mismatch")
    if not profile.requires_pkce or not profile.executable_at(now):
        raise FederatedTokenExchangeError("federated_token_profile_not_executable")
    if profile.token_url is None or profile.client_id is None:
        raise FederatedTokenExchangeError("federated_token_profile_incomplete")
    if not profile.allows(profile.token_url, ProviderLoginHttpMethod.POST):
        raise FederatedTokenExchangeError("federated_token_transition_denied")
    authorize_public_web_url(
        entry,
        profile.token_url,
        now=now,
        http_method=HttpMethod.POST,
        purpose=purpose,
    )


def _parse_token_response(
    response: httpx.Response,
    profile: ProviderFederatedAuthProfile,
) -> FederatedTokenMaterial:
    try:
        payload = response.json()
    except ValueError as exc:
        raise FederatedTokenExchangeError("federated_token_json_invalid") from exc
    if not isinstance(payload, dict):
        raise FederatedTokenExchangeError("federated_token_shape_invalid")
    access_token = payload.get("access_token")
    token_type = payload.get("token_type", "Bearer")
    refresh_token = payload.get("refresh_token")
    id_token = payload.get("id_token")
    expires_in = payload.get("expires_in")
    if not isinstance(access_token, str) or not isinstance(token_type, str):
        raise FederatedTokenExchangeError("federated_token_required_fields_invalid")
    for value, name in ((refresh_token, "refresh_token"), (id_token, "id_token")):
        if value is not None and not isinstance(value, str):
            raise FederatedTokenExchangeError(f"federated_token_{name}_invalid")
    if expires_in is not None and (not isinstance(expires_in, int) or isinstance(expires_in, bool)):
        raise FederatedTokenExchangeError("federated_token_expires_in_invalid")
    scopes = _response_scopes(payload.get("scope"), profile)
    return FederatedTokenMaterial(
        access_token=access_token,
        token_type=token_type,
        scopes=scopes,
        expires_in=expires_in,
        refresh_token=refresh_token,
        id_token=id_token,
    )


def _response_scopes(value: object, profile: ProviderFederatedAuthProfile) -> tuple[str, ...]:
    if value is None:
        return profile.scopes
    if not isinstance(value, str):
        raise FederatedTokenExchangeError("federated_token_scope_invalid")
    scopes = tuple(part for part in value.split(" ") if part)
    if not scopes or not set(scopes).issubset(profile.scopes):
        raise FederatedTokenExchangeError("federated_token_scope_escalation")
    return scopes


def _verify_oidc(
    profile: ProviderFederatedAuthProfile,
    material: FederatedAuthorizationMaterial,
    token: FederatedTokenMaterial,
    verifier: OidcIdTokenVerifier | None,
) -> None:
    if not profile.requires_nonce:
        return
    if material.nonce is None or token.id_token is None or profile.client_id is None:
        raise FederatedTokenExchangeError("oidc_required_material_missing")
    if verifier is None:
        raise FederatedTokenExchangeError("oidc_verifier_not_configured")
    verifier.verify(token.id_token, expected_nonce=material.nonce, client_id=profile.client_id)


def _token(value: str, label: str, *, maximum: int = 16_384) -> None:
    if not value or len(value) > maximum or "\x00" in value:
        raise ValueError(f"{label} is invalid")
