from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from urllib.parse import SplitResult, urlsplit

from cip.modules.provider_onboarding.domain.browser_login import (
    ProviderLoginHttpMethod,
    ProviderLoginTransitionRule,
)
from cip.shared.kernel.time import require_aware_utc


class ProviderFederatedAuthFlow(StrEnum):
    OAUTH2_AUTHORIZATION_CODE_PKCE = "oauth2_authorization_code_pkce"
    OIDC_AUTHORIZATION_CODE_PKCE = "oidc_authorization_code_pkce"
    BROWSER_SSO = "browser_sso"


@dataclass(frozen=True, slots=True)
class ProviderFederatedAuthProfile:
    id: str
    source_id: str
    flow: ProviderFederatedAuthFlow
    authorization_url: str
    redirect_uri: str
    allowed_transitions: tuple[ProviderLoginTransitionRule, ...]
    review_reference: str
    reviewed_at: datetime
    client_id: str | None = None
    token_url: str | None = None
    scopes: tuple[str, ...] = ()
    review_expires_at: datetime | None = None
    max_requests: int = 64
    max_redirects: int = 8
    timeout_ms: int = 30_000
    material_ttl_seconds: int = 3_600

    def __post_init__(self) -> None:
        _bounded_required(self.id, "profile id", 100)
        _bounded_required(self.source_id, "source id", 64)
        _url(self.authorization_url, "authorization_url")
        _redirect_uri(self.redirect_uri)
        _bounded_required(self.review_reference, "review_reference", 500)
        reviewed = require_aware_utc(self.reviewed_at, field_name="reviewed_at")
        object.__setattr__(self, "reviewed_at", reviewed)
        if self.review_expires_at is not None:
            expiry = require_aware_utc(
                self.review_expires_at,
                field_name="review_expires_at",
            )
            if expiry <= reviewed:
                raise ValueError("federated auth review expiry must follow review time")
            object.__setattr__(self, "review_expires_at", expiry)
        if not self.allowed_transitions or len(self.allowed_transitions) > 32:
            raise ValueError("federated auth transitions must be between 1 and 32")
        if len(self.scopes) > 32 or len(set(self.scopes)) != len(self.scopes):
            raise ValueError("federated auth scopes must be unique and limited to 32")
        for scope in self.scopes:
            _bounded_required(scope, "scope", 200)
            if any(char.isspace() for char in scope):
                raise ValueError("federated auth scope cannot contain whitespace")
        if not 1 <= self.max_requests <= 256:
            raise ValueError("federated auth max_requests must be between 1 and 256")
        if not 0 <= self.max_redirects <= 16:
            raise ValueError("federated auth max_redirects must be between 0 and 16")
        if not 500 <= self.timeout_ms <= 120_000:
            raise ValueError("federated auth timeout_ms must be between 500 and 120000")
        if not 60 <= self.material_ttl_seconds <= 86_400:
            raise ValueError("federated auth material_ttl_seconds must be between 60 and 86400")
        self._validate_flow_contract()
        self._validate_transition_contract()

    @property
    def requires_pkce(self) -> bool:
        return self.flow in {
            ProviderFederatedAuthFlow.OAUTH2_AUTHORIZATION_CODE_PKCE,
            ProviderFederatedAuthFlow.OIDC_AUTHORIZATION_CODE_PKCE,
        }

    @property
    def requires_nonce(self) -> bool:
        return self.flow is ProviderFederatedAuthFlow.OIDC_AUTHORIZATION_CODE_PKCE

    def executable_at(self, now: datetime) -> bool:
        current = require_aware_utc(now, field_name="now")
        return self.review_expires_at is None or self.review_expires_at > current

    def allows(self, url: str, method: ProviderLoginHttpMethod) -> bool:
        parsed = urlsplit(url)
        host = (parsed.hostname or "").lower()
        path = parsed.path or "/"
        return any(
            rule.host == host
            and _path_matches(path, rule.path_prefix)
            and method in rule.methods
            for rule in self.allowed_transitions
        )

    def callback_matches(self, url: str) -> bool:
        actual = urlsplit(url)
        expected = urlsplit(self.redirect_uri)
        return (
            actual.scheme.lower() == expected.scheme.lower()
            and (actual.hostname or "").lower() == (expected.hostname or "").lower()
            and _effective_port(actual) == _effective_port(expected)
            and (actual.path or "/") == (expected.path or "/")
            and not actual.username
            and not actual.password
            and not actual.fragment
        )

    def _validate_flow_contract(self) -> None:
        if self.requires_pkce:
            if self.client_id is None:
                raise ValueError("OAuth/OIDC profile requires client_id")
            _bounded_required(self.client_id, "client_id", 500)
            if self.token_url is None:
                raise ValueError("OAuth/OIDC profile requires token_url")
            _url(self.token_url, "token_url")
            if not self.scopes:
                raise ValueError("OAuth/OIDC profile requires at least one scope")
            return
        if self.client_id is not None or self.token_url is not None or self.scopes:
            raise ValueError("browser SSO profile cannot define OAuth token/client/scope fields")

    def _validate_transition_contract(self) -> None:
        if not self.allows(self.authorization_url, ProviderLoginHttpMethod.GET):
            raise ValueError("authorization URL is outside reviewed transitions")
        if not self.allows(self.redirect_uri, ProviderLoginHttpMethod.GET):
            raise ValueError("redirect URI is outside reviewed transitions")
        if self.token_url is not None and not self.allows(
            self.token_url,
            ProviderLoginHttpMethod.POST,
        ):
            raise ValueError("token URL is outside reviewed POST transitions")


def _redirect_uri(value: str) -> None:
    _url(value, "redirect_uri")
    parsed = urlsplit(value)
    if parsed.query:
        raise ValueError("redirect_uri cannot contain a query")
    if parsed.scheme == "http" and (parsed.hostname or "").lower() not in {
        "127.0.0.1",
        "localhost",
        "::1",
    }:
        raise ValueError("non-loopback redirect_uri must use HTTPS")


def _url(value: str, field_name: str) -> None:
    parsed = urlsplit(value.strip())
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError(f"{field_name} must be an absolute HTTP(S) URL")
    if parsed.username or parsed.password or parsed.fragment:
        raise ValueError(f"{field_name} cannot contain user info or fragment")
    if len(value) > 2000:
        raise ValueError(f"{field_name} cannot exceed 2000 characters")


def _path_matches(path: str, prefix: str) -> bool:
    normalized = prefix.rstrip("/") or "/"
    if normalized == "/":
        return True
    return path == normalized or path.startswith(f"{normalized}/")


def _effective_port(parsed: SplitResult) -> int | None:
    if parsed.port is not None:
        return parsed.port
    if parsed.scheme.lower() == "https":
        return 443
    if parsed.scheme.lower() == "http":
        return 80
    return None


def _bounded_required(value: str, field_name: str, maximum: int) -> None:
    normalized = value.strip()
    if not normalized or len(normalized) > maximum or "\x00" in normalized:
        raise ValueError(f"{field_name} is invalid")
