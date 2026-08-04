from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from cip.modules.provider_onboarding.domain.models import (
    AuthMode,
    HumanAction,
    OnboardingState,
    ProviderOnboarding,
)


class ProviderOnboardingResponse(BaseModel):
    source_id: str
    display_name: str
    auth_mode: AuthMode
    state: OnboardingState
    documentation_url: str
    signup_url: str | None
    console_url: str | None
    required_secret_names: list[str]
    missing_secret_names: list[str]
    human_actions: list[HumanAction]
    automatic_onboarding: bool
    secret_references: dict[str, str]
    blocked_reason: str | None
    last_verified_at: datetime | None
    expires_at: datetime | None
    last_error_code: str | None
    last_error_message: str | None
    updated_at: datetime | None

    @classmethod
    def from_domain(cls, value: ProviderOnboarding) -> ProviderOnboardingResponse:
        return cls(
            source_id=value.source_id,
            display_name=value.display_name,
            auth_mode=value.auth_mode,
            state=value.state,
            documentation_url=value.documentation_url,
            signup_url=value.signup_url,
            console_url=value.console_url,
            required_secret_names=list(value.required_secret_names),
            missing_secret_names=list(value.missing_secret_names),
            human_actions=list(value.human_actions),
            automatic_onboarding=value.automatic_onboarding,
            secret_references={
                name: reference.redacted
                for name, reference in value.secret_references.items()
            },
            blocked_reason=value.blocked_reason,
            last_verified_at=value.last_verified_at,
            expires_at=value.expires_at,
            last_error_code=value.last_error_code,
            last_error_message=value.last_error_message,
            updated_at=value.updated_at,
        )


class ProviderOnboardingPageResponse(BaseModel):
    items: list[ProviderOnboardingResponse]
    total: int


class ActorRequest(BaseModel):
    actor: str = Field(min_length=1, max_length=200)


class HumanCheckpointRequest(ActorRequest):
    state: OnboardingState
    note: str | None = Field(default=None, max_length=1_000)


class SecretReferenceRequest(ActorRequest):
    name: str = Field(min_length=1, max_length=100)
    reference: str = Field(min_length=1, max_length=500)
