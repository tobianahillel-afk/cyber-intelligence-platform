from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from cip.modules.source_governance.application import delegated_identity_service as service
from cip.modules.source_governance.application.delegated_identity_contracts import (
    DelegatedIdentityAuditEvent,
    DelegatedIdentityNotFoundError,
    DelegatedOperatorContext,
    DelegatedReferenceUnavailableError,
)
from cip.modules.source_governance.domain.accounts import (
    SourceAccount,
    SourceAccountAuthMode,
    SourceAccountStatus,
)
from cip.modules.source_governance.domain.delegated_browser_identity import (
    DelegatedBrowserIdentity,
    DelegatedOwnerKind,
)
from cip.modules.source_governance.infrastructure import delegated_identity_persistence
from cip.shared.persistence.metadata import get_metadata
from cip.shared.persistence.session import create_database_engine, create_session_factory

NOW = datetime(2026, 8, 16, 21, 45, tzinfo=UTC)
TENANT = uuid4()


class _NeverResolver:
    def is_available(self, _reference) -> bool:
        pytest.fail("resolver must not run when the required reference is absent")


def _account(
    *,
    status: SourceAccountStatus = SourceAccountStatus.PENDING_VERIFICATION,
    created_at: datetime = NOW,
) -> SourceAccount:
    return SourceAccount(
        source_id="missing-source",
        external_reference="provider-account",
        auth_mode=SourceAccountAuthMode.INTERACTIVE_SESSION,
        status=status,
        authorization_document_reference="AUTH-L15-COVERAGE",
        approved_purposes=frozenset({"provider-research"}),
        created_at=created_at,
        verified_at=(created_at if status is SourceAccountStatus.ACTIVE else None),
        expires_at=created_at + timedelta(days=30),
    )


def _identity(
    *,
    account: SourceAccount | None = None,
    created_at: datetime = NOW,
    **changes: object,
) -> DelegatedBrowserIdentity:
    values: dict[str, object] = {
        "account": account or _account(),
        "tenant_id": TENANT,
        "owner_kind": DelegatedOwnerKind.USER,
        "owner_subject_id": "user-coverage",
        "purpose": "provider-research",
        "approved_scopes": frozenset({"profile.read"}),
        "created_at": created_at,
    }
    values.update(changes)
    return DelegatedBrowserIdentity(**values)  # type: ignore[arg-type]


def _actor() -> DelegatedOperatorContext:
    return DelegatedOperatorContext(TENANT, DelegatedOwnerKind.USER, "user-coverage")


def _factory():
    engine = create_database_engine("sqlite+pysqlite:///:memory:")
    get_metadata().create_all(engine)
    return create_session_factory(engine)


def test_domain_rejects_creation_time_mismatch() -> None:
    with pytest.raises(ValueError, match="creation time"):
        _identity(
            account=_account(created_at=NOW),
            created_at=NOW + timedelta(seconds=1),
        )


def test_domain_rejects_deleted_identity_retaining_reference() -> None:
    revoked = _account(status=SourceAccountStatus.REVOKED)
    with pytest.raises(ValueError, match="deleted identity cannot retain"):
        _identity(
            account=revoked,
            revoked_at=NOW + timedelta(seconds=1),
            deleted_at=NOW + timedelta(seconds=2),
            secret_reference="vault://cip/deleted-secret",
        )


def test_domain_rejects_revoked_metadata_on_active_account() -> None:
    active = _account(status=SourceAccountStatus.ACTIVE)
    with pytest.raises(ValueError, match="revoked source account"):
        _identity(
            account=active,
            authorized_at=NOW,
            reviewed_at=NOW,
            revoked_at=NOW + timedelta(seconds=1),
        )


def test_register_fails_when_source_record_is_missing() -> None:
    factory = _factory()
    identity = _identity()
    with factory() as session:
        with pytest.raises(ValueError, match="source must exist"):
            service.register_delegated_identity(
                session,
                identity,
                actor=_actor(),
                now=NOW,
            )


def test_persist_change_fails_when_identity_record_is_missing() -> None:
    factory = _factory()
    identity = _identity()
    with factory() as session:
        with pytest.raises(DelegatedIdentityNotFoundError):
            service._persist_change(
                session,
                identity,
                _actor(),
                DelegatedIdentityAuditEvent.USED,
                NOW,
            )


def test_required_reference_missing_fails_before_resolver() -> None:
    with pytest.raises(DelegatedReferenceUnavailableError, match="missing"):
        service._required_available(None, True, _NeverResolver())


def test_persistence_utc_coercion_covers_aware_and_naive_values() -> None:
    assert delegated_identity_persistence._coerce_utc(NOW) == NOW
    naive = NOW.replace(tzinfo=None)
    coerced = delegated_identity_persistence._coerce_utc(naive)
    assert coerced.tzinfo is UTC
    assert coerced.replace(tzinfo=None) == naive
