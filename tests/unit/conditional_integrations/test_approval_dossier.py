from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest

from cip.modules.conditional_integrations.domain import (
    ApprovalState,
    ConditionalAccessMethod,
    ConditionalBlockReason,
    ConditionalExecutionRequest,
    ConditionalProviderKind,
    ConditionalRuntimeDependencies,
    ProviderApprovalDossier,
    TermsReviewState,
    evaluate_conditional_execution,
    provider_method_is_permitted,
)
from cip.modules.provider_onboarding.domain.models import OnboardingState
from cip.modules.source_governance.domain.models import DataCategory

NOW = datetime(2026, 8, 9, 11, 0, tzinfo=UTC)
TARGET_URL = "https://api.linkedin.example.test/organizations/123"


def test_approved_linkedin_official_api_can_pass_all_four_gates() -> None:
    decision = evaluate_conditional_execution(
        _approved_dossier(),
        _request(),
        _ready_dependencies(),
        now=NOW,
    )

    assert decision.allowed is True
    assert decision.reasons == (ConditionalBlockReason.ALLOWED,)


def test_linkedin_rejects_non_official_non_licensed_access_method() -> None:
    dossier = replace(
        _approved_dossier(),
        access_method=ConditionalAccessMethod.CUSTOMER_PROVIDED_ACCESS,
        licence_reference="contract:linkedin-customer-access",
    )
    request = replace(
        _request(),
        access_method=ConditionalAccessMethod.CUSTOMER_PROVIDED_ACCESS,
    )

    decision = evaluate_conditional_execution(
        dossier,
        request,
        _ready_dependencies(),
        now=NOW,
    )

    assert decision.allowed is False
    assert ConditionalBlockReason.PROVIDER_METHOD_NOT_PERMITTED in decision.reasons


def test_discord_requires_admin_connector_or_authorized_export() -> None:
    assert provider_method_is_permitted(
        ConditionalProviderKind.DISCORD,
        ConditionalAccessMethod.ADMIN_INSTALLED_CONNECTOR,
    )
    assert provider_method_is_permitted(
        ConditionalProviderKind.DISCORD,
        ConditionalAccessMethod.AUTHORIZED_EXPORT,
    )
    assert not provider_method_is_permitted(
        ConditionalProviderKind.DISCORD,
        ConditionalAccessMethod.OFFICIAL_API,
    )


def test_brixhub_has_no_executable_method_before_specific_review() -> None:
    for method in ConditionalAccessMethod:
        assert not provider_method_is_permitted(ConditionalProviderKind.BRIXHUB, method)


def test_scope_field_purpose_category_retention_and_account_are_exact() -> None:
    request = replace(
        _request(),
        purpose="sales-profiling",
        data_category=DataCategory.PRIVATE_PERSONAL_DATA,
        requested_scopes=frozenset({"organizations.read", "people.private.read"}),
        requested_fields=frozenset({"name", "private_email"}),
        retention_days=366,
        account_reference="account:other",
    )

    decision = evaluate_conditional_execution(
        _approved_dossier(),
        request,
        _ready_dependencies(),
        now=NOW,
    )

    assert decision.allowed is False
    assert set(decision.reasons) >= {
        ConditionalBlockReason.SCOPE_NOT_APPROVED,
        ConditionalBlockReason.FIELD_NOT_APPROVED,
        ConditionalBlockReason.PURPOSE_NOT_APPROVED,
        ConditionalBlockReason.CATEGORY_NOT_APPROVED,
        ConditionalBlockReason.RETENTION_EXCEEDS_APPROVAL,
        ConditionalBlockReason.ACCOUNT_MISMATCH,
    }


def test_source_mismatch_is_distinct_from_account_mismatch() -> None:
    decision = evaluate_conditional_execution(
        _approved_dossier(),
        replace(_request(), source_id="different-source"),
        _ready_dependencies(),
        now=NOW,
    )

    assert ConditionalBlockReason.SOURCE_MISMATCH in decision.reasons
    assert ConditionalBlockReason.ACCOUNT_MISMATCH not in decision.reasons


@pytest.mark.parametrize(
    ("state", "updates", "expected"),
    [
        (ApprovalState.DRAFT, {}, ConditionalBlockReason.DOSSIER_NOT_APPROVED),
        (
            ApprovalState.PENDING_REVIEW,
            {},
            ConditionalBlockReason.DOSSIER_NOT_APPROVED,
        ),
        (ApprovalState.EXPIRED, {}, ConditionalBlockReason.DOSSIER_EXPIRED),
        (
            ApprovalState.REVOKED,
            {"revoked_at": NOW},
            ConditionalBlockReason.DOSSIER_REVOKED,
        ),
        (
            ApprovalState.PAUSED,
            {"paused_reason": "provider terms changed"},
            ConditionalBlockReason.DOSSIER_PAUSED,
        ),
    ],
)
def test_non_approved_dossier_states_fail_closed(
    state: ApprovalState,
    updates: dict[str, object],
    expected: ConditionalBlockReason,
) -> None:
    dossier = replace(_approved_dossier(), state=state, **updates)

    decision = evaluate_conditional_execution(
        dossier,
        _request(),
        _ready_dependencies(),
        now=NOW,
    )

    assert decision.allowed is False
    assert expected in decision.reasons


def test_expiry_and_terms_review_due_block_even_if_state_says_approved() -> None:
    dossier = replace(
        _approved_dossier(),
        expires_at=NOW,
        review_due_at=NOW,
    )

    decision = evaluate_conditional_execution(
        dossier,
        _request(),
        _ready_dependencies(),
        now=NOW,
    )

    assert ConditionalBlockReason.DOSSIER_EXPIRED in decision.reasons
    assert ConditionalBlockReason.TERMS_REVIEW_REQUIRED in decision.reasons


