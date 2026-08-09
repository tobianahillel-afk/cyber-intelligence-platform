from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import delete
from sqlalchemy.orm import Session

from cip.modules.conditional_integrations.domain import (
    ConditionalAccessMethod,
    ConditionalExecutionRequest,
)
from cip.modules.conditional_integrations.infrastructure.runtime_dependencies import (
    resolve_runtime_dependencies,
)
from cip.modules.provider_onboarding.domain.models import OnboardingState
from cip.modules.provider_onboarding.infrastructure.models import ProviderOnboardingRecord
from cip.modules.source_governance.domain.models import DataCategory
from cip.modules.source_governance.infrastructure.models import SourceRecord
from cip.modules.source_portfolio.infrastructure.models import (
    AdapterCapabilityRecord,
    SourceHealthRecord,
    SourcePortfolioRecord,
)
from cip.shared.persistence.metadata import get_metadata
from cip.shared.persistence.session import create_database_engine, create_session_factory

NOW = datetime(2026, 8, 9, 13, 0, tzinfo=UTC)
SOURCE_ID = "linkedin-approved-api"
TARGET_URL = "https://api.linkedin.example.test/organizations/123"


def test_resolver_uses_persisted_positive_control_planes() -> None:
    session = _session()
    _seed_ready_runtime(session)

    dependencies = resolve_runtime_dependencies(session, _request(), now=NOW)

    assert dependencies.onboarding_state is OnboardingState.CONNECTED
    assert dependencies.source_policy_allowed is True
    assert dependencies.source_portfolio_allowed is True
    assert dependencies.adapter_capability_present is True
    assert dependencies.quota_remaining == 100
    assert dependencies.monthly_cost_used == 10.0
    assert dependencies.monthly_cost_limit == 100.0


def test_missing_onboarding_fails_closed_for_connected_method() -> None:
    session = _session()
    _seed_ready_runtime(session, include_onboarding=False)

    dependencies = resolve_runtime_dependencies(session, _request(), now=NOW)

    assert dependencies.onboarding_state is OnboardingState.NOT_CONFIGURED


def test_source_policy_denies_target_outside_approved_host() -> None:
    session = _session()
    _seed_ready_runtime(session)
    request = _request(target_url="https://unapproved.example.test/organizations/123")

    dependencies = resolve_runtime_dependencies(session, request, now=NOW)

    assert dependencies.source_policy_allowed is False
    assert dependencies.source_portfolio_allowed is True


def test_non_executable_portfolio_and_missing_capability_are_distinct() -> None:
    session = _session()
    _seed_ready_runtime(session)
    portfolio = session.get(SourcePortfolioRecord, SOURCE_ID)
    assert portfolio is not None
    portfolio.status = "paused"
    session.execute(
        delete(AdapterCapabilityRecord).where(AdapterCapabilityRecord.source_id == SOURCE_ID)
    )
    session.flush()

    dependencies = resolve_runtime_dependencies(session, _request(), now=NOW)

    assert dependencies.source_policy_allowed is True
    assert dependencies.source_portfolio_allowed is False
    assert dependencies.adapter_capability_present is False


def test_quota_exhaustion_is_derived_from_source_health() -> None:
    session = _session()
    _seed_ready_runtime(session)
    health = session.get(SourceHealthRecord, SOURCE_ID)
    assert health is not None
    health.quota_remaining = 0
    session.flush()

    dependencies = resolve_runtime_dependencies(session, _request(), now=NOW)

    assert dependencies.quota_remaining == 0
    assert dependencies.source_portfolio_allowed is False


def _session() -> Session:
    engine = create_database_engine("sqlite+pysqlite:///:memory:")
    get_metadata().create_all(engine)
    return create_session_factory(engine)()


def _seed_ready_runtime(session: Session, *, include_onboarding: bool = True) -> None:
    session.add(_source_record())
    if include_onboarding:
        session.add(_onboarding_record())
    session.add(_portfolio_record())
    session.add(_capability_record())
    session.add(_health_record())
    session.flush()


