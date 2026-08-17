from __future__ import annotations

import base64
import json
import secrets
from collections.abc import Callable
from dataclasses import dataclass, field
from hashlib import sha256
from hmac import compare_digest
from urllib.parse import parse_qs, urlencode, urlsplit, urlunsplit

from cip.modules.provider_onboarding.domain.federated_auth import (
    ProviderFederatedAuthProfile,
)

_RESERVED_AUTH_QUERY = frozenset(
    {
        "response_type",
        "client_id",
        "redirect_uri",
        "scope",
        "state",
        "code_challenge",
        "code_challenge_method",
        "nonce",
    }
)


class FederatedAuthorizationError(RuntimeError):
    pass


class FederatedStateMismatchError(FederatedAuthorizationError):
    pass


class FederatedProviderRejectedError(FederatedAuthorizationError):
    def __init__(self, error_code: str) -> None:
        self.error_code = error_code
        super().__init__(f"federated_provider_rejected:{error_code}")


@dataclass(frozen=True, slots=True)
class FederatedAuthorizationMaterial:
    profile_id: str
    state: str = field(repr=False)
    code_verifier: str = field(repr=False)
    nonce: str | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        if not self.profile_id.strip() or len(self.profile_id) > 100:
            raise ValueError("profile_id is invalid")
        _bounded_secret(self.state, "state", minimum=16, maximum=512)
        _bounded_secret(self.code_verifier, "code_verifier", minimum=43, maximum=128)
        if self.nonce is not None:
            _bounded_secret(self.nonce, "nonce", minimum=16, maximum=512)

    def to_secret_json(self) -> str:
        return json.dumps(
            {
                "version": 1,
                "profile_id": self.profile_id,
                "state": self.state,
                "code_verifier": self.code_verifier,
                "nonce": self.nonce,
            },
            separators=(",", ":"),
            sort_keys=True,
        )

    @classmethod
    def from_secret_json(cls, payload: str) -> FederatedAuthorizationMaterial:
        if len(payload.encode("utf-8")) > 16_384:
            raise ValueError("federated authorization material is too large")
        try:
            value = json.loads(payload)
        except json.JSONDecodeError as exc:
            raise ValueError("invalid federated authorization material") from exc
        if not isinstance(value, dict) or set(value) != {
            "version",
            "profile_id",
            "state",
            "code_verifier",
            "nonce",
        }:
            raise ValueError("invalid federated authorization material shape")
        if value["version"] != 1:
            raise ValueError("unsupported federated authorization material version")
        profile_id = value["profile_id"]
        state = value["state"]
        verifier = value["code_verifier"]
        nonce = value["nonce"]
        if (
            not isinstance(profile_id, str)
            or not isinstance(state, str)
            or not isinstance(verifier, str)
        ):
            raise ValueError("invalid federated authorization material fields")
        if nonce is not None and not isinstance(nonce, str):
            raise ValueError("invalid federated authorization nonce")
        return cls(
            profile_id=profile_id,
            state=state,
            code_verifier=verifier,
            nonce=nonce,
        )


@dataclass(frozen=True, slots=True)
class FederatedAuthorizationStart:
    authorization_url: str = field(repr=False)
    material: FederatedAuthorizationMaterial = field(repr=False)


@dataclass(frozen=True, slots=True)
class FederatedAuthorizationCode:
    code: str = field(repr=False)

    def __post_init__(self) -> None:
        _bounded_secret(self.code, "authorization code", minimum=1, maximum=4096)


def create_federated_authorization(
    profile: ProviderFederatedAuthProfile,
    *,
    token_factory: Callable[[], str] | None = None,
) -> FederatedAuthorizationStart:
    if not profile.requires_pkce:
        raise ValueError("federated authorization-code initiation requires an OAuth/OIDC profile")
    factory = token_factory or (lambda: secrets.token_urlsafe(48))
    state = factory()
    verifier = factory()
    nonce = factory() if profile.requires_nonce else None
    material = FederatedAuthorizationMaterial(
        profile_id=profile.id,
        state=state,
        code_verifier=verifier,
        nonce=nonce,
    )
    return FederatedAuthorizationStart(
        authorization_url=_authorization_url(profile, material),
        material=material,
    )


def validate_federated_callback(
    profile: ProviderFederatedAuthProfile,
    callback_url: str,
    material: FederatedAuthorizationMaterial,
) -> FederatedAuthorizationCode:
    if material.profile_id != profile.id:
        raise FederatedStateMismatchError("federated_profile_binding_mismatch")
    if not profile.callback_matches(callback_url):
        raise FederatedStateMismatchError("federated_redirect_mismatch")
    query = parse_qs(urlsplit(callback_url).query, keep_blank_values=True)
    provider_error = _single_optional(query, "error")
    if provider_error is not None:
        if not provider_error or len(provider_error) > 100:
            raise FederatedProviderRejectedError("invalid_provider_error")
        raise FederatedProviderRejectedError(provider_error)
    returned_state = _single_required(query, "state", maximum=512)
    if not compare_digest(returned_state, material.state):
        raise FederatedStateMismatchError("federated_state_mismatch")
    return FederatedAuthorizationCode(
        _single_required(query, "code", maximum=4096)
    )


def pkce_s256_challenge(verifier: str) -> str:
    _bounded_secret(verifier, "code_verifier", minimum=43, maximum=128)
    digest = sha256(verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


def _authorization_url(
    profile: ProviderFederatedAuthProfile,
    material: FederatedAuthorizationMaterial,
) -> str:
    if profile.client_id is None:
        raise ValueError("OAuth/OIDC profile is missing client_id")
    parsed = urlsplit(profile.authorization_url)
    existing = parse_qs(parsed.query, keep_blank_values=True)
    if _RESERVED_AUTH_QUERY.intersection(existing):
        raise ValueError("authorization URL contains reserved OAuth query parameters")
    query: list[tuple[str, str]] = []
    for key, values in existing.items():
        query.extend((key, value) for value in values)
    query.extend(
        (
            ("response_type", "code"),
            ("client_id", profile.client_id),
            ("redirect_uri", profile.redirect_uri),
            ("scope", " ".join(profile.scopes)),
            ("state", material.state),
            ("code_challenge", pkce_s256_challenge(material.code_verifier)),
            ("code_challenge_method", "S256"),
        )
    )
    if material.nonce is not None:
        query.append(("nonce", material.nonce))
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, urlencode(query), ""))


def _single_required(
    query: dict[str, list[str]],
    key: str,
    *,
    maximum: int,
) -> str:
    values = query.get(key)
    if values is None or len(values) != 1:
        raise FederatedStateMismatchError(f"federated_{key}_missing_or_ambiguous")
    value = values[0]
    if not value or len(value) > maximum:
        raise FederatedStateMismatchError(f"federated_{key}_invalid")
    return value


def _single_optional(query: dict[str, list[str]], key: str) -> str | None:
    values = query.get(key)
    if values is None:
        return None
    if len(values) != 1:
        raise FederatedStateMismatchError(f"federated_{key}_ambiguous")
    return values[0]


def _bounded_secret(value: str, label: str, *, minimum: int, maximum: int) -> None:
    if not minimum <= len(value) <= maximum or value != value.strip() or "\x00" in value:
        raise ValueError(f"{label} has invalid bounds")