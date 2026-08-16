from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from cip.modules.source_governance.domain.accounts import (
    SourceAccount,
    SourceAccountAuthMode,
    SourceAccountStatus,
)
from cip.modules.source_governance.domain.delegated_browser_identity import (
    DelegatedBrowserIdentity,
    DelegatedExecutionRequest,
    DelegatedIdentityDecisionReason,
    DelegatedOwnerKind,
)

NOW = datetime(2026, 8, 16, 20, 30, tzinfo=UTC)
TENANT = uuid4()


def _account(**changes: object) -> SourceAccount:
    values: dict[str, object] = {
        "source_id": "provider-browser",
        "external_reference": "provider-account-1",
        "auth_mode": SourceAccountAuthMode.INTERACTIVE_SESSION,
        "status": SourceAccountStatus.PENDING_VERIFICATION,
        "authorization_document_reference": "AUTH-L15-1",
        "approved_purposes": frozenset({"authorized-provider-research"}),
        "created_at": NOW,
        "expires_at": NOW + timedelta(days=30),
    }
    values.update(changes)
    return SourceAccount(**values)  # type: ignore[arg-type]


def _identity(**changes: object) -> DelegatedBrowserIdentity:
    values: dict[str, object] = {
        "account": _account(),
        "tenant_id": TENANT,
        "owner_kind": DelegatedOwnerKind.USER,
        "owner_subject_id": "user-123",
        "purpose": "authorized-provider-research",
        "approved_scopes": frozenset({"profile.read", "company.read"}),
        "created_at": NOW,
    }
    values.update(changes)
    return DelegatedBrowserIdentity(**values)  # type: ignore[arg-type]


def _request(**changes: object) -> DelegatedExecutionRequest:
    values: dict[str, object] = {
        "tenant_id": TENANT,
        "owner_kind": DelegatedOwnerKind.USER,
        "owner_subject_id": "user-123",
        "source_id": "provider-browser",
        "purpose": "authorized-provider-research",
        "required_scopes": frozenset({"profile.read"}),
    }
    values.update(changes)
    return DelegatedExecutionRequest(**values)  # type: ignore[arg-type]


def _active_identity(**changes: object) -> DelegatedBrowserIdentity:
    identity = _identity().authorize(reviewed_at=NOW + timedelta(minutes=1))
    if changes:
        values = {
            field_name: getattr(identity, field_name)
            for field_name in identity.__dataclass_fields__
        }
        values.update(changes)
        return DelegatedBrowserIdentity(**values)
    return identity


def test_authorized_identity_allows_exact_owner_scope() -> None:
    identity = _active_identity()
    decision = identity.evaluate_execution(_request(), now=NOW + timedelta(minutes=2))

    assert decision.allowed is True
    assert decision.reason is DelegatedIdentityDecisionReason.ALLOWED
    assert identity.authorized_at == NOW + timedelta(minutes=1)
    assert identity.account.verified_at == NOW + timedelta(minutes=1)


@pytest.mark.parametrize(
    ("changes", "reason"),
    [
        ({"tenant_id": uuid4()}, DelegatedIdentityDecisionReason.TENANT_MISMATCH),
        ({"owner_subject_id": "other"}, DelegatedIdentityDecisionReason.OWNER_MISMATCH),
        (
            {"owner_kind": DelegatedOwnerKind.SERVICE_PRINCIPAL},
            DelegatedIdentityDecisionReason.OWNER_MISMATCH,
        ),
        ({"source_id": "other-provider"}, DelegatedIdentityDecisionReason.SOURCE_MISMATCH),
        ({"purpose": "other-purpose"}, DelegatedIdentityDecisionReason.PURPOSE_MISMATCH),
        (
            {"required_scopes": frozenset({"admin.write"})},
            DelegatedIdentityDecisionReason.SCOPE_MISMATCH,
        ),
    ],
)
def test_execution_fails_closed_on_ownership_or_scope_mismatch(
    changes: dict[str, object],
    reason: DelegatedIdentityDecisionReason,
) -> None:
    decision = _active_identity().evaluate_execution(
        _request(**changes),
        now=NOW + timedelta(minutes=2),
    )
    assert decision.allowed is False
    assert decision.reason is reason