def _source_record() -> SourceRecord:
    return SourceRecord(
        id=SOURCE_ID,
        name="LinkedIn approved API",
        base_url="https://api.linkedin.example.test",
        status="enabled",
        source_type="api",
        owner="provider-governance",
        terms_url="https://www.linkedin.example.test/terms",
        licence=None,
        allowed_data_categories=[DataCategory.PROFESSIONAL_CONTACT.value],
        prohibited_data_categories=[],
        rate_limit_per_minute=60,
        retention_days=365,
        attribution_required=False,
        raw_content_storage=False,
        human_review_required=False,
        authorization_status="approved",
        authorization_document_reference="approval:linkedin-2026-08",
        authorization_reviewed_at=NOW - timedelta(days=1),
        authorization_expires_at=NOW + timedelta(days=180),
        approved_hosts=["api.linkedin.example.test"],
        approved_path_prefixes=["/organizations"],
        approved_purposes=["professional-context"],
        automated_collection_allowed=True,
        raw_storage_allowed=False,
    )


def _onboarding_record() -> ProviderOnboardingRecord:
    return ProviderOnboardingRecord(
        source_id=SOURCE_ID,
        display_name="LinkedIn approved API",
        auth_mode="api_key",
        state=OnboardingState.CONNECTED.value,
        documentation_url="https://api.linkedin.example.test/docs",
        signup_url=None,
        console_url=None,
        required_secret_names=[],
        human_actions=[],
        automatic_onboarding=False,
        secret_references={},
        blocked_reason=None,
        last_verified_at=NOW,
        expires_at=NOW + timedelta(days=90),
        last_error_code=None,
        last_error_message=None,
        created_at=NOW,
        updated_at=NOW,
    )


def _portfolio_record() -> SourcePortfolioRecord:
    return SourcePortfolioRecord(
        source_id=SOURCE_ID,
        display_name="LinkedIn approved API",
        canonical_url="https://api.linkedin.example.test",
        category="professional_context",
        status="executable",
        freshness_max_age_seconds=86_400,
        commercial_use_cases=["professional-context"],
        authorization_expires_at=NOW + timedelta(days=180),
        review_due_at=NOW + timedelta(days=90),
        candidate_origin="lot22-test",
        monthly_cost_limit=100.0,
        extra_metadata={},
        created_at=NOW,
        updated_at=NOW,
    )


def _capability_record() -> AdapterCapabilityRecord:
    return AdapterCapabilityRecord(
        source_id=SOURCE_ID,
        adapter_id="linkedin-approved-api-v1",
        adapter_version="1.0.0",
        provider_schema_version="2026-08",
        modes=["entity_lookup"],
        canonical_output_types=["professional_context"],
        supports_corrections=False,
        supports_tombstones=False,
        supports_retractions=False,
        max_page_size=100,
        max_window_days=None,
        cost_per_request=1.0,
        updated_at=NOW,
    )


def _health_record() -> SourceHealthRecord:
    return SourceHealthRecord(
        source_id=SOURCE_ID,
        freshness_state="fresh",
        schema_state="stable",
        volume_state="normal",
        field_population_state="normal",
        last_attempt_at=NOW,
        last_success_at=NOW,
        last_source_record_at=NOW,
        consecutive_failures=0,
        quota_remaining=100,
        monthly_cost_used=10.0,
        cost_window_started_at=datetime(2026, 8, 1, tzinfo=UTC),
        current_backfill_state=None,
        last_error_code=None,
        updated_at=NOW,
    )


def _request(*, target_url: str = TARGET_URL) -> ConditionalExecutionRequest:
    return ConditionalExecutionRequest(
        source_id=SOURCE_ID,
        access_method=ConditionalAccessMethod.OFFICIAL_API,
        purpose="professional-context",
        data_category=DataCategory.PROFESSIONAL_CONTACT,
        target_url=target_url,
        requested_scopes=frozenset({"organizations.read"}),
        requested_fields=frozenset({"organization", "public_professional_role"}),
        retention_days=180,
        automated=True,
        store_raw_content=False,
        account_reference="account:linkedin-cip",
    )
