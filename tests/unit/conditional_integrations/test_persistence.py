from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from cip.modules.conditional_integrations.domain import (
    ApprovalState,
    ConditionalAccessMethod,
    ConditionalBlockReason,
    ConditionalExecutionRequest,
    ConditionalProviderKind,
    ConditionalRuntimeDependencies,
    ProviderApprovalDossier,
    ProviderControlAction,
    ProviderControlDecision,
    TermsReviewState,
)
from cip.modules.conditional_integrations.infrastructure.approval_persistence import (
    persist_provider_approval,
)
from cip.modules.conditional_integrations.infrastructure.control_persistence import (
    apply_persisted_control_decision,
)
from cip.modules.conditional_integrations.infrastructure.execution_audit import (
    evaluate_and_audit_conditional_execution,
)
from cip.modules.conditional_integrations.infrastructure.models import (
    ConditionalExecutionDecisionRecord,
    ConditionalProviderApprovalRecord,
    ConditionalProviderApprovalRevisionRecord,
    ConditionalProviderControlDecisionRecord,
)
from cip.modules.provider_onboarding.domain.models import OnboardingState
from cip.modules.source_governance.domain.models import DataCategory
from cip.shared.persistence.metadata import get_metadata
from cip.shared.persistence.session import create_database_engine, create_session_factory

NOW = datetime(2026, 8, 9, 12, 0, tzinfo=UTC)
ACTOR = "provider-admin@example.test"


def test_dossier_replay_is_idempotent_and_changes_append_revision() -> None:
    session = _session()
    dossier = _approved_dossier()

    first = _persist(session, dossier, now=NOW, reason="initial approval")
    _persist(
        session,
        dossier,
        now=NOW + timedelta(minutes=1),
        reason="idempotent replay",
    )

    assert _count(session, ConditionalProviderApprovalRecord) == 1
    assert _count(session, ConditionalProviderApprovalRevisionRecord) == 1

    changed = replace(
        dossier,
        approved_fields=dossier.approved_fields | {"public_team"},
        reviewed_at=NOW + timedelta(minutes=2),
    )
    current = _persist(
        session,
        changed,
        now=NOW + timedelta(minutes=2),
        reason="approve public team field",
    )

    revisions = tuple(
        session.scalars(
            select(ConditionalProviderApprovalRevisionRecord).order_by(
                ConditionalProviderApprovalRevisionRecord.created_at
            )
        )
    )
    assert current.id == first.id
    assert set(current.approved_fields) == {
        "organization",
        "public_professional_role",
        "public_team",
    }
    assert len(revisions) == 2
    assert revisions[0].actor == ACTOR
    assert revisions[0].change_reason == "initial approval"
    assert revisions[1].actor == ACTOR
    assert revisions[1].change_reason == "approve public team field"


def test_revocation_preserves_approved_revision_history() -> None:
    session = _session()
    dossier = _approved_dossier()
    _persist(session, dossier, now=NOW, reason="initial approval")
    revoked = replace(
        dossier,
        state=ApprovalState.REVOKED,
        revoked_at=NOW + timedelta(hours=1),
    )

    current = _persist(
        session,
        revoked,
        now=NOW + timedelta(hours=1),
        reason="authorization withdrawn",
    )
    revisions = tuple(
        session.scalars(
            select(ConditionalProviderApprovalRevisionRecord).order_by(
                ConditionalProviderApprovalRevisionRecord.created_at
            )
        )
    )

    assert current.state == ApprovalState.REVOKED.value
    assert tuple(record.state for record in revisions) == (
        ApprovalState.APPROVED.value,
        ApprovalState.REVOKED.value,
    )
    assert revisions[-1].change_reason == "authorization withdrawn"


def test_provider_kind_cannot_mutate_for_existing_source() -> None:
    session = _session()
    dossier = _approved_dossier()
    _persist(session, dossier, now=NOW, reason="initial approval")

    with pytest.raises(ValueError, match="provider_kind"):
        _persist(
            session,
            replace(dossier, provider_kind=ConditionalProviderKind.DISCORD),
            now=NOW + timedelta(minutes=1),
            reason="invalid provider mutation",
        )


def test_control_history_is_append_only_and_old_replay_is_idempotent() -> None:
    session = _session()
    _persist(session, _approved_dossier(), now=NOW, reason="initial approval")
    pause = _control_decision(
        ProviderControlAction.PAUSE,
        at=NOW + timedelta(minutes=1),
        reason="provider maintenance",
    )
    resume = _control_decision(
        ProviderControlAction.RESUME,
        at=NOW + timedelta(minutes=2),
        reason="maintenance complete",
    )

    paused = apply_persisted_control_decision(
        session,
        pause,
        now=NOW + timedelta(minutes=1),
    )
    assert paused.paused is True
    assert paused.paused_reason == "provider maintenance"

    resumed = apply_persisted_control_decision(
        session,
        resume,
        now=NOW + timedelta(minutes=2),
    )
    assert resumed.paused is False
    assert resumed.paused_reason is None

    replayed = apply_persisted_control_decision(
        session,
        pause,
        now=NOW + timedelta(minutes=3),
    )
    assert replayed.paused is False
    assert _count(session, ConditionalProviderControlDecisionRecord) == 2


