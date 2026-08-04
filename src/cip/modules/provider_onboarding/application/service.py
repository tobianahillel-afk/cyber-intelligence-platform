from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from cip.modules.provider_onboarding.application.secrets import SecretReferenceResolver
from cip.modules.provider_onboarding.domain.models import (
    AuthMode,
    HumanAction,
    OnboardingState,
    ProviderOnboarding,
    ProviderProfile,
    SecretReference,
)
from cip.modules.provider_onboarding.infrastructure.models import (
    ProviderOnboardingAuditRecord,
    ProviderOnboardingRecord,
)
from cip.modules.provider_onboarding.infrastructure.persistence_time import normalize_optional_utc
from cip.modules.source_governance.infrastructure.models import SourceRecord
from cip.shared.kernel.time import require_aware_utc

_HUMAN_CHECKPOINT_STATES = {
    OnboardingState.AWAITING_USER_ACTION,
    OnboardingState.AWAITING_EMAIL_VERIFICATION,
    OnboardingState.AWAITING_MFA,
    OnboardingState.AWAITING_PROVIDER_APPROVAL,
}


class ProviderOnboardingNotFoundError(LookupError):
    pass


class ProviderOnboardingBlockedError(RuntimeError):
    pass


def sync_provider_profiles(
    session: Session,
    profiles: Sequence[ProviderProfile],
    *,
    now: datetime,
) -> tuple[str, ...]:
    synchronized_at = require_aware_utc(now, field_name="now")
    existing_source_ids = set(session.scalars(select(SourceRecord.id)).all())
    synchronized: list[str] = []
    for profile in profiles:
        if profile.source_id not in existing_source_ids:
            continue
        record = session.get(ProviderOnboardingRecord, profile.source_id)
        if record is None:
            record = _new_record(profile, synchronized_at)
            session.add(record)
            _audit(
                session,
                source_id=profile.source_id,
                action="catalog_synced",
                previous_state=None,
                new_state=profile.initial_state,
                actor="system",
                occurred_at=synchronized_at,
                details={"auth_mode": profile.auth_mode.value},
            )
        else:
            _refresh_record(record, profile, synchronized_at)
        synchronized.append(profile.source_id)
    session.flush()
    return tuple(synchronized)


def list_provider_onboarding(session: Session) -> tuple[ProviderOnboarding, ...]:
    records = session.scalars(
        select(ProviderOnboardingRecord).order_by(ProviderOnboardingRecord.source_id)
    ).all()
    return tuple(_to_domain(record) for record in records)


def get_provider_onboarding(session: Session, source_id: str) -> ProviderOnboarding:
    return _to_domain(_get_record(session, source_id))


def start_provider_onboarding(
    session: Session,
    source_id: str,
    *,
    actor: str,
    now: datetime,
) -> ProviderOnboarding:
    record = _get_record(session, source_id)
    changed_at = require_aware_utc(now, field_name="now")
    if record.blocked_reason:
        raise ProviderOnboardingBlockedError(record.blocked_reason)
    previous = OnboardingState(record.state)
    target = (
        OnboardingState.CONNECTED
        if AuthMode(record.auth_mode) is AuthMode.NONE
        else OnboardingState.AWAITING_USER_ACTION
    )
    if target is OnboardingState.CONNECTED:
        record.last_verified_at = changed_at
    _transition(session, record, target, "onboarding_started", actor, changed_at, previous)
    return _to_domain(record)


def set_human_checkpoint(
    session: Session,
    source_id: str,
    *,
    state: OnboardingState,
    actor: str,
    now: datetime,
    note: str | None = None,
) -> ProviderOnboarding:
    if state not in _HUMAN_CHECKPOINT_STATES:
        raise ValueError("state is not a supported human checkpoint")
    record = _get_record(session, source_id)
    _ensure_not_blocked(record)
    previous = OnboardingState(record.state)
    _transition(
        session,
        record,
        state,
        "human_checkpoint_recorded",
        actor,
        require_aware_utc(now, field_name="now"),
        previous,
        details={"note": _bounded_note(note)},
    )
    return _to_domain(record)


