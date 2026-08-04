from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from cip.modules.provider_onboarding.api.dependencies import ensure_provider_catalog
from cip.modules.provider_onboarding.api.schemas import (
    ActorRequest,
    HumanCheckpointRequest,
    ProviderOnboardingPageResponse,
    ProviderOnboardingResponse,
    SecretReferenceRequest,
)
from cip.modules.provider_onboarding.application.secrets import (
    LocalSecretReferenceResolver,
)
from cip.modules.provider_onboarding.application.service import (
    ProviderOnboardingBlockedError,
    ProviderOnboardingNotFoundError,
    get_provider_onboarding,
    list_provider_onboarding,
    register_secret_reference,
    revoke_provider_onboarding,
    set_human_checkpoint,
    start_provider_onboarding,
    verify_provider_configuration,
)
from cip.modules.provider_onboarding.domain.models import (
    ProviderOnboarding,
    SecretReference,
)
from cip.shared.config.settings import Settings, get_settings
from cip.shared.kernel.time import utc_now
from cip.shared.persistence.dependencies import get_database_session

router = APIRouter(prefix="/v1/provider-onboarding", tags=["provider-onboarding"])
SessionDependency = Annotated[Session, Depends(get_database_session)]
SettingsDependency = Annotated[Settings, Depends(get_settings)]


@router.get("/providers", response_model=ProviderOnboardingPageResponse)
def read_provider_catalog(
    session: SessionDependency,
    settings: SettingsDependency,
) -> ProviderOnboardingPageResponse:
    _prepare(session, settings)
    providers = list_provider_onboarding(session)
    return ProviderOnboardingPageResponse(
        items=[ProviderOnboardingResponse.from_domain(item) for item in providers],
        total=len(providers),
    )


@router.get("/providers/{source_id}", response_model=ProviderOnboardingResponse)
def read_provider(
    source_id: str,
    session: SessionDependency,
    settings: SettingsDependency,
) -> ProviderOnboardingResponse:
    _prepare(session, settings)
    return ProviderOnboardingResponse.from_domain(_get(session, source_id))


@router.post("/providers/{source_id}/start", response_model=ProviderOnboardingResponse)
def start_provider(
    source_id: str,
    payload: ActorRequest,
    session: SessionDependency,
    settings: SettingsDependency,
) -> ProviderOnboardingResponse:
    _prepare(session, settings)
    try:
        result = start_provider_onboarding(
            session,
            source_id,
            actor=payload.actor,
            now=utc_now(),
        )
    except ProviderOnboardingNotFoundError as exc:
        raise HTTPException(status_code=404, detail="provider not found") from exc
    except ProviderOnboardingBlockedError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return ProviderOnboardingResponse.from_domain(result)


@router.post(
    "/providers/{source_id}/human-checkpoint",
    response_model=ProviderOnboardingResponse,
)
def record_human_checkpoint(
    source_id: str,
    payload: HumanCheckpointRequest,
    session: SessionDependency,
    settings: SettingsDependency,
) -> ProviderOnboardingResponse:
    _prepare(session, settings)
    try:
        result = set_human_checkpoint(
            session,
            source_id,
            state=payload.state,
            actor=payload.actor,
            now=utc_now(),
            note=payload.note,
        )
    except ProviderOnboardingNotFoundError as exc:
        raise HTTPException(status_code=404, detail="provider not found") from exc
    except ProviderOnboardingBlockedError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return ProviderOnboardingResponse.from_domain(result)


@router.post(
    "/providers/{source_id}/secret-reference",
    response_model=ProviderOnboardingResponse,
)
def add_secret_reference(
    source_id: str,
    payload: SecretReferenceRequest,
    session: SessionDependency,
    settings: SettingsDependency,
) -> ProviderOnboardingResponse:
    _prepare(session, settings)
    try:
        result = register_secret_reference(
            session,
            source_id,
            name=payload.name,
            reference=SecretReference(payload.reference),
            actor=payload.actor,
            now=utc_now(),
        )
    except ProviderOnboardingNotFoundError as exc:
        raise HTTPException(status_code=404, detail="provider not found") from exc
    except ProviderOnboardingBlockedError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return ProviderOnboardingResponse.from_domain(result)


@router.post("/providers/{source_id}/verify", response_model=ProviderOnboardingResponse)
def verify_provider(
    source_id: str,
    payload: ActorRequest,
    session: SessionDependency,
    settings: SettingsDependency,
) -> ProviderOnboardingResponse:
    _prepare(session, settings)
    try:
        result = verify_provider_configuration(
            session,
            source_id,
            resolver=LocalSecretReferenceResolver(),
            actor=payload.actor,
            now=utc_now(),
        )
    except ProviderOnboardingNotFoundError as exc:
        raise HTTPException(status_code=404, detail="provider not found") from exc
    except ProviderOnboardingBlockedError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return ProviderOnboardingResponse.from_domain(result)


@router.post("/providers/{source_id}/revoke", response_model=ProviderOnboardingResponse)
def revoke_provider(
    source_id: str,
    payload: ActorRequest,
    session: SessionDependency,
    settings: SettingsDependency,
) -> ProviderOnboardingResponse:
    _prepare(session, settings)
    try:
        result = revoke_provider_onboarding(
            session,
            source_id,
            actor=payload.actor,
            now=utc_now(),
        )
    except ProviderOnboardingNotFoundError as exc:
        raise HTTPException(status_code=404, detail="provider not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return ProviderOnboardingResponse.from_domain(result)


def _prepare(session: Session, settings: Settings) -> None:
    ensure_provider_catalog(session, settings)


def _get(session: Session, source_id: str) -> ProviderOnboarding:
    try:
        return get_provider_onboarding(session, source_id)
    except ProviderOnboardingNotFoundError as exc:
        raise HTTPException(status_code=404, detail="provider not found") from exc
