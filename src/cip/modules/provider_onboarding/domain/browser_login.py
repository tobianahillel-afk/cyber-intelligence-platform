from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from urllib.parse import urlsplit

from cip.shared.kernel.time import require_aware_utc


class ProviderLoginHttpMethod(StrEnum):
    GET = "GET"
    POST = "POST"


class ProviderLoginChallenge(StrEnum):
    MFA = "mfa"
    CAPTCHA = "captcha"
    OAUTH = "oauth"
    SSO = "sso"
    IDENTITY_VERIFICATION = "identity_verification"
    LOCKOUT_RISK = "lockout_risk"
    PASSWORD_RESET = "password_reset"
    TERMS_CONFIRMATION = "terms_confirmation"


@dataclass(frozen=True, slots=True)
class ProviderLoginTransitionRule:
    host: str
    path_prefix: str
    methods: frozenset[ProviderLoginHttpMethod]

    def __post_init__(self) -> None:
        host = self.host.strip().lower()
        path = self.path_prefix.strip()
        if not host or len(host) > 253 or any(char.isspace() for char in host):
            raise ValueError("login transition host is invalid")
        if not path.startswith("/") or len(path) > 1000:
            raise ValueError("login transition path prefix is invalid")
        if not self.methods:
            raise ValueError("login transition requires at least one HTTP method")
        object.__setattr__(self, "host", host)
        object.__setattr__(self, "path_prefix", path)


@dataclass(frozen=True, slots=True)
class ProviderLoginChallengeSignal:
    challenge: ProviderLoginChallenge
    selector: str

    def __post_init__(self) -> None:
        _selector(self.selector, "challenge selector")


@dataclass(frozen=True, slots=True)
class ProviderLoginProfile:
    id: str
    source_id: str
    login_url: str
    username_selector: str
    secret_selector: str
    submit_selector: str
    success_selector: str
    authenticated_probe_url: str
    allowed_transitions: tuple[ProviderLoginTransitionRule, ...]
    review_reference: str
    reviewed_at: datetime
    logout_url: str | None = None
    review_expires_at: datetime | None = None
    challenge_signals: tuple[ProviderLoginChallengeSignal, ...] = ()
    max_requests: int = 32
    max_redirects: int = 4
    timeout_ms: int = 15_000
    session_ttl_seconds: int = 3_600

    def __post_init__(self) -> None:
        _bounded_required(self.id, "profile id", 100)
        _bounded_required(self.source_id, "source id", 64)
        _url(self.login_url, "login_url")
        _url(self.authenticated_probe_url, "authenticated_probe_url")
        if self.logout_url is not None:
            _url(self.logout_url, "logout_url")
        _selector(self.username_selector, "username_selector")
        _selector(self.secret_selector, "secret_selector")
        _selector(self.submit_selector, "submit_selector")
        _selector(self.success_selector, "success_selector")
        _bounded_required(self.review_reference, "review_reference", 500)
        reviewed = require_aware_utc(self.reviewed_at, field_name="reviewed_at")
        object.__setattr__(self, "reviewed_at", reviewed)
        if self.review_expires_at is not None:
            expiry = require_aware_utc(
                self.review_expires_at,
                field_name="review_expires_at",
            )
            if expiry <= reviewed:
                raise ValueError("login profile review expiry must follow review time")
            object.__setattr__(self, "review_expires_at", expiry)
        if not self.allowed_transitions or len(self.allowed_transitions) > 32:
            raise ValueError("login profile transition rules must be between 1 and 32")
        if len(self.challenge_signals) > 32:
            raise ValueError("login profile challenge signals cannot exceed 32")
        if len({signal.challenge for signal in self.challenge_signals}) != len(
            self.challenge_signals
        ):
            raise ValueError("login profile challenge kinds must be unique")
        if not 1 <= self.max_requests <= 256:
            raise ValueError("login max_requests must be between 1 and 256")
        if not 0 <= self.max_redirects <= 10:
            raise ValueError("login max_redirects must be between 0 and 10")
        if not 500 <= self.timeout_ms <= 120_000:
            raise ValueError("login timeout_ms must be between 500 and 120000")
        if not 60 <= self.session_ttl_seconds <= 86_400:
            raise ValueError("session_ttl_seconds must be between 60 and 86400")
        for url in self._profile_urls():
            parsed = urlsplit(url)
            if not any(
                rule.host == (parsed.hostname or "").lower()
                and _path_matches(parsed.path or "/", rule.path_prefix)
                and ProviderLoginHttpMethod.GET in rule.methods
                for rule in self.allowed_transitions
            ):
                raise ValueError("profile URL is outside allowed login transitions")

    def executable_at(self, now: datetime) -> bool:
        current = require_aware_utc(now, field_name="now")
        return self.review_expires_at is None or self.review_expires_at > current

    def allows(
        self,
        url: str,
        method: ProviderLoginHttpMethod,
    ) -> bool:
        parsed = urlsplit(url)
        host = (parsed.hostname or "").lower()
        path = parsed.path or "/"
        return any(
            rule.host == host
            and _path_matches(path, rule.path_prefix)
            and method in rule.methods
            for rule in self.allowed_transitions
        )

    def _profile_urls(self) -> tuple[str, ...]:
        urls = [self.login_url, self.authenticated_probe_url]
        if self.logout_url is not None:
            urls.append(self.logout_url)
        return tuple(urls)


def _path_matches(path: str, prefix: str) -> bool:
    normalized = prefix.rstrip("/") or "/"
    if normalized == "/":
        return True
    return path == normalized or path.startswith(f"{normalized}/")


def _url(value: str, field_name: str) -> None:
    parsed = urlsplit(value.strip())
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError(f"{field_name} must be an absolute HTTP(S) URL")
    if parsed.username or parsed.password or parsed.fragment:
        raise ValueError(f"{field_name} cannot contain user info or fragment")
    if len(value) > 2000:
        raise ValueError(f"{field_name} cannot exceed 2000 characters")


def _selector(value: str, field_name: str) -> None:
    _bounded_required(value, field_name, 1000)
    if "\x00" in value:
        raise ValueError(f"{field_name} is invalid")


def _bounded_required(value: str, field_name: str, maximum: int) -> None:
    normalized = value.strip()
    if not normalized or len(normalized) > maximum or "\x00" in normalized:
        raise ValueError(f"{field_name} is invalid")
