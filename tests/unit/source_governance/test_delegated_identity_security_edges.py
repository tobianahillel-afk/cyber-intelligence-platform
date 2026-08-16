from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from cip.modules.source_governance.application import delegated_identity_service
from cip.modules.source_governance.domain.accounts import (
    SourceAccount,
    SourceAccountAuthMode,
    SourceAccountStatus,
)
from cip.modules.source_governance.domain.delegated_browser_identity import (
    DelegatedBrowserIdentity,
    DelegatedOwnerKind,
)

NOW = datetime(2026, 8, 16, 21, 30, tzinfo=UTC)


class _FailIfCalledResolver:
    def is_available(self, _reference) -> bool:
        pytest.fail("resolver must not be consulted for an unrequested reference")


def _identity() -> DelegatedBrowserIdentity:
    account = SourceAccount(
        source_id="provider-browser",
        external_reference="provider-account-1",
        auth_mode=SourceAccountAuthMode.INTERACTIVE_SESSION,
        status=SourceAccountStatus.PENDING_VERIFICATION,
        authorization_document_reference="AUTH-L15-1",
        approved_purposes=frozenset({"authorized-provider-research"}),
        created_at=NOW,
        expires_at=NOW + timedelta(days=30),
    )
    return DelegatedBrowserIdentity(
        account=account,
        tenant_id=uuid4(),
        owner_kind=DelegatedOwnerKind.USER,
        owner_subject_id="user-123",
        purpose="authorized-provider-research",
        approved_scopes=frozenset({"profile.read"}),
        created_at=NOW,
    )


def test_unrequested_reference_is_not_returned_or_resolved() -> None:
    assert (
        delegated_identity_service._required_available(
            "vault://cip/provider/login",
            False,
            _FailIfCalledResolver(),
        )
        is None
    )


def test_references_cannot_be_attached_before_authorization() -> None:
    identity = _identity()
    with pytest.raises(ValueError, match="only active"):
        identity.attach_secret_reference(
            "vault://cip/provider/login",
            at=NOW + timedelta(minutes=1),
        )
    with pytest.raises(ValueError, match="only active"):
        identity.attach_session_reference(
            "vault://cip/provider/session",
            at=NOW + timedelta(minutes=1),
        )


def test_session_reference_expiry_must_follow_rotation_time() -> None:
    identity = _identity().authorize(reviewed_at=NOW + timedelta(minutes=1))
    with pytest.raises(ValueError, match="session expiry"):
        identity.attach_session_reference(
            "vault://cip/provider/session",
            at=NOW + timedelta(minutes=2),
            expires_at=NOW + timedelta(minutes=2),
        )


def test_revoked_identity_cannot_renew_or_mark_used() -> None:
    identity = _identity().authorize(reviewed_at=NOW + timedelta(minutes=1))
    revoked = identity.revoke(at=NOW + timedelta(minutes=2))
    with pytest.raises(ValueError, match="cannot be renewed"):
        revoked.renew(
            expires_at=NOW + timedelta(days=60),
            at=NOW + timedelta(days=20),
        )
    with pytest.raises(ValueError, match="only active"):
        revoked.mark_used(at=NOW + timedelta(minutes=3))
