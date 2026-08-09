from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from cip.modules.provider_onboarding.application.secrets import SecretValueResolver
from cip.modules.provider_onboarding.application.service import (
    ProviderOnboardingNotFoundError,
    get_provider_onboarding,
)
from cip.modules.provider_onboarding.domain.models import OnboardingState
from cip.shared.kernel.time import require_aware_utc


def resolve_connected_provider_secret(
    session: Session,
    source_id: str,
    secret_name: str,
    *,
    resolver: SecretValueResolver,
    now: datetime,
) -> str | None:
    current = require_aware_utc(now, field_name="now")
    try:
        onboarding = get_provider_onboarding(session, source_id)
    except ProviderOnboardingNotFoundError:
        return None
    if onboarding.state is not OnboardingState.CONNECTED:
        return None
    if onboarding.expires_at is not None and onboarding.expires_at <= current:
        return None
    reference = onboarding.secret_references.get(secret_name)
    if reference is None:
        return None
    try:
        return resolver.resolve(reference)
    except RuntimeError:
        return None
