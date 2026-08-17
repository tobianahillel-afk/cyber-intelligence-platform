from __future__ import annotations

import secrets
from collections.abc import Callable
from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta
from typing import Any, Protocol
from uuid import UUID, uuid4

import httpx

from cip.adapters.sources.public_web.collection_policy import authorize_public_web_url
from cip.adapters.sources.public_web.federated_continuation import (
    FederatedContinuationBundle,
    FederatedContinuationState,
)
from cip.adapters.sources.public_web.federated_token_runtime import (
    FederatedTokenMaterial,
    OidcIdTokenVerifier,
    exchange_federated_authorization_code,
)
from cip.modules.collection_orchestration.domain.human_checkpoints import (
    HumanCheckpointBinding,
    HumanCheckpointKind,
    HumanCheckpointRequest,
    HumanCheckpointResumeRequest,
    correlation_digest,
)
from cip.modules.provider_onboarding.application.federated_authorization import (
    create_federated_authorization,
    validate_federated_callback,
)
from cip.modules.provider_onboarding.application.federated_material import (
    FederatedContinuationMaterialStore,
)
from cip.modules.provider_onboarding.application.secrets import SecretReferenceResolver
from cip.modules.provider_onboarding.domain.federated_auth import ProviderFederatedAuthProfile
from cip.modules.provider_onboarding.domain.models import SecretReference
from cip.modules.source_governance.application.delegated_identity_contracts import (
    DelegatedIdentityExecutionGrant,
    DelegatedOperatorContext,
)
from cip.modules.source_governance.application.delegated_identity_service import (
    attach_delegated_session_reference,
    issue_delegated_execution_grant,
)
from cip.modules.source_governance.domain.delegated_browser_identity import (
    DelegatedExecutionRequest,
)
from cip.modules.source_governance.domain.models import HttpMethod
from cip.modules.source_governance.infrastructure.registry import SourceRegistryEntry
from cip.shared.kernel.time import require_aware_utc


class HumanCheckpointResumer(Protocol):
    def __call__(self, session: Any, request: HumanCheckpointResumeRequest) -> UUID: ...


@dataclass(frozen=True, slots=True)
class FederatedCheckpointContext:
    delegated_identity_id: UUID
    collection_job_id: UUID
    adapter_id: str
    execution_request: DelegatedExecutionRequest

    def __post_init__(self) -> None:
        adapter_id = self.adapter_id.strip()
        if not adapter_id or len(adapter_id) > 200:
            raise ValueError("adapter_id must be 1..200 characters")
        object.__setattr__(self, "adapter_id", adapter_id)


@dataclass(frozen=True, slots=True)
class FederatedCheckpointStart:
    checkpoint: HumanCheckpointRequest
    authorization_url: str = field(repr=False)
    correlation_token: str = field(repr=False)


@dataclass(frozen=True, slots=True)
class FederatedCheckpointCompletion:
    checkpoint_id: UUID
    callback_url: str = field(repr=False)
    correlation_token: str = field(repr=False)
    actor_reference: str
    completed_at: datetime

    def __post_init__(self) -> None:
        if not self.callback_url.strip() or len(self.callback_url) > 8_000:
            raise ValueError("callback_url is invalid")
        actor = self.actor_reference.strip()
        if not actor or len(actor) > 200:
            raise ValueError("actor_reference is invalid")
        correlation_digest(self.correlation_token)
        object.__setattr__(self, "actor_reference", actor)
        object.__setattr__(
            self,
            "completed_at",
            require_aware_utc(self.completed_at, field_name="completed_at"),
        )


@dataclass(frozen=True, slots=True)
class FederatedCheckpointCompletionResult:
    checkpoint_id: UUID
    job_id: UUID
    session_reference: str
    token_exchange_reused: bool


