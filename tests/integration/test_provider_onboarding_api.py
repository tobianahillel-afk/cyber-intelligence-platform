from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from cip.main import create_app
from cip.modules.provider_onboarding.infrastructure.models import (
    ProviderOnboardingAuditRecord,
)
from cip.shared.config.settings import Settings, get_settings
from cip.shared.persistence.dependencies import get_database_session
from cip.shared.persistence.metadata import get_metadata


@pytest.fixture
def client_and_session() -> Iterator[tuple[TestClient, Session]]:
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    get_metadata().create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)
    session = factory()
    application = create_app()

    def override_session() -> Iterator[Session]:
        yield session
        session.commit()

    application.dependency_overrides[get_database_session] = override_session
    application.dependency_overrides[get_settings] = lambda: Settings(_env_file=None)
    with TestClient(application) as client:
        yield client, session
    session.close()


def test_catalog_auto_connects_public_sources(
    client_and_session: tuple[TestClient, Session],
) -> None:
    client, _ = client_and_session

    response = client.get("/v1/provider-onboarding/providers")

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 14
    by_source = {item["source_id"]: item for item in payload["items"]}
    assert by_source["cisa-kev"]["state"] == "connected"
    assert by_source["sirene-api"]["state"] == "connected"
    assert by_source["inpi-rne"]["state"] == "not_configured"
    assert by_source["linkedin-official-api"]["state"] == "not_configured"
    assert by_source["brixhub"]["state"] == "blocked"


def test_inpi_human_flow_registers_only_redacted_references(
    client_and_session: tuple[TestClient, Session],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, session = client_and_session

    started = client.post(
        "/v1/provider-onboarding/providers/inpi-rne/start",
        json={"actor": "operator"},
    )
    assert started.status_code == 200
    assert started.json()["state"] == "awaiting_user_action"

    checkpoint = client.post(
        "/v1/provider-onboarding/providers/inpi-rne/human-checkpoint",
        json={
            "actor": "operator",
            "state": "awaiting_provider_approval",
            "note": "Official provider request submitted",
        },
    )
    assert checkpoint.status_code == 200

    username = client.post(
        "/v1/provider-onboarding/providers/inpi-rne/secret-reference",
        json={
            "actor": "operator",
            "name": "username",
            "reference": "env://CIP_INPI_RNE_USERNAME",
        },
    )
    assert username.status_code == 200
    assert username.json()["state"] == "awaiting_user_action"
    password = client.post(
        "/v1/provider-onboarding/providers/inpi-rne/secret-reference",
        json={
            "actor": "operator",
            "name": "password",
            "reference": "env://CIP_INPI_RNE_PASSWORD",
        },
    )
    assert password.status_code == 200
    assert password.json()["state"] == "ready_to_verify"
    assert password.json()["secret_references"] == {
        "username": "env://***",
        "password": "env://***",
    }
    assert "CIP_INPI_RNE_PASSWORD" not in password.text

    unavailable = client.post(
        "/v1/provider-onboarding/providers/inpi-rne/verify",
        json={"actor": "operator"},
    )
    assert unavailable.status_code == 200
    assert unavailable.json()["state"] == "failed"
    assert unavailable.json()["last_error_code"] == "secret_reference_unavailable"

    monkeypatch.setenv("CIP_INPI_RNE_USERNAME", "technical-user")
    monkeypatch.setenv("CIP_INPI_RNE_PASSWORD", "technical-password")
    connected = client.post(
        "/v1/provider-onboarding/providers/inpi-rne/verify",
        json={"actor": "operator"},
    )
    assert connected.status_code == 200
    assert connected.json()["state"] == "connected"
    assert "technical-password" not in connected.text

    audit_count = session.scalar(select(func.count()).select_from(ProviderOnboardingAuditRecord))
    assert audit_count is not None and audit_count >= 5


def test_raw_secrets_and_unexpected_secret_names_are_rejected(
    client_and_session: tuple[TestClient, Session],
) -> None:
    client, _ = client_and_session

    raw = client.post(
        "/v1/provider-onboarding/providers/inpi-rne/secret-reference",
        json={
            "actor": "operator",
            "name": "password",
            "reference": "raw-provider-password",
        },
    )
    unexpected = client.post(
        "/v1/provider-onboarding/providers/inpi-rne/secret-reference",
        json={
            "actor": "operator",
            "name": "token",
            "reference": "env://CIP_INPI_RNE_TOKEN",
        },
    )
    public_secret = client.post(
        "/v1/provider-onboarding/providers/cisa-kev/secret-reference",
        json={
            "actor": "operator",
            "name": "token",
            "reference": "env://CIP_CISA_TOKEN",
        },
    )

    assert raw.status_code == 422
    assert unexpected.status_code == 422
    assert public_secret.status_code == 422


def test_manual_and_blocked_providers_have_distinct_behavior(
    client_and_session: tuple[TestClient, Session],
) -> None:
    client, _ = client_and_session

    manual = client.post(
        "/v1/provider-onboarding/providers/linkedin-official-api/start",
        json={"actor": "operator"},
    )
    assert manual.status_code == 200
    assert manual.json()["state"] == "awaiting_user_action"
    verified = client.post(
        "/v1/provider-onboarding/providers/linkedin-official-api/verify",
        json={"actor": "operator"},
    )
    assert verified.status_code == 200
    assert verified.json()["state"] == "awaiting_provider_approval"

    blocked = client.post(
        "/v1/provider-onboarding/providers/brixhub/start",
        json={"actor": "operator"},
    )
    browser = client.post(
        "/v1/provider-onboarding/providers/linkedin-authorized-browser/start",
        json={"actor": "operator"},
    )
    assert blocked.status_code == 409
    assert browser.status_code == 409


def test_revoke_clears_references_and_provider_not_found_is_404(
    client_and_session: tuple[TestClient, Session],
) -> None:
    client, _ = client_and_session
    client.post(
        "/v1/provider-onboarding/providers/inpi-rne/secret-reference",
        json={
            "actor": "operator",
            "name": "username",
            "reference": "env://CIP_INPI_RNE_USERNAME",
        },
    )

    revoked = client.post(
        "/v1/provider-onboarding/providers/inpi-rne/revoke",
        json={"actor": "operator"},
    )
    missing = client.get("/v1/provider-onboarding/providers/unknown-provider")

    assert revoked.status_code == 200
    assert revoked.json()["state"] == "revoked"
    assert revoked.json()["secret_references"] == {}
    assert missing.status_code == 404


def test_invalid_checkpoint_and_actor_are_rejected(
    client_and_session: tuple[TestClient, Session],
) -> None:
    client, _ = client_and_session

    invalid_state = client.post(
        "/v1/provider-onboarding/providers/inpi-rne/human-checkpoint",
        json={"actor": "operator", "state": "connected"},
    )
    empty_actor = client.post(
        "/v1/provider-onboarding/providers/inpi-rne/start",
        json={"actor": ""},
    )

    assert invalid_state.status_code == 422
    assert empty_actor.status_code == 422