def test_secret_and_session_requirements_are_explicit() -> None:
    identity = _active_identity()
    secret_required = identity.evaluate_execution(
        _request(require_secret_reference=True),
        now=NOW + timedelta(minutes=2),
    )
    session_required = identity.evaluate_execution(
        _request(require_session_reference=True),
        now=NOW + timedelta(minutes=2),
    )

    assert secret_required.reason is DelegatedIdentityDecisionReason.SECRET_REFERENCE_REQUIRED
    assert session_required.reason is DelegatedIdentityDecisionReason.SESSION_REFERENCE_REQUIRED

    identity = identity.attach_secret_reference(
        "vault://cip/provider/login",
        at=NOW + timedelta(minutes=2),
    ).attach_session_reference(
        "vault://cip/provider/session",
        at=NOW + timedelta(minutes=3),
        expires_at=NOW + timedelta(hours=1),
    )
    decision = identity.evaluate_execution(
        _request(require_secret_reference=True, require_session_reference=True),
        now=NOW + timedelta(minutes=4),
    )
    assert decision.allowed is True
    assert identity.reference_version == 2


def test_session_expiry_is_independent_from_account_expiry() -> None:
    identity = _active_identity().attach_session_reference(
        "vault://cip/provider/session",
        at=NOW + timedelta(minutes=2),
        expires_at=NOW + timedelta(minutes=3),
    )
    decision = identity.evaluate_execution(
        _request(require_session_reference=True),
        now=NOW + timedelta(minutes=4),
    )
    assert decision.reason is DelegatedIdentityDecisionReason.SESSION_EXPIRED


def test_account_expiry_is_fail_closed() -> None:
    account = _account(
        status=SourceAccountStatus.ACTIVE,
        verified_at=NOW,
        expires_at=NOW + timedelta(minutes=1),
    )
    identity = _identity(
        account=account,
        authorized_at=NOW,
        reviewed_at=NOW,
    )
    decision = identity.evaluate_execution(_request(), now=NOW + timedelta(minutes=2))
    assert decision.reason is DelegatedIdentityDecisionReason.ACCOUNT_EXPIRED


def test_revocation_and_deletion_prevent_future_execution() -> None:
    active = _active_identity().attach_secret_reference(
        "vault://cip/provider/login",
        at=NOW + timedelta(minutes=2),
    ).attach_session_reference(
        "vault://cip/provider/session",
        at=NOW + timedelta(minutes=3),
    )
    revoked = active.revoke(at=NOW + timedelta(minutes=4))
    assert revoked.evaluate_execution(_request(), now=NOW + timedelta(minutes=5)).reason is (
        DelegatedIdentityDecisionReason.REVOKED
    )

    deleted = revoked.delete(at=NOW + timedelta(minutes=6))
    assert deleted.secret_reference is None
    assert deleted.session_reference is None
    assert deleted.evaluate_execution(_request(), now=NOW + timedelta(minutes=7)).reason is (
        DelegatedIdentityDecisionReason.DELETED
    )


def test_renew_updates_expiry_without_changing_identity() -> None:
    identity = _active_identity()
    renewed = identity.renew(
        expires_at=NOW + timedelta(days=60),
        at=NOW + timedelta(days=20),
    )
    assert renewed.id == identity.id
    assert renewed.account.expires_at == NOW + timedelta(days=60)
    assert renewed.renewed_at == NOW + timedelta(days=20)


def test_mark_used_updates_source_account_metadata() -> None:
    identity = _active_identity()
    used = identity.mark_used(at=NOW + timedelta(minutes=5))
    assert used.account.last_used_at == NOW + timedelta(minutes=5)


def test_secret_and_session_references_are_not_in_domain_repr() -> None:
    identity = _active_identity().attach_secret_reference(
        "vault://very-sensitive/provider-secret-path",
        at=NOW + timedelta(minutes=2),
    ).attach_session_reference(
        "vault://very-sensitive/browser-session-path",
        at=NOW + timedelta(minutes=3),
    )
    rendered = repr(identity)
    assert "provider-secret-path" not in rendered
    assert "browser-session-path" not in rendered
    assert "secret_reference=" not in rendered
    assert "session_reference=" not in rendered


def test_invalid_identity_and_request_shapes_fail_closed() -> None:
    with pytest.raises(ValueError, match="purpose"):
        _identity(purpose="not-approved")
    with pytest.raises(ValueError, match="reference_version"):
        _identity(reference_version=-1)
    with pytest.raises(ValueError, match="reviewed_at"):
        _identity(authorized_at=NOW)
    with pytest.raises(ValueError, match="session_expires_at"):
        _identity(session_expires_at=NOW + timedelta(hours=1))
    with pytest.raises(ValueError, match="owner_subject_id"):
        _request(owner_subject_id="")
    with pytest.raises(ValueError, match="scope"):
        _request(required_scopes=frozenset({""}))
