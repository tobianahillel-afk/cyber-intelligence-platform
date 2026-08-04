from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime
from enum import StrEnum
from urllib.parse import urlsplit

from cip.shared.kernel.time import require_aware_utc


class AuthMode(StrEnum):
    NONE = "none"
    API_KEY = "api_key"
    OAUTH2_CLIENT_CREDENTIALS = "oauth2_client_credentials"
    BASIC = "basic"
    SFTP_KEY = "sftp_key"
    MANUAL = "manual"


class OnboardingState(StrEnum):
    NOT_REQUIRED = "not_required"
    NOT_CONFIGURED = "not_configured"
    AWAITING_USER_ACTION = "awaiting_user_action"
    AWAITING_EMAIL_VERIFICATION = "awaiting_email_verification"
    AWAITING_MFA = "awaiting_mfa"
    AWAITING_PROVIDER_APPROVAL = "awaiting_provider_approval"
    READY_TO_VERIFY = "ready_to_verify"
    CONNECTED = "connected"
    FAILED = "failed"
    REVOKED = "revoked"
    BLOCKED = "blocked"


class HumanAction(StrEnum):
    OPEN_OFFICIAL_SIGNUP = "open_official_signup"
    SIGN_IN = "sign_in"
    VERIFY_EMAIL = "verify_email"
    COMPLETE_MFA = "complete_mfa"
    ACCEPT_PROVIDER_TERMS = "accept_provider_terms"
    REQUEST_PROVIDER_ACCESS = "request_provider_access"
    WAIT_FOR_PROVIDER_APPROVAL = "wait_for_provider_approval"
    RETRIEVE_TECHNICAL_CREDENTIALS = "retrieve_technical_credentials"
    REGISTER_SECRET_REFERENCE = "register_secret_reference"
    ENABLE_SOURCE_POLICY = "enable_source_policy"


class SecretReferenceScheme(StrEnum):
    ENV = "env"
    VAULT = "vault"
    FILE_SECRET = "file-secret"


@dataclass(frozen=True, slots=True)
class SecretReference:
    value: str

    def __post_init__(self) -> None:
        normalized = self.value.strip()
        parsed = urlsplit(normalized)
        try:
            scheme = SecretReferenceScheme(parsed.scheme)
        except ValueError as exc:
            raise ValueError("secret reference scheme is not allowed") from exc
        if parsed.query or parsed.fragment or parsed.username or parsed.password:
            raise ValueError("secret references cannot contain query, fragment, or user info")
        target = _reference_target(parsed.netloc, parsed.path)
        if scheme is SecretReferenceScheme.ENV:
            if not target.startswith("CIP_") or not target.replace("_", "").isalnum():
                raise ValueError("env secret references must target a CIP_* variable")
        elif scheme is SecretReferenceScheme.FILE_SECRET:
            if not target.startswith("/run/secrets/") or ".." in target.split("/"):
                raise ValueError("file-secret references must stay under /run/secrets")
        elif not target:
            raise ValueError("vault secret references require a non-empty target")
        if len(normalized) > 500:
            raise ValueError("secret reference cannot exceed 500 characters")
        object.__setattr__(self, "value", normalized)

    @property
    def scheme(self) -> SecretReferenceScheme:
        return SecretReferenceScheme(urlsplit(self.value).scheme)

    @property
    def target(self) -> str:
        parsed = urlsplit(self.value)
        return _reference_target(parsed.netloc, parsed.path)

    @property
    def redacted(self) -> str:
        return f"{self.scheme.value}://***"


