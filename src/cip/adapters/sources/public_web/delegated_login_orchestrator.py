from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy.orm import Session

from cip.adapters.sources.public_web.delegated_login_runtime import (
    ProviderAuthenticatedRuntimeResult,
    ProviderLoginRuntimeError,
    execute_reviewed_provider_login,
    execute_reviewed_provider_logout,
    execute_reviewed_session_reuse,
)
from cip.modules.provider_onboarding.application.secrets import (
    SecretReferenceResolver,
    SecretValueResolver,
)
from cip.modules.provider_onboarding.domain.browser_login import ProviderLoginProfile
from cip.modules.provider_onboarding.domain.models import SecretReference
from cip.modules.source_governance.application.delegated_identity_contracts import (
    DelegatedIdentityExecutionGrant,
    DelegatedOperatorContext,
)
from cip.modules.source_governance.application.delegated_identity_service import (
    attach_delegated_session_reference,
    get_delegated_identity,
    issue_delegated_execution_grant,
    revoke_delegated_identity,
)
from cip.modules.source_governance.application.session_material import SessionMaterialStore
from cip.modules.source_governance.domain.accounts import SourceAccountAuthMode
from cip.modules.source_governance.domain.delegated_browser_identity import (
    DelegatedExecutionRequest,
)
from cip.modules.source_governance.infrastructure.registry import SourceRegistryEntry
from cip.shared.kernel.time import require_aware_utc


class DelegatedLoginOrchestrationError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class DelegatedAuthenticatedPage:
    identity_id: UUID
    source_id: str
    final_url: str
    html: bytes = field(repr=False)
    session_established: bool = False
    session_reused: bool = False
    requests_seen: int = 0
    redirects_seen: int = 0


@dataclass(frozen=True, slots=True)
class DelegatedSessionRevocationResult:
    identity_id: UUID
    local_revoked: bool
    remote_logout_attempted: bool
    remote_logout_completed: bool


def establish_delegated_provider_session(
    session: Session,
    identity_id: UUID,
    request: DelegatedExecutionRequest,
    entry: SourceRegistryEntry,
    profile: ProviderLoginProfile,
    *,
    secret_reference_resolver: SecretReferenceResolver,
    secret_value_resolver: SecretValueResolver,
    session_store: SessionMaterialStore,
    now: datetime,
) -> DelegatedAuthenticatedPage:
    current = require_aware_utc(now, field_name="now")
    actor = _actor(request)
    view = get_delegated_identity(session, identity_id, actor=actor)
    _validate_login_context(view.source_id, view.auth_mode, entry, profile)
    grant = issue_delegated_execution_grant(
        session,
        identity_id,
        replace(
            request,
            require_secret_reference=True,
            require_session_reference=False,
        ),
        resolver=secret_reference_resolver,
        now=current,
    )
    secret_reference = _required_reference(grant.secret_reference, "login secret")
    runtime = execute_reviewed_provider_login(
        entry,
        profile,
        account_identifier=view.provider_account_identifier,
        secret_reference=secret_reference,
        secret_resolver=secret_value_resolver,
        purpose=grant.purpose,
        now=current,
    )
    session_reference = session_store.reference_for(identity_id)
    try:
        session_store.write(session_reference, runtime.session_state_json)
        attach_delegated_session_reference(
            session,
            identity_id,
            session_reference.value,
            actor=actor,
            resolver=session_store,
            now=current,
            expires_at=current + timedelta(seconds=profile.session_ttl_seconds),
        )
    except BaseException:
        session_store.delete(session_reference)
        raise
    return _safe_page(grant, runtime, established=True, reused=False)