def register_secret_reference(
    session: Session,
    source_id: str,
    *,
    name: str,
    reference: SecretReference,
    actor: str,
    now: datetime,
) -> ProviderOnboarding:
    record = _get_record(session, source_id)
    _ensure_not_blocked(record)
    if AuthMode(record.auth_mode) is AuthMode.NONE:
        raise ValueError("provider does not require a secret")
    onboarding = _to_domain(record).with_secret_reference(name, reference)
    record.secret_references = {
        key: value.value for key, value in onboarding.secret_references.items()
    }
    _transition(
        session,
        record,
        onboarding.state,
        "secret_reference_registered",
        actor,
        require_aware_utc(now, field_name="now"),
        OnboardingState(record.state),
        details={"secret_name": name.strip(), "reference": reference.redacted},
    )
    return _to_domain(record)


def verify_provider_configuration(
    session: Session,
    source_id: str,
    *,
    resolver: SecretReferenceResolver,
    actor: str,
    now: datetime,
) -> ProviderOnboarding:
    record = _get_record(session, source_id)
    _ensure_not_blocked(record)
    changed_at = require_aware_utc(now, field_name="now")
    onboarding = _to_domain(record)
    target, error_code, error_message = _verification_result(onboarding, resolver)
    previous = OnboardingState(record.state)
    record.last_error_code = error_code
    record.last_error_message = error_message
    record.last_verified_at = changed_at if target is OnboardingState.CONNECTED else None
    _transition(
        session,
        record,
        target,
        "configuration_verified",
        actor,
        changed_at,
        previous,
        details={"result": target.value, "error_code": error_code},
    )
    return _to_domain(record)


def revoke_provider_onboarding(
    session: Session,
    source_id: str,
    *,
    actor: str,
    now: datetime,
) -> ProviderOnboarding:
    record = _get_record(session, source_id)
    previous = OnboardingState(record.state)
    record.secret_references = {}
    record.last_verified_at = None
    record.expires_at = None
    record.last_error_code = None
    record.last_error_message = None
    _transition(
        session,
        record,
        OnboardingState.REVOKED,
        "provider_revoked",
        actor,
        require_aware_utc(now, field_name="now"),
        previous,
    )
    return _to_domain(record)


def _verification_result(
    onboarding: ProviderOnboarding,
    resolver: SecretReferenceResolver,
) -> tuple[OnboardingState, str | None, str | None]:
    if onboarding.auth_mode is AuthMode.NONE:
        return OnboardingState.CONNECTED, None, None
    if onboarding.auth_mode is AuthMode.MANUAL:
        return (
            OnboardingState.AWAITING_PROVIDER_APPROVAL,
            "manual_provider_authorization_required",
            "Provider authorization and scopes require human review.",
        )
    if onboarding.missing_secret_names:
        return (
            OnboardingState.FAILED,
            "missing_secret_references",
            "One or more required secret references are missing.",
        )
    unavailable = [
        name
        for name, reference in onboarding.secret_references.items()
        if not resolver.is_available(reference)
    ]
    if unavailable:
        return (
            OnboardingState.FAILED,
            "secret_reference_unavailable",
            "One or more secret references cannot be resolved by this deployment.",
        )
    return OnboardingState.CONNECTED, None, None


def _new_record(profile: ProviderProfile, now: datetime) -> ProviderOnboardingRecord:
    return ProviderOnboardingRecord(
        source_id=profile.source_id,
        display_name=profile.display_name,
        auth_mode=profile.auth_mode.value,
        state=profile.initial_state.value,
        documentation_url=profile.documentation_url,
        signup_url=profile.signup_url,
        console_url=profile.console_url,
        required_secret_names=list(profile.required_secret_names),
        human_actions=[action.value for action in profile.human_actions],
        automatic_onboarding=profile.automatic_onboarding,
        secret_references={},
        blocked_reason=profile.blocked_reason,
        last_verified_at=now if profile.initial_state is OnboardingState.CONNECTED else None,
        expires_at=None,
        last_error_code=None,
        last_error_message=None,
        created_at=now,
        updated_at=now,
    )


