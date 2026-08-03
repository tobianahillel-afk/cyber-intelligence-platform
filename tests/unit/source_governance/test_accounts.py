from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from cip.modules.source_governance.domain.accounts import (
    AccountDecisionReason,
    SourceAccount,
    SourceAccountAuthMode,
    SourceAccountStatus,
)

NOW = datetime(2026, 8, 3, 16, 0, tzinfo=UTC)
LATER = NOW + timedelta(days=30)


def active_account(**changes: object) -> SourceAccount:
    values: dict[str, object] = {
        "source_id": "linkedin-official-api",
        "external_reference": "organization-account-1",
        "auth_mode": SourceAccountAuthMode.OAUTH,
        "status": SourceAccountStatus.ACTIVE,
        "authorization_document_reference": "AUTH-2026-001",
        "approved_purposes": frozenset({"professional-research"}),
        "created_at": NOW,
        "verified_at": NOW,
        "expires_at": LATER,
    }
    values.update(changes)
    return SourceAccount(**values)  # type: ignore[arg-type]


def test_active_account_allows_approved_purpose() -> None:
    decision = active_account().evaluate_use("professional-research", now=NOW)

    assert decision.allowed is True
    assert decision.reason is AccountDecisionReason.ALLOWED


def test_non_active_account_is_denied() -> None:
    account = active_account(status=SourceAccountStatus.MFA_REQUIRED)

    assert account.evaluate_use("professional-research", now=NOW).reason is (
        AccountDecisionReason.NOT_ACTIVE
    )


def test_expired_account_is_denied() -> None:
    account = active_account(expires_at=NOW + timedelta(seconds=1))

    assert account.evaluate_use("professional-research", now=LATER).reason is (
        AccountDecisionReason.EXPIRED
    )


def test_unapproved_purpose_is_denied() -> None:
    decision = active_account().evaluate_use("bulk-profile-scraping", now=NOW)

    assert decision.reason is AccountDecisionReason.PURPOSE_NOT_ALLOWED


def test_pending_account_can_be_verified_and_activated() -> None:
    pending = SourceAccount(
        source_id="provider",
        external_reference="account-1",
        auth_mode=SourceAccountAuthMode.SERVICE_ACCOUNT,
        status=SourceAccountStatus.PENDING_VERIFICATION,
        authorization_document_reference="AUTH-1",
        approved_purposes=frozenset({"official-feed"}),
        created_at=NOW,
    )

    active = pending.transition(SourceAccountStatus.ACTIVE, at=NOW, verified=True)

    assert active.status is SourceAccountStatus.ACTIVE
    assert active.verified_at == NOW
    assert active.id == pending.id


def test_invalid_transition_is_rejected() -> None:
    account = active_account()

    with pytest.raises(ValueError, match="invalid account transition"):
        account.transition(SourceAccountStatus.PENDING_VERIFICATION, at=NOW)


def test_revoked_account_has_no_outgoing_transition() -> None:
    revoked = active_account(status=SourceAccountStatus.REVOKED)

    with pytest.raises(ValueError, match="invalid account transition"):
        revoked.transition(SourceAccountStatus.ACTIVE, at=NOW, verified=True)


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"source_id": ""}, "source_id"),
        ({"external_reference": ""}, "external_reference"),
        ({"authorization_document_reference": None}, "authorization document"),
        ({"verified_at": None}, "verified_at"),
        ({"created_at": datetime(2026, 8, 3)}, "timezone-aware"),
        ({"expires_at": NOW}, "later than created_at"),
    ],
)
def test_account_validation(changes: dict[str, object], message: str) -> None:
    with pytest.raises(ValueError, match=message):
        active_account(**changes)


def test_use_rejects_naive_current_time() -> None:
    with pytest.raises(ValueError, match="now must be timezone-aware"):
        active_account().evaluate_use(
            "professional-research",
            now=datetime(2026, 8, 3),
        )


def test_transition_rejects_naive_timestamp() -> None:
    pending = SourceAccount(
        source_id="provider",
        external_reference="account-1",
        auth_mode=SourceAccountAuthMode.API_KEY,
        status=SourceAccountStatus.PENDING_VERIFICATION,
        authorization_document_reference="AUTH-1",
        approved_purposes=frozenset({"feed"}),
        created_at=NOW,
    )

    with pytest.raises(ValueError, match="at must be timezone-aware"):
        pending.transition(
            SourceAccountStatus.ACTIVE,
            at=datetime(2026, 8, 3),
            verified=True,
        )
