from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from cip.modules.conditional_integrations.api.routes import router
from cip.modules.provider_onboarding.domain.models import OnboardingState
from cip.modules.provider_onboarding.infrastructure.models import ProviderOnboardingRecord
from cip.modules.source_governance.domain.models import DataCategory
from cip.modules.source_governance.infrastructure.models import SourceRecord
from cip.modules.source_portfolio.infrastructure.models import (
    AdapterCapabilityRecord,
    SourceHealthRecord,
    SourcePortfolioRecord,
)
from cip.shared.config.settings import Settings, get_settings
from cip.shared.persistence.dependencies import get_database_session
from cip.shared.persistence.metadata import get_metadata

CONTROL_TOKEN = "conditional-test-control-token"
HEADERS = {"X-CIP-Control-Token": CONTROL_TOKEN}
SOURCE_ID = "linkedin-approved-api"
NOW = datetime(2026, 8, 9, 12, 0, tzinfo=UTC)
TARGET_URL = "https://api.linkedin.example.test/organizations/123"


@pytest.fixture
def client() -> Iterator[TestClient]:
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    get_metadata().create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)
    database = factory()
    _seed_runtime(database)
    settings = Settings(
        environment="test",
        database_url="sqlite+pysqlite://",
        control_plane_token=CONTROL_TOKEN,
    )
    application = FastAPI()
    application.include_router(router)

    def override_session() -> Iterator[Session]:
        yield database

    def override_settings() -> Settings:
        return settings

    application.dependency_overrides[get_database_session] = override_session
    application.dependency_overrides[get_settings] = override_settings
    with TestClient(application) as test_client:
        yield test_client
    database.close()


def test_control_plane_rejects_anonymous_access(client: TestClient) -> None:
    response = client.get("/v1/conditional-integrations/providers")

    assert response.status_code == 401


def test_approval_list_detail_and_revision_history(client: TestClient) -> None:
    created = client.put(
        f"/v1/conditional-integrations/providers/{SOURCE_ID}/approval",
        headers=HEADERS,
        json=_approval_payload(change_reason="initial provider approval"),
    )

    assert created.status_code == 200
    assert created.json()["source_id"] == SOURCE_ID
    assert created.json()["state"] == "approved"

    listed = client.get("/v1/conditional-integrations/providers", headers=HEADERS)
    assert listed.status_code == 200
    assert listed.json()["total"] == 1
    assert listed.json()["items"][0]["approval"]["source_id"] == SOURCE_ID

    changed_payload = _approval_payload(change_reason="approve public team field")
    changed_payload["approved_fields"].append("public_team")
    changed = client.put(
        f"/v1/conditional-integrations/providers/{SOURCE_ID}/approval",
        headers=HEADERS,
        json=changed_payload,
    )
    assert changed.status_code == 200
    assert "public_team" in changed.json()["approved_fields"]

    detail = client.get(
        f"/v1/conditional-integrations/providers/{SOURCE_ID}",
        headers=HEADERS,
    )
    assert detail.status_code == 200
    body = detail.json()
    assert len(body["revisions"]) == 2
    assert body["revisions"][0]["actor"] == "provider-admin@example.test"
    assert body["revisions"][0]["change_reason"] == "approve public team field"
    assert body["revisions"][1]["change_reason"] == "initial provider approval"
    assert body["control"] is None
    assert body["control_decisions"] == []
    assert body["execution_decisions"] == []


def test_pause_resume_and_kill_switch_are_audited(client: TestClient) -> None:
    _create_approval(client)

    paused = _control(client, "pause", "terms review")
    assert paused["paused"] is True
    assert paused["kill_switch_active"] is False
    assert paused["paused_reason"] == "terms review"

    stopped = _control(client, "activate_kill_switch", "emergency stop")
    assert stopped["paused"] is True
    assert stopped["kill_switch_active"] is True

    resumed = _control(client, "resume", "terms review complete")
    assert resumed["paused"] is False
    assert resumed["kill_switch_active"] is True

    cleared = _control(client, "clear_kill_switch", "incident resolved")
    assert cleared["paused"] is False
    assert cleared["kill_switch_active"] is False

    detail = client.get(
        f"/v1/conditional-integrations/providers/{SOURCE_ID}",
        headers=HEADERS,
    )
    assert detail.status_code == 200
    decisions = detail.json()["control_decisions"]
    assert len(decisions) == 4
    assert decisions[0]["action"] == "clear_kill_switch"
    assert decisions[-1]["action"] == "pause"


