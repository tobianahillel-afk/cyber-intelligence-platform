from __future__ import annotations

from sqlalchemy.orm import Session

from cip.modules.provider_onboarding.application.service import sync_provider_profiles
from cip.modules.provider_onboarding.infrastructure.registry import load_provider_profiles
from cip.modules.source_governance.infrastructure.persistence import sync_source_registry
from cip.modules.source_governance.infrastructure.registry_bundle import (
    load_source_registry_bundle,
)
from cip.shared.config.settings import Settings
from cip.shared.kernel.time import utc_now


def ensure_provider_catalog(session: Session, settings: Settings) -> None:
    source_entries = load_source_registry_bundle(
        settings.source_registry_path,
        settings.identity_source_registry_path,
    )
    sync_source_registry(session, source_entries)
    session.flush()
    profiles = load_provider_profiles(settings.provider_onboarding_registry_path)
    sync_provider_profiles(session, profiles, now=utc_now())