def begin_delegated_federated_checkpoint(
    session: Any,
    context: FederatedCheckpointContext,
    entry: SourceRegistryEntry,
    profile: ProviderFederatedAuthProfile,
    *,
    identity_reference_resolver: SecretReferenceResolver,
    material_store: FederatedContinuationMaterialStore,
    now: datetime,
    token_factory: Callable[[], str] | None = None,
    resume_token_factory: Callable[[], str] | None = None,
    checkpoint_id_factory: Callable[[], UUID] = uuid4,
) -> FederatedCheckpointStart:
    current = require_aware_utc(now, field_name="now")
    _validate_context(context, entry, profile, now=current)
    _issue_grant(
        session,
        context,
        profile,
        resolver=identity_reference_resolver,
        now=current,
        require_session=False,
    )
    authorize_public_web_url(
        entry,
        profile.authorization_url,
        now=current,
        http_method=HttpMethod.GET,
        purpose=context.execution_request.purpose,
    )
    authorization = create_federated_authorization(profile, token_factory=token_factory)
    resume_factory = resume_token_factory or (lambda: secrets.token_urlsafe(48))
    resume_token = resume_factory()
    digest = correlation_digest(resume_token)
    checkpoint_id = checkpoint_id_factory()
    reference = material_store.reference_for(context.delegated_identity_id, checkpoint_id)
    bundle = FederatedContinuationBundle(
        checkpoint_id=checkpoint_id,
        job_id=context.collection_job_id,
        delegated_identity_id=context.delegated_identity_id,
        source_id=context.execution_request.source_id,
        profile_id=profile.id,
        state=FederatedContinuationState.AUTHORIZATION_PENDING,
        authorization_url=authorization.authorization_url,
        authorization=authorization.material,
    )
    material_store.write(reference, bundle.to_secret_json())
    checkpoint = HumanCheckpointRequest(
        id=checkpoint_id,
        binding=_binding(context),
        kind=HumanCheckpointKind.OAUTH_CONSENT,
        correlation_digest=digest,
        session_reference=reference.value,
        created_at=current,
        expires_at=current + timedelta(seconds=profile.material_ttl_seconds),
    )
    return FederatedCheckpointStart(
        checkpoint=checkpoint,
        authorization_url=authorization.authorization_url,
        correlation_token=resume_token,
    )


def complete_delegated_federated_checkpoint(
    session: Any,
    context: FederatedCheckpointContext,
    entry: SourceRegistryEntry,
    profile: ProviderFederatedAuthProfile,
    completion: FederatedCheckpointCompletion,
    *,
    identity_reference_resolver: SecretReferenceResolver,
    material_store: FederatedContinuationMaterialStore,
    client: httpx.Client,
    resume_checkpoint: HumanCheckpointResumer,
    oidc_verifier: OidcIdTokenVerifier | None = None,
) -> FederatedCheckpointCompletionResult:
    current = completion.completed_at
    _validate_context(context, entry, profile, now=current)
    _issue_grant(
        session,
        context,
        profile,
        resolver=identity_reference_resolver,
        now=current,
        require_session=False,
    )
    reference = material_store.reference_for(
        context.delegated_identity_id,
        completion.checkpoint_id,
    )
    bundle = FederatedContinuationBundle.from_secret_json(material_store.resolve(reference))
    _validate_bundle(bundle, context, profile, completion.checkpoint_id)
    token_exchange_reused = bundle.state is FederatedContinuationState.TOKEN_READY
    if token_exchange_reused:
        token = _required_token(bundle)
    else:
        code = validate_federated_callback(
            profile,
            completion.callback_url,
            bundle.authorization,
        )
        token = exchange_federated_authorization_code(
            entry,
            profile,
            code,
            bundle.authorization,
            purpose=context.execution_request.purpose,
            now=current,
            client=client,
            oidc_verifier=oidc_verifier,
        )
        bundle = bundle.with_token(token)
        material_store.write(reference, bundle.to_secret_json())
    resumed_job_id = resume_checkpoint(
        session,
        HumanCheckpointResumeRequest(
            checkpoint_id=completion.checkpoint_id,
            binding=_binding(context),
            correlation_token=completion.correlation_token,
            actor_reference=completion.actor_reference,
            resumed_at=current,
        ),
    )
    if resumed_job_id != context.collection_job_id:
        raise RuntimeError("human checkpoint resumed an unexpected collection job")
    _attach_session_reference(
        session,
        context,
        reference,
        token,
        material_store=material_store,
        now=current,
    )
    return FederatedCheckpointCompletionResult(
        checkpoint_id=completion.checkpoint_id,
        job_id=resumed_job_id,
        session_reference=reference.value,
        token_exchange_reused=token_exchange_reused,
    )


