from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from cip.adapters.sources.public_web.delegated_login_executor import (
    PublicWebDelegatedLoginExecutor,
)
from cip.modules.provider_onboarding.application.secrets import (
    SecretReferenceResolver,
    SecretValueResolver,
)
from cip.modules.provider_onboarding.domain.browser_login import ProviderLoginProfile
from cip.modules.source_governance.application import (
    delegated_provider_session_service as session_service,
)
from cip.modules.source_governance.application.session_material import SessionMaterialStore
from cip.modules.source_governance.domain.delegated_browser_identity import (
    DelegatedExecutionRequest,
)
from cip.modules.source_governance.infrastructure.registry import SourceRegistryEntry

DelegatedAuthenticatedPage = session_service.DelegatedAuthenticatedPage
DelegatedLoginOrchestrationError = session_service.DelegatedProviderSessionError
DelegatedSessionRevocationResult = session_service.DelegatedSessionRevocationResult


def establish_delegated_provider_session(
    session: Any,
    identity_id: UUID,
    request: DelegatedExecutionRequest,
    entry: SourceRegistryEntry,
    profile: ProviderLoginProfile,
    *,
    secret_reference_resolver: SecretReferenceResolver,
    secret_value_resolver: SecretValueResolver,
    session_store: SessionMaterialStore,
    now: datetime,
) -> session_service.DelegatedAuthenticatedPage:
    return session_service.establish_delegated_provider_session(
        session,
        identity_id,
        request,
        PublicWebDelegatedLoginExecutor(entry, profile),
        secret_reference_resolver=secret_reference_resolver,
        secret_value_resolver=secret_value_resolver,
        session_store=session_store,
        now=now,
    )


def reuse_delegated_provider_session(
    session: Any,
    identity_id: UUID,
    request: DelegatedExecutionRequest,
    entry: SourceRegistryEntry,
    profile: ProviderLoginProfile,
    *,
    session_store: SessionMaterialStore,
    now: datetime,
) -> session_service.DelegatedAuthenticatedPage:
    return session_service.reuse_delegated_provider_session(
        session,
        identity_id,
        request,
        PublicWebDelegatedLoginExecutor(entry, profile),
        session_store=session_store,
        now=now,
    )


def revoke_delegated_provider_session(
    session: Any,
    identity_id: UUID,
    request: DelegatedExecutionRequest,
    entry: SourceRegistryEntry,
    profile: ProviderLoginProfile,
    *,
    session_store: SessionMaterialStore,
    now: datetime,
) -> session_service.DelegatedSessionRevocationResult:
    return session_service.revoke_delegated_provider_session(
        session,
        identity_id,
        request,
        PublicWebDelegatedLoginExecutor(entry, profile),
        session_store=session_store,
        now=now,
    )
