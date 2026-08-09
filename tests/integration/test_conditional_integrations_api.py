from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from cip.modules.conditional_integrations.api.routes import router
from cip.shared.config.settings import Settings, get_settings
from cip.shared.persistence.dependencies import get_database_session
from cip.shared.persistence.metadata import get_metadata

CONTROL_TOKEN = "conditional-test-control-token"
HEADERS = {"X-CIP-Control-Token": CONTROL_TOKEN}
SOURCE_ID = "linkedin-approved-api"


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