def test_new_backdated_control_decision_is_rejected() -> None:
    session = _session()
    _persist(session, _approved_dossier(), now=NOW, reason="initial approval")
    apply_persisted_control_decision(
        session,
        _control_decision(
            ProviderControlAction.PAUSE,
            at=NOW + timedelta(minutes=2),
            reason="pause",
        ),
        now=NOW + timedelta(minutes=2),
    )

    with pytest.raises(ValueError, match="predate"):
        apply_persisted_control_decision(
            session,
            _control_decision(
                ProviderControlAction.ACTIVATE_KILL_SWITCH,
                at=NOW + timedelta(minutes=1),
                reason="older distinct decision",
            ),
            now=NOW + timedelta(minutes=3),
        )


def test_pause_and_kill_switch_block_and_are_audited_idempotently() -> None:
    session = _session()
    _persist(session, _approved_dossier(), now=NOW, reason="initial approval")
    request = _request()
    dependencies = _ready_dependencies()

    allowed = evaluate_and_audit_conditional_execution(
        session,
        request,
        dependencies,
        now=NOW + timedelta(seconds=1),
    )
    evaluate_and_audit_conditional_execution(
        session,
        request,
        dependencies,
        now=NOW + timedelta(seconds=1),
    )
    assert allowed.allowed is True
    assert _count(session, ConditionalExecutionDecisionRecord) == 1

    apply_persisted_control_decision(
        session,
        _control_decision(
            ProviderControlAction.PAUSE,
            at=NOW + timedelta(minutes=1),
            reason="terms review",
        ),
        now=NOW + timedelta(minutes=1),
    )
    paused = evaluate_and_audit_conditional_execution(
        session,
        request,
        dependencies,
        now=NOW + timedelta(minutes=1, seconds=1),
    )
    assert paused.allowed is False
    assert ConditionalBlockReason.PROVIDER_PAUSED in paused.reasons

    apply_persisted_control_decision(
        session,
        _control_decision(
            ProviderControlAction.ACTIVATE_KILL_SWITCH,
            at=NOW + timedelta(minutes=2),
            reason="emergency stop",
        ),
        now=NOW + timedelta(minutes=2),
    )
    stopped = evaluate_and_audit_conditional_execution(
        session,
        request,
        dependencies,
        now=NOW + timedelta(minutes=2, seconds=1),
    )
    assert ConditionalBlockReason.PROVIDER_PAUSED in stopped.reasons
    assert ConditionalBlockReason.KILL_SWITCH_ACTIVE in stopped.reasons
    assert _count(session, ConditionalExecutionDecisionRecord) == 3


def test_conditional_tables_do_not_model_raw_secrets_or_browser_sessions() -> None:
    metadata = get_metadata()
    table_names = (
        "conditional_provider_approvals",
        "conditional_provider_approval_revisions",
        "conditional_provider_runtime_controls",
        "conditional_provider_control_decisions",
        "conditional_execution_decisions",
    )
    forbidden_fragments = ("password", "token", "cookie", "session_value", "secret_value")

    for table_name in table_names:
        column_names = {column.name for column in metadata.tables[table_name].columns}
        assert all(
            fragment not in column_name
            for column_name in column_names
            for fragment in forbidden_fragments
        )


def _session() -> Session:
    engine = create_database_engine("sqlite+pysqlite:///:memory:")
    get_metadata().create_all(engine)
    return create_session_factory(engine)()


def _count(session: Session, model: type[object]) -> int:
    return int(session.scalar(select(func.count()).select_from(model)) or 0)


def _persist(
    session: Session,
    dossier: ProviderApprovalDossier,
    *,
    now: datetime,
    reason: str,
) -> ConditionalProviderApprovalRecord:
    return persist_provider_approval(
        session,
        dossier,
        actor=ACTOR,
        change_reason=reason,
        now=now,
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
        reviewed_at=NOW,
        review_due_at=NOW + timedelta(days=90),
        expires_at=NOW + timedelta(days=180),
    )


def _request() -> ConditionalExecutionRequest:
    return ConditionalExecutionRequest(
        source_id="linkedin-approved-api",
        access_method=ConditionalAccessMethod.OFFICIAL_API,
        purpose="professional-context",
        data_category=DataCategory.PROFESSIONAL_CONTACT,
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
        adapter_capability_present=True,
        quota_remaining=100,
        monthly_cost_used=10.0,
        monthly_cost_limit=100.0,
    )


def _control_decision(
    action: ProviderControlAction,
    *,
    at: datetime,
    reason: str,
) -> ProviderControlDecision:
    return ProviderControlDecision(
        source_id="linkedin-approved-api",
        action=action,
        actor=ACTOR,
        reason=reason,
        decided_at=at,
    )