def resolve_federated_token_for_job(
    session: Any,
    context: FederatedCheckpointContext,
    profile: ProviderFederatedAuthProfile,
    *,
    material_store: FederatedContinuationMaterialStore,
    now: datetime,
) -> FederatedTokenMaterial:
    current = require_aware_utc(now, field_name="now")
    grant = _issue_grant(
        session,
        context,
        profile,
        resolver=material_store,
        now=current,
        require_session=True,
    )
    if grant.session_reference is None:
        raise RuntimeError("federated session reference is unavailable")
    reference = SecretReference(grant.session_reference)
    bundle = FederatedContinuationBundle.from_secret_json(material_store.resolve(reference))
    _validate_bundle(bundle, context, profile, bundle.checkpoint_id)
    return _required_token(bundle)


def _issue_grant(
    session: Any,
    context: FederatedCheckpointContext,
    profile: ProviderFederatedAuthProfile,
    *,
    resolver: SecretReferenceResolver,
    now: datetime,
    require_session: bool,
) -> DelegatedIdentityExecutionGrant:
    request = replace(
        context.execution_request,
        required_scopes=frozenset(
            set(context.execution_request.required_scopes).union(profile.scopes)
        ),
        require_session_reference=require_session,
    )
    return issue_delegated_execution_grant(
        session,
        context.delegated_identity_id,
        request,
        resolver=resolver,
        now=now,
    )


def _attach_session_reference(
    session: Any,
    context: FederatedCheckpointContext,
    reference: SecretReference,
    token: FederatedTokenMaterial,
    *,
    material_store: FederatedContinuationMaterialStore,
    now: datetime,
) -> None:
    expiry = None
    if token.expires_in is not None:
        expiry = now + timedelta(seconds=token.expires_in)
    request = context.execution_request
    attach_delegated_session_reference(
        session,
        context.delegated_identity_id,
        reference.value,
        actor=DelegatedOperatorContext(
            tenant_id=request.tenant_id,
            owner_kind=request.owner_kind,
            owner_subject_id=request.owner_subject_id,
        ),
        resolver=material_store,
        now=now,
        expires_at=expiry,
    )


def _validate_context(
    context: FederatedCheckpointContext,
    entry: SourceRegistryEntry,
    profile: ProviderFederatedAuthProfile,
    *,
    now: datetime,
) -> None:
    if (
        context.execution_request.source_id != entry.policy.id
        or profile.source_id != entry.policy.id
    ):
        raise ValueError("federated checkpoint source binding mismatch")
    if not profile.requires_pkce or not profile.executable_at(now):
        raise ValueError("federated checkpoint profile is not executable")


def _validate_bundle(
    bundle: FederatedContinuationBundle,
    context: FederatedCheckpointContext,
    profile: ProviderFederatedAuthProfile,
    checkpoint_id: UUID,
) -> None:
    if (
        bundle.checkpoint_id != checkpoint_id
        or bundle.job_id != context.collection_job_id
        or bundle.delegated_identity_id != context.delegated_identity_id
        or bundle.source_id != context.execution_request.source_id
        or bundle.profile_id != profile.id
    ):
        raise ValueError("federated continuation binding mismatch")


def _required_token(bundle: FederatedContinuationBundle) -> FederatedTokenMaterial:
    if bundle.state is not FederatedContinuationState.TOKEN_READY or bundle.token is None:
        raise ValueError("federated continuation does not contain a ready token")
    return bundle.token


def _binding(context: FederatedCheckpointContext) -> HumanCheckpointBinding:
    request = context.execution_request
    return HumanCheckpointBinding(
        job_id=context.collection_job_id,
        source_id=request.source_id,
        adapter_id=context.adapter_id,
        delegated_identity_id=context.delegated_identity_id,
        purpose=request.purpose,
    )
