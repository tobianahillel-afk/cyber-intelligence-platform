from __future__ import annotations

from datetime import UTC, datetime

import pytest

from cip.modules.provider_onboarding.domain.models import (
    AuthMode,
    HumanAction,
    OnboardingState,
    ProviderOnboarding,
    ProviderProfile,
    SecretReference,
    SecretReferenceScheme,
)

NOW = datetime(2026, 8, 4, 18, 0, tzinfo=UTC)


def test_secret_references_accept_only_supported_indirections() -> None:
    environment = SecretReference("env://CIP_INPI_RNE_PASSWORD")
    file_secret = SecretReference("file-secret:///run/secrets/inpi-rne-password")
    vault = SecretReference("vault://secret/data/cip/inpi-rne")

    assert environment.scheme is SecretReferenceScheme.ENV
    assert environment.target == "CIP_INPI_RNE_PASSWORD"
    assert environment.redacted == "env://***"
    assert file_secret.target == "/run/secrets/inpi-rne-password"
    assert vault.redacted == "vault://***"


@pytest.mark.parametrize(
    "value",
    (
        "plain-secret-value",
        "https://example.test/secret",
        "env://PASSWORD",
        "env://CIP_KEY?leak=value",
        "file-secret:///tmp/secret",
        "file-secret:///run/secrets/../other",
        "vault://",
    ),
)
def test_secret_references_reject_raw_or_unsafe_values(value: str) -> None:
    with pytest.raises(ValueError):
        SecretReference(value)


def test_provider_profile_initial_state_is_safe() -> None:
    public = _profile(AuthMode.NONE, automatic=True)
    manual = _profile(AuthMode.MANUAL)
    blocked = _profile(
        AuthMode.MANUAL,
        blocked_reason="Provider is quarantined.",
    )

    assert public.initial_state is OnboardingState.CONNECTED
    assert manual.initial_state is OnboardingState.NOT_CONFIGURED
    assert blocked.initial_state is OnboardingState.BLOCKED


def test_profile_validation_rejects_invalid_auth_contracts() -> None:
    with pytest.raises(ValueError, match="no-auth"):
        _profile(AuthMode.NONE, required=("token",))
    with pytest.raises(ValueError, match="require at least one"):
        _profile(AuthMode.API_KEY)
    with pytest.raises(ValueError, match="blocked"):
        _profile(
            AuthMode.MANUAL,
            automatic=True,
            blocked_reason="blocked",
        )


def test_registering_secret_references_reaches_ready_state() -> None:
    onboarding = ProviderOnboarding(
        source_id="inpi-rne",
        display_name="INPI RNE",
        auth_mode=AuthMode.BASIC,
        state=OnboardingState.AWAITING_USER_ACTION,
        documentation_url="https://data.inpi.fr/documentation",
        signup_url="https://data.inpi.fr/",
        console_url="https://data.inpi.fr/",
        required_secret_names=("username", "password"),
        human_actions=(HumanAction.REGISTER_SECRET_REFERENCE,),
        automatic_onboarding=False,
        updated_at=NOW,
    )

    username = onboarding.with_secret_reference(
        "username",
        SecretReference("env://CIP_INPI_RNE_USERNAME"),
    )
    complete = username.with_secret_reference(
        "password",
        SecretReference("env://CIP_INPI_RNE_PASSWORD"),
    )

    assert username.state is OnboardingState.AWAITING_USER_ACTION
    assert username.missing_secret_names == ("password",)
    assert complete.state is OnboardingState.READY_TO_VERIFY
    assert complete.missing_secret_names == ()
    with pytest.raises(ValueError, match="not required"):
        complete.with_secret_reference("token", SecretReference("env://CIP_TOKEN"))


def _profile(
    auth_mode: AuthMode,
    *,
    automatic: bool = False,
    required: tuple[str, ...] = (),
    blocked_reason: str | None = None,
) -> ProviderProfile:
    return ProviderProfile(
        source_id="provider",
        display_name="Provider",
        auth_mode=auth_mode,
        documentation_url="https://provider.example/docs",
        required_secret_names=required,
        human_actions=(HumanAction.OPEN_OFFICIAL_SIGNUP,),
        automatic_onboarding=automatic,
        blocked_reason=blocked_reason,
    )
