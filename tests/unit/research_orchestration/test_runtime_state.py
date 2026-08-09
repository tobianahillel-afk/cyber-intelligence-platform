from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy.orm import Session

from cip.modules.conditional_integrations.domain import (
    ApprovalState,
    ConditionalAccessMethod,
    ConditionalProviderKind,
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
from cip.modules.provider_onboarding.domain.models import OnboardingState
from cip.modules.provider_onboarding.infrastructure.models import ProviderOnboardingRecord
from cip.modules.research_orchestration.domain import (
    ResearchBudget,
    ResearchPlan,
    ResearchPlanState,
    ResearchRiskLevel,
    ResearchStep,
    ResearchStepMode,
)
from cip.modules.research_orchestration.infrastructure.runtime_state import (
    resolve_research_runtime,
)
from cip.modules.source_governance.domain.models import (
    AuthorizationStatus,
    DataCategory,
    SourceAuthorization,
    SourcePolicy,
    SourceStatus,
    SourceType,
)
from cip.modules.source_governance.infrastructure.persistence import sync_source_registry
from cip.modules.source_governance.infrastructure.registry import SourceRegistryEntry
from cip.modules.source_portfolio.application.service import sync_source_portfolio
from cip.modules.source_portfolio.domain.models import (
    AdapterCapabilityManifest,
    CatalogStatus,
    CollectionMode,
    SourceCatalogEntry,
)
from cip.modules.source_portfolio.infrastructure.models import SourceHealthRecord
from cip.shared.persistence.metadata import get_metadata
from cip.shared.persistence.session import create_database_engine, create_session_factory

NOW = datetime(2026, 8, 9, 16, 0, tzinfo=UTC)
PLAN_ID = UUID("cccccccc-cccc-4ccc-8ccc-cccccccccccc")
SOURCE_ID = "research-approved-source"
TOOL_ID = "approved-search-adapter"
TARGET = "https://research.example.test/results?q=acme"


def test_persisted_search_needs_no_external_runtime() -> None:
    session = _session()
    step = replace(_step(), mode=ResearchStepMode.PERSISTED_SEARCH, target_url=None)

    runtime = resolve_research_runtime(session, _plan(), step, now=NOW)

    assert runtime.source_authorized is False
    assert runtime.source_executable is False
    assert runtime.adapter_capability_present is False


def test_missing_source_fails_closed_for_automated_step() -> None:
    runtime = resolve_research_runtime(_session(), _plan(), _step(), now=NOW)

    assert runtime.source_authorized is False
    assert runtime.source_executable is False
    assert runtime.adapter_capability_present is False
    assert runtime.quota_remaining is None


def test_automated_runtime_uses_persisted_policy_portfolio_capability_and_quota() -> None:
    session = _ready_session()

    runtime = resolve_research_runtime(session, _plan(), _step(), now=NOW)

    assert runtime.source_authorized is True
    assert runtime.source_executable is True
    assert runtime.adapter_capability_present is True
    assert runtime.quota_remaining == 100


def test_wrong_host_is_not_authorized_even_when_runtime_is_executable() -> None:
    session = _ready_session()
    step = replace(_step(), target_url="https://other.example.test/results")

    runtime = resolve_research_runtime(session, _plan(), step, now=NOW)

    assert runtime.source_authorized is False
    assert runtime.source_executable is True
    assert runtime.adapter_capability_present is True


def test_capability_must_match_exact_tool_id() -> None:
    session = _ready_session()

    runtime = resolve_research_runtime(
        session,
        _plan(),
        replace(_step(), tool_id="different-adapter"),
        now=NOW,
    )

    assert runtime.adapter_capability_present is False


def test_missing_portfolio_and_zero_quota_fail_closed() -> None:
    source_only = _session()
    _persist_source(source_only)
    missing = resolve_research_runtime(source_only, _plan(), _step(), now=NOW)

    assert missing.source_authorized is True
    assert missing.source_executable is False
    assert missing.adapter_capability_present is False

    session = _ready_session(quota=0)
    exhausted = resolve_research_runtime(session, _plan(), _step(), now=NOW)
    assert exhausted.source_executable is False
    assert exhausted.quota_remaining == 0


def test_revoked_onboarding_blocks_source_authorization() -> None:
    session = _ready_session()
    session.add(_onboarding(OnboardingState.REVOKED))
    session.flush()

    runtime = resolve_research_runtime(session, _plan(), _step(), now=NOW)

    assert runtime.source_authorized is False


def test_conditional_provider_requires_persisted_access_method_mapping() -> None:
    session = _ready_session()
    _persist_conditional_approval(session)

    runtime = resolve_research_runtime(session, _plan(), _step(), now=NOW)

    assert runtime.source_authorized is False


def test_conditional_provider_matching_scope_can_authorize() -> None:
    session = _ready_session(
        conditional_access_method=ConditionalAccessMethod.OFFICIAL_API.value
    )
    _persist_conditional_approval(session)

    runtime = resolve_research_runtime(session, _plan(), _step(), now=NOW)

    assert runtime.source_authorized is True


def test_conditional_provider_scope_or_terms_mismatch_blocks() -> None:
    session = _ready_session(
        conditional_access_method=ConditionalAccessMethod.OFFICIAL_API.value
    )
    _persist_conditional_approval(
        session,
        replace(
            _approval_dossier(),
            approved_purposes=frozenset({"different-purpose"}),
        ),
    )

    wrong_purpose = resolve_research_runtime(session, _plan(), _step(), now=NOW)
    assert wrong_purpose.source_authorized is False

    session = _ready_session(
        conditional_access_method=ConditionalAccessMethod.OFFICIAL_API.value
    )
    _persist_conditional_approval(
        session,
        replace(
            _approval_dossier(),
            state=ApprovalState.PENDING_REVIEW,
            terms_state=TermsReviewState.CHANGED,
        ),
    )
    changed_terms = resolve_research_runtime(session, _plan(), _step(), now=NOW)
    assert changed_terms.source_authorized is False


def test_conditional_provider_pause_blocks_automated_authorization() -> None:
    session = _ready_session(
        conditional_access_method=ConditionalAccessMethod.OFFICIAL_API.value
    )
    _persist_conditional_approval(session)
    before_pause = resolve_research_runtime(session, _plan(), _step(), now=NOW)
    assert before_pause.source_authorized is True

    apply_persisted_control_decision(
        session,
        ProviderControlDecision(
            source_id=SOURCE_ID,
            action=ProviderControlAction.PAUSE,
            actor="research-admin@example.test",
            reason="terms review",
            decided_at=NOW + timedelta(minutes=1),
        ),
        now=NOW + timedelta(minutes=1),
    )

    runtime = resolve_research_runtime(
        session,
        _plan(),
        _step(),
        now=NOW + timedelta(minutes=2),
    )

    assert runtime.source_authorized is False


def test_manual_link_requires_governed_search_provider_and_exact_host() -> None:
    session = _session()
    _persist_source(
        session,
        source_type=SourceType.SEARCH_PROVIDER,
        status=SourceStatus.CONDITIONAL,
    )
    manual = replace(_step(), mode=ResearchStepMode.MANUAL_LINK)

    allowed = resolve_research_runtime(session, _plan(), manual, now=NOW)
    wrong_host = resolve_research_runtime(
        session,
        _plan(),
        replace(manual, target_url="https://other.example.test/results"),
        now=NOW,
    )

    assert allowed.manual_link_allowed is True
    assert wrong_host.manual_link_allowed is False


def test_manual_link_rejects_quarantined_or_browser_source() -> None:
    session = _session()
    _persist_source(
        session,
        source_type=SourceType.BROWSER,
        status=SourceStatus.QUARANTINED,
    )

    runtime = resolve_research_runtime(
        session,
        _plan(),
        replace(_step(), mode=ResearchStepMode.MANUAL_LINK),
        now=NOW,
    )

    assert runtime.manual_link_allowed is False


def test_approved_ingestion_accepts_only_validated_internal_path() -> None:
    approved = replace(
        _step(),
        mode=ResearchStepMode.APPROVED_INGESTION,
        target_url=None,
        ingestion_path_id="existing-evidence-reference",
    )
    unapproved = replace(approved, ingestion_path_id="arbitrary-import")

    approved_runtime = resolve_research_runtime(_session(), _plan(), approved, now=NOW)
    denied_runtime = resolve_research_runtime(_session(), _plan(), unapproved, now=NOW)

    assert approved_runtime.ingestion_path_approved is True
    assert denied_runtime.ingestion_path_approved is False


def _session() -> Session:
    engine = create_database_engine("sqlite+pysqlite:///:memory:")
    get_metadata().create_all(engine)
    return create_session_factory(engine)()


def _ready_session(
    *,
    quota: int = 100,
    conditional_access_method: str | None = None,
) -> Session:
    session = _session()
    _persist_source(session)
    sync_source_portfolio(
        session,
        (_portfolio(conditional_access_method=conditional_access_method),),
        now=NOW,
    )
    health = session.get(SourceHealthRecord, SOURCE_ID)
    assert health is not None
    health.quota_remaining = quota
    health.last_success_at = NOW
    session.flush()
    return session


def _persist_source(
    session: Session,
    *,
    source_type: SourceType = SourceType.API,
    status: SourceStatus = SourceStatus.ENABLED,
) -> None:
    policy = SourcePolicy(
        id=SOURCE_ID,
        name="Research approved source",
        base_url="https://research.example.test",
        status=status,
        source_type=source_type,
        owner="Research provider",
        allowed_data_categories=frozenset({DataCategory.ORGANIZATION_METADATA}),
        prohibited_data_categories=frozenset({DataCategory.PRIVATE_PERSONAL_DATA}),
        terms_url="https://research.example.test/terms",
        retention_days=90,
        raw_content_storage=False,
        human_review_required=True,
    )
    authorization = SourceAuthorization(
        status=AuthorizationStatus.APPROVED,
        document_reference="approval:research-source",
        reviewed_at=NOW - timedelta(days=1),
        approved_hosts=frozenset({"research.example.test"}),
        approved_path_prefixes=("/results",),
        approved_purposes=frozenset({"organization-research"}),
        automated_collection_allowed=True,
        raw_storage_allowed=False,
    )
    sync_source_registry(session, (SourceRegistryEntry(policy, authorization, {}),))
    session.flush()


def _portfolio(*, conditional_access_method: str | None) -> SourceCatalogEntry:
    capability = AdapterCapabilityManifest(
        source_id=SOURCE_ID,
        adapter_id=TOOL_ID,
        adapter_version="1",
        provider_schema_version="research-v1",
        modes=frozenset({CollectionMode.PRIORITY_REFRESH}),
        canonical_output_types=("research_result",),
        max_page_size=25,
        cost_per_request=0.0,
    )
    metadata: dict[str, object] = {}
    if conditional_access_method is not None:
        metadata["conditional_access_method"] = conditional_access_method
    return SourceCatalogEntry(
        source_id=SOURCE_ID,
        display_name="Research approved source",
        canonical_url="https://research.example.test",
        category="research",
        status=CatalogStatus.EXECUTABLE,
        freshness_max_age_seconds=3600,
        commercial_use_cases=("organization_research",),
        adapter=capability,
        monthly_cost_limit=100.0,
        metadata=metadata,
    )


def _onboarding(state: OnboardingState) -> ProviderOnboardingRecord:
    return ProviderOnboardingRecord(
        source_id=SOURCE_ID,
        display_name="Research provider",
        auth_mode="api_key",
        state=state.value,
        documentation_url="https://research.example.test/docs",
        signup_url=None,
        console_url=None,
        required_secret_names=[],
        human_actions=[],
        automatic_onboarding=False,
        secret_references={},
        blocked_reason=None,
        last_verified_at=NOW,
        expires_at=None,
        last_error_code=None,
        last_error_message=None,
        created_at=NOW,
        updated_at=NOW,
    )


def _persist_conditional_approval(
    session: Session,
    dossier: ProviderApprovalDossier | None = None,
) -> None:
    persist_provider_approval(
        session,
        dossier or _approval_dossier(),
        actor="research-admin@example.test",
        change_reason="approved controlled provider",
        now=NOW,
    )


def _approval_dossier() -> ProviderApprovalDossier:
    return ProviderApprovalDossier(
        source_id=SOURCE_ID,
        provider_kind=ConditionalProviderKind.OTHER,
        access_method=ConditionalAccessMethod.OFFICIAL_API,
        state=ApprovalState.APPROVED,
        authorization_document_reference="approval:conditional-research",
        licence_reference=None,
        terms_reference="terms:conditional-research",
        terms_state=TermsReviewState.CURRENT,
        approved_purposes=frozenset({"organization-research"}),
        approved_data_categories=frozenset({DataCategory.ORGANIZATION_METADATA}),
        retention_days=90,
        automated_collection_allowed=True,
        reviewed_at=NOW,
        expires_at=NOW + timedelta(days=30),
    )


def _plan() -> ResearchPlan:
    return ResearchPlan(
        plan_id=PLAN_ID,
        question="What evidence supports Acme's security priorities?",
        purpose="organization-research",
        data_category=DataCategory.ORGANIZATION_METADATA,
        state=ResearchPlanState.APPROVED,
        budget=ResearchBudget(10, 3, 20.0, 5.0),
        allowed_source_ids=frozenset({SOURCE_ID}),
        allowed_tool_ids=frozenset({TOOL_ID, "different-adapter"}),
        approved_step_keys=frozenset({"step-1"}),
        allowed_hosts=frozenset({"research.example.test", "other.example.test"}),
        allowed_path_prefixes=("/results",),
        max_risk_level=ResearchRiskLevel.MEDIUM,
        expires_at=NOW + timedelta(hours=4),
    )


def _step() -> ResearchStep:
    return ResearchStep(
        step_key="step-1",
        sequence=1,
        source_id=SOURCE_ID,
        tool_id=TOOL_ID,
        mode=ResearchStepMode.AUTOMATED_ADAPTER,
        purpose="organization-research",
        data_category=DataCategory.ORGANIZATION_METADATA,
        estimated_cost=1.0,
        risk_level=ResearchRiskLevel.LOW,
        target_url=TARGET,
        query_text="security priorities",
    )
