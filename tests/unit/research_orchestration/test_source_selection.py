from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from cip.modules.research_orchestration.domain import ResearchStepMode
from cip.modules.research_orchestration.infrastructure.source_selection import (
    select_ranked_research_sources,
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

NOW = datetime(2026, 8, 9, 17, 30, tzinfo=UTC)
PURPOSE = "organization-research"
CATEGORY = DataCategory.ORGANIZATION_METADATA


def test_persisted_evidence_is_always_first_and_zero_cost() -> None:
    candidates = select_ranked_research_sources(
        _session(),
        purpose=PURPOSE,
        data_category=CATEGORY,
        now=NOW,
    )

    assert candidates[0].mode is ResearchStepMode.PERSISTED_SEARCH
    assert candidates[0].source_id == "persisted-evidence"
    assert candidates[0].estimated_cost == 0


def test_authorized_executable_adapter_is_ranked_after_persisted_search() -> None:
    session = _session()
    _sync_automated_source(session, "approved-api")

    candidates = select_ranked_research_sources(
        session,
        purpose=PURPOSE,
        data_category=CATEGORY,
        now=NOW,
    )

    assert [candidate.source_id for candidate in candidates] == [
        "persisted-evidence",
        "approved-api",
    ]
    automated = candidates[1]
    assert automated.mode is ResearchStepMode.AUTOMATED_ADAPTER
    assert automated.authorized is True
    assert automated.executable is True
    assert automated.quota_remaining == 100


def test_wrong_purpose_category_and_missing_authorization_remove_adapter() -> None:
    session = _session()
    _sync_automated_source(session, "approved-api")

    wrong_purpose = select_ranked_research_sources(
        session,
        purpose="different-purpose",
        data_category=CATEGORY,
        now=NOW,
    )
    wrong_category = select_ranked_research_sources(
        session,
        purpose=PURPOSE,
        data_category=DataCategory.PUBLIC_TENDER,
        now=NOW,
    )

    assert [candidate.source_id for candidate in wrong_purpose] == ["persisted-evidence"]
    assert [candidate.source_id for candidate in wrong_category] == ["persisted-evidence"]

    missing_auth = _session()
    _sync_automated_source(
        missing_auth,
        "missing-auth-api",
        authorization_status=AuthorizationStatus.MISSING,
    )
    candidates = select_ranked_research_sources(
        missing_auth,
        purpose=PURPOSE,
        data_category=CATEGORY,
        now=NOW,
    )
    assert [candidate.source_id for candidate in candidates] == ["persisted-evidence"]


def test_quota_and_monthly_cost_budget_remove_automated_candidate() -> None:
    quota_session = _session()
    _sync_automated_source(quota_session, "quota-api", quota=0)
    quota_candidates = select_ranked_research_sources(
        quota_session,
        purpose=PURPOSE,
        data_category=CATEGORY,
        now=NOW,
    )
    assert [candidate.source_id for candidate in quota_candidates] == ["persisted-evidence"]

    cost_session = _session()
    _sync_automated_source(
        cost_session,
        "cost-api",
        monthly_cost_limit=1.0,
        cost_per_request=1.0,
        monthly_cost_used=1.0,
    )
    cost_candidates = select_ranked_research_sources(
        cost_session,
        purpose=PURPOSE,
        data_category=CATEGORY,
        now=NOW,
    )
    assert [candidate.source_id for candidate in cost_candidates] == ["persisted-evidence"]


def test_governed_search_provider_is_manual_candidate_without_automation() -> None:
    session = _session()
    _sync_manual_source(session, "manual-search")

    candidates = select_ranked_research_sources(
        session,
        purpose=PURPOSE,
        data_category=CATEGORY,
        now=NOW,
    )

    assert [candidate.mode for candidate in candidates] == [
        ResearchStepMode.PERSISTED_SEARCH,
        ResearchStepMode.MANUAL_LINK,
    ]
    manual = candidates[1]
    assert manual.source_id == "manual-search"
    assert manual.manual_link_allowed is True
    assert manual.authorized is False
    assert manual.executable is False


def test_quarantined_browser_is_never_offered_as_manual_research() -> None:
    session = _session()
    _sync_manual_source(
        session,
        "blocked-browser",
        source_type=SourceType.BROWSER,
        status=SourceStatus.QUARANTINED,
    )

    candidates = select_ranked_research_sources(
        session,
        purpose=PURPOSE,
        data_category=CATEGORY,
        now=NOW,
    )

    assert [candidate.source_id for candidate in candidates] == ["persisted-evidence"]


def _session() -> Session:
    engine = create_database_engine("sqlite+pysqlite:///:memory:")
    get_metadata().create_all(engine)
    return create_session_factory(engine)()


def _sync_automated_source(
    session: Session,
    source_id: str,
    *,
    authorization_status: AuthorizationStatus = AuthorizationStatus.APPROVED,
    quota: int = 100,
    monthly_cost_limit: float = 10.0,
    cost_per_request: float = 0.0,
    monthly_cost_used: float = 0.0,
) -> None:
    policy = _policy(source_id, source_type=SourceType.API, status=SourceStatus.ENABLED)
    authorization = SourceAuthorization(
        status=authorization_status,
        document_reference=(
            f"approval:{source_id}"
            if authorization_status is AuthorizationStatus.APPROVED
            else None
        ),
        reviewed_at=NOW - timedelta(days=1),
        approved_hosts=frozenset({f"{source_id}.example.test"}),
        approved_path_prefixes=("/results",),
        approved_purposes=frozenset({PURPOSE}),
        automated_collection_allowed=True,
        raw_storage_allowed=False,
    )
    sync_source_registry(session, (SourceRegistryEntry(policy, authorization, {}),))
    capability = AdapterCapabilityManifest(
        source_id=source_id,
        adapter_id=f"{source_id}-adapter",
        adapter_version="1",
        provider_schema_version="research-v1",
        modes=frozenset({CollectionMode.PRIORITY_REFRESH}),
        canonical_output_types=("research_result",),
        max_page_size=25,
        cost_per_request=cost_per_request,
    )
    sync_source_portfolio(
        session,
        (
            SourceCatalogEntry(
                source_id=source_id,
                display_name=source_id,
                canonical_url=f"https://{source_id}.example.test",
                category="research",
                status=CatalogStatus.EXECUTABLE,
                freshness_max_age_seconds=3600,
                commercial_use_cases=("organization_research",),
                adapter=capability,
                monthly_cost_limit=monthly_cost_limit,
            ),
        ),
        now=NOW,
    )
    health = session.get(SourceHealthRecord, source_id)
    assert health is not None
    health.quota_remaining = quota
    health.monthly_cost_used = monthly_cost_used
    health.last_success_at = NOW
    session.flush()


def _sync_manual_source(
    session: Session,
    source_id: str,
    *,
    source_type: SourceType = SourceType.SEARCH_PROVIDER,
    status: SourceStatus = SourceStatus.CONDITIONAL,
) -> None:
    policy = _policy(source_id, source_type=source_type, status=status)
    authorization = SourceAuthorization(
        status=AuthorizationStatus.PENDING_REVIEW,
        document_reference=None,
        approved_hosts=frozenset(),
        approved_path_prefixes=(),
        approved_purposes=frozenset(),
        automated_collection_allowed=False,
        raw_storage_allowed=False,
    )
    sync_source_registry(session, (SourceRegistryEntry(policy, authorization, {}),))
    session.flush()


def _policy(
    source_id: str,
    *,
    source_type: SourceType,
    status: SourceStatus,
) -> SourcePolicy:
    return SourcePolicy(
        id=source_id,
        name=source_id,
        base_url=f"https://{source_id}.example.test",
        status=status,
        source_type=source_type,
        owner="Research provider",
        allowed_data_categories=frozenset({CATEGORY}),
        prohibited_data_categories=frozenset({DataCategory.PRIVATE_PERSONAL_DATA}),
        terms_url=f"https://{source_id}.example.test/terms",
        retention_days=90,
        raw_content_storage=False,
        human_review_required=True,
    )