def reuse_delegated_provider_session(
    session: Session,
    identity_id: UUID,
    request: DelegatedExecutionRequest,
    entry: SourceRegistryEntry,
    profile: ProviderLoginProfile,
    *,
    session_store: SessionMaterialStore,
    now: datetime,
) -> DelegatedAuthenticatedPage:
    current = require_aware_utc(now, field_name="now")
    actor = _actor(request)
    view = get_delegated_identity(session, identity_id, actor=actor)
    _validate_login_context(view.source_id, view.auth_mode, entry, profile)
    grant = issue_delegated_execution_grant(
        session,
        identity_id,
        replace(
            request,
            require_secret_reference=False,
            require_session_reference=True,
        ),
        resolver=session_store,
        now=current,
    )
    session_reference = _required_reference(grant.session_reference, "browser session")
    runtime = execute_reviewed_session_reuse(
        entry,
        profile,
        session_reference=session_reference,
        session_resolver=session_store,
        purpose=grant.purpose,
        now=current,
    )
    session_store.write(session_reference, runtime.session_state_json)
    return _safe_page(grant, runtime, established=False, reused=True)


def revoke_delegated_provider_session(
    session: Session,
    identity_id: UUID,
    request: DelegatedExecutionRequest,
    entry: SourceRegistryEntry,
    profile: ProviderLoginProfile,
    *,
    session_store: SessionMaterialStore,
    now: datetime,
) -> DelegatedSessionRevocationResult:
    current = require_aware_utc(now, field_name="now")
    actor = _actor(request)
    view = get_delegated_identity(session, identity_id, actor=actor)
    _validate_login_context(view.source_id, view.auth_mode, entry, profile)
    remote_attempted = False
    remote_completed = False
    reference: SecretReference | None = None
    try:
        grant = issue_delegated_execution_grant(
            session,
            identity_id,
            replace(
                request,
                require_secret_reference=False,
                require_session_reference=True,
            ),
            resolver=session_store,
            now=current,
        )
        reference = _required_reference(grant.session_reference, "browser session")
        if profile.logout_url is not None:
            remote_attempted = True
            try:
                remote_completed = execute_reviewed_provider_logout(
                    entry,
                    profile,
                    session_reference=reference,
                    session_resolver=session_store,
                    purpose=grant.purpose,
                    now=current,
                )
            except ProviderLoginRuntimeError:
                remote_completed = False
    finally:
        revoke_delegated_identity(session, identity_id, actor=actor, now=current)
        if reference is not None:
            session_store.delete(reference)
    return DelegatedSessionRevocationResult(
        identity_id=identity_id,
        local_revoked=True,
        remote_logout_attempted=remote_attempted,
        remote_logout_completed=remote_completed,
    )


def _validate_login_context(
    source_id: str,
    auth_mode: SourceAccountAuthMode,
    entry: SourceRegistryEntry,
    profile: ProviderLoginProfile,
) -> None:
    if auth_mode is not SourceAccountAuthMode.INTERACTIVE_SESSION:
        raise DelegatedLoginOrchestrationError("delegated identity is not interactive-session auth")
    if source_id != entry.policy.id or profile.source_id != source_id:
        raise DelegatedLoginOrchestrationError("delegated login source/profile mismatch")


def _required_reference(value: str | None, label: str) -> SecretReference:
    if value is None:
        raise DelegatedLoginOrchestrationError(f"required {label} reference is missing")
    return SecretReference(value)


def _actor(request: DelegatedExecutionRequest) -> DelegatedOperatorContext:
    return DelegatedOperatorContext(
        tenant_id=request.tenant_id,
        owner_kind=request.owner_kind,
        owner_subject_id=request.owner_subject_id,
    )


def _safe_page(
    grant: DelegatedIdentityExecutionGrant,
    runtime: ProviderAuthenticatedRuntimeResult,
    *,
    established: bool,
    reused: bool,
) -> DelegatedAuthenticatedPage:
    return DelegatedAuthenticatedPage(
        identity_id=grant.identity_id,
        source_id=grant.source_id,
        final_url=runtime.final_url,
        html=runtime.html,
        session_established=established,
        session_reused=reused,
        requests_seen=runtime.requests_seen,
        redirects_seen=runtime.redirects_seen,
    )