def test_eligibility_uses_persisted_runtime_state_and_is_audited(
    client: TestClient,
) -> None:
    _create_approval(client)

    allowed = _eligibility(client)
    assert allowed["allowed"] is True
    assert allowed["reasons"] == ["allowed"]
    assert allowed["target_url"] == TARGET_URL
    assert allowed["onboarding_state"] == "connected"
    assert allowed["source_policy_allowed"] is True
    assert allowed["source_portfolio_allowed"] is True
    assert allowed["adapter_capability_present"] is True
    assert allowed["quota_remaining"] == 100
    assert allowed["monthly_cost_used"] == 10.0
    assert allowed["monthly_cost_limit"] == 100.0

    _control(client, "pause", "provider review")
    paused = _eligibility(client)
    assert paused["allowed"] is False
    assert "provider_paused" in paused["reasons"]

    denied = _eligibility(
        client,
        target_url="https://unapproved.example.test/organizations/123",
    )
    assert denied["allowed"] is False
    assert denied["source_policy_allowed"] is False
    assert "source_policy_denied" in denied["reasons"]

    detail = client.get(
        f"/v1/conditional-integrations/providers/{SOURCE_ID}",
        headers=HEADERS,
    )
    assert detail.status_code == 200
    audits = detail.json()["execution_decisions"]
    assert len(audits) == 3
    assert audits[0]["source_policy_allowed"] is False


def test_missing_provider_and_invalid_approval_fail_closed(client: TestClient) -> None:
    missing = client.get(
        "/v1/conditional-integrations/providers/missing-provider",
        headers=HEADERS,
    )
    assert missing.status_code == 404

    missing_control = client.post(
        "/v1/conditional-integrations/providers/missing-provider/control",
        headers=HEADERS,
        json={
            "action": "pause",
            "actor": "provider-admin@example.test",
            "reason": "test",
        },
    )
    assert missing_control.status_code == 404

    missing_eligibility = client.post(
        "/v1/conditional-integrations/providers/missing-provider/eligibility",
        headers=HEADERS,
        json=_eligibility_payload(),
    )
    assert missing_eligibility.status_code == 404

    invalid_payload = _approval_payload(change_reason="invalid approval")
    invalid_payload["authorization_document_reference"] = None
    invalid = client.put(
        f"/v1/conditional-integrations/providers/{SOURCE_ID}/approval",
        headers=HEADERS,
        json=invalid_payload,
    )
    assert invalid.status_code == 422
    assert "authorization document" in invalid.json()["detail"]


def test_list_pagination_is_validated(client: TestClient) -> None:
    response = client.get(
        "/v1/conditional-integrations/providers?limit=0",
        headers=HEADERS,
    )

    assert response.status_code == 422


def _create_approval(client: TestClient) -> None:
    response = client.put(
        f"/v1/conditional-integrations/providers/{SOURCE_ID}/approval",
        headers=HEADERS,
        json=_approval_payload(change_reason="initial provider approval"),
    )
    assert response.status_code == 200


def _control(client: TestClient, action: str, reason: str) -> dict[str, object]:
    response = client.post(
        f"/v1/conditional-integrations/providers/{SOURCE_ID}/control",
        headers=HEADERS,
        json={
            "action": action,
            "actor": "provider-admin@example.test",
            "reason": reason,
        },
    )
    assert response.status_code == 200
    return response.json()


def _eligibility(
    client: TestClient,
    *,
    target_url: str = TARGET_URL,
) -> dict[str, object]:
    response = client.post(
        f"/v1/conditional-integrations/providers/{SOURCE_ID}/eligibility",
        headers=HEADERS,
        json=_eligibility_payload(target_url=target_url),
    )
    assert response.status_code == 200
    return response.json()


def _eligibility_payload(*, target_url: str = TARGET_URL) -> dict[str, object]:
    return {
        "access_method": "official_api",
        "purpose": "professional-context",
        "data_category": "professional_contact",
        "target_url": target_url,
        "requested_scopes": ["organizations.read"],
        "requested_fields": ["organization", "public_professional_role"],
        "retention_days": 180,
        "automated": True,
        "store_raw_content": False,
        "account_reference": "account:linkedin-cip",
    }


def _approval_payload(*, change_reason: str) -> dict[str, object]:
    return {
        "provider_kind": "linkedin",
        "access_method": "official_api",
        "state": "approved",
        "authorization_document_reference": "approval:linkedin-2026-08",
        "licence_reference": None,
        "terms_reference": "terms:linkedin-reviewed-2026-08",
        "terms_state": "current",
        "approved_scopes": ["organizations.read"],
        "approved_fields": ["organization", "public_professional_role"],
        "approved_purposes": ["professional-context"],
        "approved_data_categories": ["professional_contact"],
        "retention_days": 365,
        "automated_collection_allowed": True,
        "account_reference": "account:linkedin-cip",
        "reviewed_at": "2026-08-09T12:00:00Z",
        "review_due_at": "2026-11-07T12:00:00Z",
        "expires_at": "2027-02-05T12:00:00Z",
        "revoked_at": None,
        "paused_reason": None,
        "actor": "provider-admin@example.test",
        "change_reason": change_reason,
    }


def _seed_runtime(session: Session) -> None:
    session.add(
        SourceRecord(
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
    )
    session.add(
        ProviderOnboardingRecord(
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
    )
    session.add(
        SourcePortfolioRecord(
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
    )
    session.add(
        AdapterCapabilityRecord(
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
    )
    session.add(
        SourceHealthRecord(
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
    )
    session.commit()