@dataclass(frozen=True, slots=True)
class ProviderProfile:
    source_id: str
    display_name: str
    auth_mode: AuthMode
    documentation_url: str
    signup_url: str | None = None
    console_url: str | None = None
    required_secret_names: tuple[str, ...] = ()
    human_actions: tuple[HumanAction, ...] = ()
    automatic_onboarding: bool = False
    blocked_reason: str | None = None

    def __post_init__(self) -> None:
        _required_text(self.source_id, "source_id", maximum=64)
        _required_text(self.display_name, "display_name", maximum=200)
        _https_url(self.documentation_url, "documentation_url")
        if self.signup_url is not None:
            _https_url(self.signup_url, "signup_url")
        if self.console_url is not None:
            _https_url(self.console_url, "console_url")
        names = tuple(dict.fromkeys(name.strip() for name in self.required_secret_names))
        if any(not name or len(name) > 100 for name in names):
            raise ValueError("required secret names must be non-empty and bounded")
        if self.auth_mode is AuthMode.NONE and names:
            raise ValueError("no-auth providers cannot require secrets")
        if self.auth_mode is not AuthMode.NONE and not names and self.auth_mode is not AuthMode.MANUAL:
            raise ValueError("authenticated providers require at least one secret name")
        if self.blocked_reason and self.automatic_onboarding:
            raise ValueError("blocked providers cannot support automatic onboarding")
        object.__setattr__(self, "required_secret_names", names)

    @property
    def initial_state(self) -> OnboardingState:
        if self.blocked_reason:
            return OnboardingState.BLOCKED
        if self.auth_mode is AuthMode.NONE and self.automatic_onboarding:
            return OnboardingState.CONNECTED
        if self.auth_mode is AuthMode.NONE:
            return OnboardingState.NOT_REQUIRED
        return OnboardingState.NOT_CONFIGURED


@dataclass(frozen=True, slots=True)
class ProviderOnboarding:
    source_id: str
    auth_mode: AuthMode
    state: OnboardingState
    documentation_url: str
    signup_url: str | None
    console_url: str | None
    required_secret_names: tuple[str, ...]
    human_actions: tuple[HumanAction, ...]
    automatic_onboarding: bool
    secret_references: dict[str, SecretReference] = field(default_factory=dict)
    blocked_reason: str | None = None
    last_verified_at: datetime | None = None
    expires_at: datetime | None = None
    last_error_code: str | None = None
    last_error_message: str | None = None
    updated_at: datetime | None = None

    def __post_init__(self) -> None:
        if self.last_verified_at is not None:
            object.__setattr__(
                self,
                "last_verified_at",
                require_aware_utc(self.last_verified_at, field_name="last_verified_at"),
            )
        if self.expires_at is not None:
            object.__setattr__(
                self,
                "expires_at",
                require_aware_utc(self.expires_at, field_name="expires_at"),
            )
        if self.updated_at is not None:
            object.__setattr__(
                self,
                "updated_at",
                require_aware_utc(self.updated_at, field_name="updated_at"),
            )
        if set(self.secret_references) - set(self.required_secret_names):
            raise ValueError("unexpected secret reference name")

    @property
    def missing_secret_names(self) -> tuple[str, ...]:
        return tuple(
            name for name in self.required_secret_names if name not in self.secret_references
        )

    def with_secret_reference(
        self,
        name: str,
        reference: SecretReference,
    ) -> ProviderOnboarding:
        normalized_name = name.strip()
        if normalized_name not in self.required_secret_names:
            raise ValueError("secret name is not required by this provider")
        references = dict(self.secret_references)
        references[normalized_name] = reference
        state = (
            OnboardingState.READY_TO_VERIFY
            if set(references) == set(self.required_secret_names)
            else OnboardingState.AWAITING_USER_ACTION
        )
        return replace(
            self,
            secret_references=references,
            state=state,
            last_error_code=None,
            last_error_message=None,
        )


def _reference_target(netloc: str, path: str) -> str:
    if netloc and path:
        return f"{netloc}{path}"
    return netloc or path


def _required_text(value: str, field_name: str, *, maximum: int) -> None:
    if not value.strip():
        raise ValueError(f"{field_name} is required")
    if len(value.strip()) > maximum:
        raise ValueError(f"{field_name} cannot exceed {maximum} characters")


def _https_url(value: str, field_name: str) -> None:
    parsed = urlsplit(value)
    if parsed.scheme != "https" or not parsed.hostname:
        raise ValueError(f"{field_name} must be an absolute HTTPS URL")