def _refresh_record(
    record: ProviderOnboardingRecord,
    profile: ProviderProfile,
    now: datetime,
) -> None:
    record.display_name = profile.display_name
    record.auth_mode = profile.auth_mode.value
    record.documentation_url = profile.documentation_url
    record.signup_url = profile.signup_url
    record.console_url = profile.console_url
    record.required_secret_names = list(profile.required_secret_names)
    record.human_actions = [action.value for action in profile.human_actions]
    record.automatic_onboarding = profile.automatic_onboarding
    record.blocked_reason = profile.blocked_reason
    if profile.blocked_reason:
        record.state = OnboardingState.BLOCKED.value
        record.secret_references = {}
    record.updated_at = now


def _to_domain(record: ProviderOnboardingRecord) -> ProviderOnboarding:
    return ProviderOnboarding(
        source_id=record.source_id,
        display_name=record.display_name,
        auth_mode=AuthMode(record.auth_mode),
        state=OnboardingState(record.state),
        documentation_url=record.documentation_url,
        signup_url=record.signup_url,
        console_url=record.console_url,
        required_secret_names=tuple(record.required_secret_names),
        human_actions=tuple(HumanAction(value) for value in record.human_actions),
        automatic_onboarding=record.automatic_onboarding,
        secret_references={
            name: SecretReference(value)
            for name, value in record.secret_references.items()
        },
        blocked_reason=record.blocked_reason,
        last_verified_at=normalize_optional_utc(record.last_verified_at),
        expires_at=normalize_optional_utc(record.expires_at),
        last_error_code=record.last_error_code,
        last_error_message=record.last_error_message,
        updated_at=normalize_optional_utc(record.updated_at),
    )


def _transition(
    session: Session,
    record: ProviderOnboardingRecord,
    target: OnboardingState,
    action: str,
    actor: str,
    occurred_at: datetime,
    previous: OnboardingState,
    *,
    details: dict[str, object] | None = None,
) -> None:
    record.state = target.value
    record.updated_at = occurred_at
    _audit(
        session,
        source_id=record.source_id,
        action=action,
        previous_state=previous,
        new_state=target,
        actor=_actor(actor),
        occurred_at=occurred_at,
        details=details or {},
    )
    session.flush()


def _audit(
    session: Session,
    *,
    source_id: str,
    action: str,
    previous_state: OnboardingState | None,
    new_state: OnboardingState,
    actor: str,
    occurred_at: datetime,
    details: dict[str, object],
) -> None:
    session.add(
        ProviderOnboardingAuditRecord(
            id=uuid4(),
            source_id=source_id,
            action=action,
            previous_state=previous_state.value if previous_state else None,
            new_state=new_state.value,
            actor=actor,
            details=details,
            occurred_at=occurred_at,
        )
    )


def _get_record(session: Session, source_id: str) -> ProviderOnboardingRecord:
    record = session.get(ProviderOnboardingRecord, source_id.strip())
    if record is None:
        raise ProviderOnboardingNotFoundError(source_id)
    return record


def _ensure_not_blocked(record: ProviderOnboardingRecord) -> None:
    if record.blocked_reason:
        raise ProviderOnboardingBlockedError(record.blocked_reason)


def _actor(value: str) -> str:
    actor = value.strip()
    if not actor or len(actor) > 200:
        raise ValueError("actor must be a non-empty value of at most 200 characters")
    return actor


def _bounded_note(value: str | None) -> str | None:
    if value is None:
        return None
    note = value.strip()
    if len(note) > 1_000:
        raise ValueError("note cannot exceed 1000 characters")
    return note or None