def test_terms_change_blocks_execution() -> None:
    dossier = replace(
        _approved_dossier(),
        state=ApprovalState.PENDING_REVIEW,
        terms_state=TermsReviewState.CHANGED,
    )

    decision = evaluate_conditional_execution(
        dossier,
        _request(),
        _ready_dependencies(),
        now=NOW,
    )

    assert ConditionalBlockReason.TERMS_REVIEW_REQUIRED in decision.reasons


def test_runtime_dependencies_fail_closed_together() -> None:
    dependencies = ConditionalRuntimeDependencies(
        onboarding_state=OnboardingState.REVOKED,
        source_policy_allowed=False,
        source_portfolio_allowed=False,
        adapter_capability_present=False,
        kill_switch_active=True,
        quota_remaining=0,
        monthly_cost_used=100.0,
        monthly_cost_limit=100.0,
    )

    decision = evaluate_conditional_execution(
        _approved_dossier(),
        _request(),
        dependencies,
        now=NOW,
    )

    assert set(decision.reasons) >= {
        ConditionalBlockReason.ONBOARDING_NOT_READY,
        ConditionalBlockReason.SOURCE_POLICY_DENIED,
        ConditionalBlockReason.SOURCE_PORTFOLIO_NOT_EXECUTABLE,
        ConditionalBlockReason.CAPABILITY_MISSING,
        ConditionalBlockReason.KILL_SWITCH_ACTIVE,
        ConditionalBlockReason.QUOTA_EXHAUSTED,
        ConditionalBlockReason.COST_BUDGET_EXHAUSTED,
    }


def test_authorized_export_does_not_require_connected_onboarding() -> None:
    dossier = ProviderApprovalDossier(
        source_id="discord-approved-export",
        provider_kind=ConditionalProviderKind.DISCORD,
        access_method=ConditionalAccessMethod.AUTHORIZED_EXPORT,
        state=ApprovalState.APPROVED,
        authorization_document_reference="approval:discord-export",
        licence_reference=None,
        terms_reference="terms:discord-export-review",
        terms_state=TermsReviewState.CURRENT,
        approved_fields=frozenset({"public_member_role"}),
        approved_purposes=frozenset({"professional-context"}),
        approved_data_categories=frozenset({DataCategory.PROFESSIONAL_CONTACT}),
        retention_days=90,
        automated_collection_allowed=False,
        reviewed_at=NOW - timedelta(days=1),
    )
    request = ConditionalExecutionRequest(
        source_id=dossier.source_id,
        access_method=dossier.access_method,
        purpose="professional-context",
        data_category=DataCategory.PROFESSIONAL_CONTACT,
        target_url="https://discord.example.test/exports/public-members.csv",
        requested_fields=frozenset({"public_member_role"}),
        retention_days=30,
        automated=False,
    )
    dependencies = replace(
        _ready_dependencies(),
        onboarding_state=OnboardingState.NOT_REQUIRED,
    )

    assert evaluate_conditional_execution(dossier, request, dependencies, now=NOW).allowed


def test_approved_dossier_requires_positive_review_artifacts() -> None:
    with pytest.raises(ValueError, match="authorization document"):
        replace(_approved_dossier(), authorization_document_reference=None)
    with pytest.raises(ValueError, match="current terms"):
        replace(_approved_dossier(), terms_state=TermsReviewState.REVIEW_REQUIRED)
    with pytest.raises(ValueError, match="retention"):
        replace(_approved_dossier(), retention_days=None)


def test_licensed_access_requires_licence_reference() -> None:
    with pytest.raises(ValueError, match="licence reference"):
        replace(
            _approved_dossier(),
            access_method=ConditionalAccessMethod.LICENSED_API,
            licence_reference=None,
        )


def _approved_dossier() -> ProviderApprovalDossier:
    return ProviderApprovalDossier(
        source_id="linkedin-approved-api",
        provider_kind=ConditionalProviderKind.LINKEDIN,
        access_method=ConditionalAccessMethod.OFFICIAL_API,
        state=ApprovalState.APPROVED,
        authorization_document_reference="approval:linkedin-2026-08",
        licence_reference=None,
        terms_reference="terms:linkedin-reviewed-2026-08",
        terms_state=TermsReviewState.CURRENT,
        approved_scopes=frozenset({"organizations.read"}),
        approved_fields=frozenset({"organization", "public_professional_role"}),
        approved_purposes=frozenset({"professional-context"}),
        approved_data_categories=frozenset({DataCategory.PROFESSIONAL_CONTACT}),
        retention_days=365,
        automated_collection_allowed=True,
        account_reference="account:linkedin-cip",
        reviewed_at=NOW - timedelta(days=1),
        review_due_at=NOW + timedelta(days=90),
        expires_at=NOW + timedelta(days=180),
    )


def _request() -> ConditionalExecutionRequest:
    return ConditionalExecutionRequest(
        source_id="linkedin-approved-api",
        access_method=ConditionalAccessMethod.OFFICIAL_API,
        purpose="professional-context",
        data_category=DataCategory.PROFESSIONAL_CONTACT,
        target_url=TARGET_URL,
        requested_scopes=frozenset({"organizations.read"}),
        requested_fields=frozenset({"organization", "public_professional_role"}),
        retention_days=180,
        automated=True,
        account_reference="account:linkedin-cip",
    )


def _ready_dependencies() -> ConditionalRuntimeDependencies:
    return ConditionalRuntimeDependencies(
        onboarding_state=OnboardingState.CONNECTED,
        source_policy_allowed=True,
        source_portfolio_allowed=True,
        adapter_capability_present=True,
        quota_remaining=100,
        monthly_cost_used=10.0,
        monthly_cost_limit=100.0,
    )
