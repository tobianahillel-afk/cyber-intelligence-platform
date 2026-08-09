from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from cip.modules.evidence.infrastructure.models import EvidenceRecord
from cip.modules.research_orchestration.api.router import router
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
from cip.shared.config.settings import Settings, get_settings
from cip.shared.persistence.dependencies import get_database_session
from cip.shared.persistence.metadata import get_metadata

CONTROL_TOKEN = "research-control-token"
HEADERS = {"X-CIP-Control-Token": CONTROL_TOKEN}
PLAN_ID = UUID("11111111-1111-4111-8111-111111111111")
MANUAL_SOURCE = "manual-search-provider"
MANUAL_TOOL = "manual-search-link"
MISSING_SOURCE = "missing-automated-source"
MISSING_TOOL = "missing-automated-adapter"
EVIDENCE_ID = UUID("22222222-2222-4222-8222-222222222222")
SOURCE_RECORD_KEY = "manual-result-42"


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
    _persist_manual_source(database)
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


def test_research_api_rejects_anonymous_access(client: TestClient) -> None:
    response = client.get("/v1/research/plans")

    assert response.status_code == 401


def test_plan_lifecycle_revision_list_and_detail(client: TestClient) -> None:
    created = _create_plan(client)
    assert created["state"] == "draft"

    listed = client.get("/v1/research/plans", headers=HEADERS)
    assert listed.status_code == 200
    assert listed.json()["total"] == 1

    approved = _decide(client, "approve", "bounded plan reviewed")
    assert approved["resulting_state"] == "approved"

    revised_payload = _plan_payload(change_reason="refine question")
    revised_payload["question"] = "Which bounded public evidence is most useful?"
    revised = client.put(
        f"/v1/research/plans/{PLAN_ID}",
        headers=HEADERS,
        json=revised_payload,
    )
    assert revised.status_code == 200
    assert revised.json()["state"] == "approved"

    detail = client.get(f"/v1/research/plans/{PLAN_ID}", headers=HEADERS)
    assert detail.status_code == 200
    body = detail.json()
    assert body["plan"]["state"] == "approved"
    assert len(body["revisions"]) == 3
    assert len(body["plan_decisions"]) == 1
    assert body["usage"] == {
        "completed_steps": 0,
        "automated_steps": 0,
        "cost_used": 0.0,
    }


def test_automated_step_is_evaluated_from_persisted_runtime(client: TestClient) -> None:
    _create_and_approve_plan(client)
    _create_step(client, _automated_step_payload())

    response = client.post(
        f"/v1/research/plans/{PLAN_ID}/steps/automated-1/evaluate",
        headers=HEADERS,
        json={
            "source_authorized": True,
            "source_executable": True,
            "adapter_capability_present": True,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["allowed"] is False
    assert body["runtime"]["source_authorized"] is False
    assert body["runtime"]["source_executable"] is False
    assert body["runtime"]["adapter_capability_present"] is False
    assert "source_authorization_required" in body["reasons"]

    attempt = client.post(
        f"/v1/research/plans/{PLAN_ID}/steps/automated-1/attempts",
        headers=HEADERS,
        json={"actor": "analyst@example.test", "idempotency_key": "blocked-1"},
    )
    assert attempt.status_code == 422


def test_manual_link_attempt_is_idempotent_and_never_starts_external_action(
    client: TestClient,
) -> None:
    _create_and_approve_plan(client)
    _create_step(client, _manual_step_payload())

    evaluated = client.post(
        f"/v1/research/plans/{PLAN_ID}/steps/manual-1/evaluate",
        headers=HEADERS,
    )
    assert evaluated.status_code == 200
    assert evaluated.json()["allowed"] is True
    assert evaluated.json()["next_state"] == "manual_action_required"
    assert evaluated.json()["runtime"]["manual_link_allowed"] is True

    first = _create_attempt(client, "manual-1", "manual-request-1")
    replay = _create_attempt(client, "manual-1", "manual-request-1")
    assert first["id"] == replay["id"]
    assert first["state"] == "manual_action_required"
    assert first["external_action_started"] is False
    assert first["external_action_reference"] is None

    completed = client.post(
        f"/v1/research/plans/{PLAN_ID}/attempts/{first['id']}/complete",
        headers=HEADERS,
    )
    assert completed.status_code == 200
    assert completed.json()["state"] == "completed"

    detail = client.get(f"/v1/research/plans/{PLAN_ID}", headers=HEADERS)
    assert detail.status_code == 200
    assert detail.json()["usage"]["completed_steps"] == 1
    assert detail.json()["usage"]["automated_steps"] == 0


def test_result_capture_requires_existing_matching_evidence_and_provenance(
    client: TestClient,
) -> None:
    _create_and_approve_plan(client)
    _create_step(client, _manual_step_payload())
    attempt = _create_attempt_after_evaluation(client, "manual-1", "manual-result")
    _complete_attempt(client, attempt["id"])
    _insert_evidence(client)

    arbitrary = _post_result(
        client,
        attempt_id=attempt["id"],
        evidence_reference="public-resource:42",
        provenance_reference=f"source-record:{SOURCE_RECORD_KEY}",
    )
    assert arbitrary.status_code == 422

    missing = _post_result(
        client,
        attempt_id=attempt["id"],
        evidence_reference=f"evidence:{uuid4()}",
        provenance_reference=f"source-record:{SOURCE_RECORD_KEY}",
    )
    assert missing.status_code == 404

    valid = _post_result(
        client,
        attempt_id=attempt["id"],
        evidence_reference=f"evidence:{EVIDENCE_ID}",
        provenance_reference=f"source-record:{SOURCE_RECORD_KEY}",
    )
    assert valid.status_code == 200
    assert valid.json()["source_id"] == MANUAL_SOURCE

    wrong_source = _post_result(
        client,
        attempt_id=attempt["id"],
        evidence_reference=f"evidence:{EVIDENCE_ID}",
        provenance_reference=f"source-record:{SOURCE_RECORD_KEY}",
        source_id="different-source",
    )
    assert wrong_source.status_code == 422


def test_missing_resources_invalid_transition_and_terminal_revision_fail_closed(
    client: TestClient,
) -> None:
    missing_plan = client.get(f"/v1/research/plans/{uuid4()}", headers=HEADERS)
    assert missing_plan.status_code == 404

    _create_and_approve_plan(client)
    missing_step = client.post(
        f"/v1/research/plans/{PLAN_ID}/steps/missing/evaluate",
        headers=HEADERS,
    )
    assert missing_step.status_code == 404

    invalid_transition = client.post(
        f"/v1/research/plans/{PLAN_ID}/decision",
        headers=HEADERS,
        json={
            "decision_type": "reject",
            "actor": "research-lead@example.test",
            "reason": "too late",
        },
    )
    assert invalid_transition.status_code == 422

    completed = _decide(client, "complete", "research complete")
    assert completed["resulting_state"] == "completed"
    terminal_edit = client.put(
        f"/v1/research/plans/{PLAN_ID}",
        headers=HEADERS,
        json=_plan_payload(change_reason="late edit"),
    )
    assert terminal_edit.status_code == 422

    pagination = client.get("/v1/research/plans?limit=0", headers=HEADERS)
    assert pagination.status_code == 422


def _create_and_approve_plan(client: TestClient) -> None:
    _create_plan(client)
    _decide(client, "approve", "bounded plan reviewed")


def _create_plan(client: TestClient) -> dict[str, object]:
    response = client.put(
        f"/v1/research/plans/{PLAN_ID}",
        headers=HEADERS,
        json=_plan_payload(change_reason="initial plan"),
    )
    assert response.status_code == 200
    return response.json()


def _decide(client: TestClient, decision_type: str, reason: str) -> dict[str, object]:
    response = client.post(
        f"/v1/research/plans/{PLAN_ID}/decision",
        headers=HEADERS,
        json={
            "decision_type": decision_type,
            "actor": "research-lead@example.test",
            "reason": reason,
        },
    )
    assert response.status_code == 200
    return response.json()


def _create_step(client: TestClient, payload: dict[str, object]) -> dict[str, object]:
    response = client.post(
        f"/v1/research/plans/{PLAN_ID}/steps",
        headers=HEADERS,
        json=payload,
    )
    assert response.status_code == 200
    return response.json()


def _create_attempt(
    client: TestClient,
    step_key: str,
    idempotency_key: str,
) -> dict[str, object]:
    response = client.post(
        f"/v1/research/plans/{PLAN_ID}/steps/{step_key}/attempts",
        headers=HEADERS,
        json={"actor": "analyst@example.test", "idempotency_key": idempotency_key},
    )
    assert response.status_code == 200
    return response.json()


def _create_attempt_after_evaluation(
    client: TestClient,
    step_key: str,
    idempotency_key: str,
) -> dict[str, object]:
    evaluated = client.post(
        f"/v1/research/plans/{PLAN_ID}/steps/{step_key}/evaluate",
        headers=HEADERS,
    )
    assert evaluated.status_code == 200
    assert evaluated.json()["allowed"] is True
    return _create_attempt(client, step_key, idempotency_key)


def _complete_attempt(client: TestClient, attempt_id: str) -> None:
    response = client.post(
        f"/v1/research/plans/{PLAN_ID}/attempts/{attempt_id}/complete",
        headers=HEADERS,
    )
    assert response.status_code == 200


def _post_result(
    client: TestClient,
    *,
    attempt_id: str,
    evidence_reference: str,
    provenance_reference: str,
    source_id: str = MANUAL_SOURCE,
):
    return client.post(
        f"/v1/research/plans/{PLAN_ID}/steps/manual-1/results",
        headers=HEADERS,
        json={
            "attempt_id": attempt_id,
            "result_type": "evidence_reference",
            "evidence_reference": evidence_reference,
            "provenance_reference": provenance_reference,
            "source_id": source_id,
            "summary": "Bounded analyst summary",
            "recorded_by": "analyst@example.test",
        },
    )


def _insert_evidence(client: TestClient) -> None:
    dependency = client.app.dependency_overrides[get_database_session]
    session = next(dependency())
    session.add(
        EvidenceRecord(
            id=EVIDENCE_ID,
            source_id=MANUAL_SOURCE,
            source_record_key=SOURCE_RECORD_KEY,
            source_url="https://search.example.test/results/42",
            summary="Bounded evidence",
            confidence=0.9,
            collected_at=datetime.now(UTC),
            published_at=None,
            observed_at=datetime.now(UTC),
            content_hash_sha256="c" * 64,
            raw_storage_uri=None,
            raw_storage_permitted=False,
            retention_until=None,
        )
    )
    session.commit()


def _persist_manual_source(session: Session) -> None:
    policy = SourcePolicy(
        id=MANUAL_SOURCE,
        name="Governed manual search provider",
        base_url="https://search.example.test",
        status=SourceStatus.CONDITIONAL,
        source_type=SourceType.SEARCH_PROVIDER,
        owner="Research team",
        allowed_data_categories=frozenset({DataCategory.ORGANIZATION_METADATA}),
        prohibited_data_categories=frozenset({DataCategory.PRIVATE_PERSONAL_DATA}),
        terms_url="https://search.example.test/terms",
        retention_days=90,
        raw_content_storage=False,
        human_review_required=True,
    )
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
    session.commit()


def _plan_payload(*, change_reason: str) -> dict[str, object]:
    return {
        "question": "What bounded public evidence should the analyst review?",
        "purpose": "organization-research",
        "data_category": "organization_metadata",
        "budget": {
            "max_steps": 5,
            "max_automated_steps": 2,
            "max_total_cost": 10.0,
            "max_step_cost": 3.0,
        },
        "allowed_source_ids": [MANUAL_SOURCE, MISSING_SOURCE],
        "allowed_tool_ids": [MANUAL_TOOL, MISSING_TOOL],
        "approved_step_keys": ["manual-1", "automated-1"],
        "allowed_hosts": ["search.example.test", "missing.example.test"],
        "allowed_path_prefixes": ["/results"],
        "max_risk_level": "medium",
        "expires_at": "2027-01-01T00:00:00Z",
        "actor": "research-lead@example.test",
        "change_reason": change_reason,
    }


def _manual_step_payload() -> dict[str, object]:
    return {
        "step_key": "manual-1",
        "sequence": 1,
        "source_id": MANUAL_SOURCE,
        "tool_id": MANUAL_TOOL,
        "mode": "manual_link",
        "purpose": "organization-research",
        "data_category": "organization_metadata",
        "estimated_cost": 0.0,
        "risk_level": "low",
        "target_url": "https://search.example.test/results?q=acme",
        "query_text": "acme security",
    }


def _automated_step_payload() -> dict[str, object]:
    return {
        "step_key": "automated-1",
        "sequence": 2,
        "source_id": MISSING_SOURCE,
        "tool_id": MISSING_TOOL,
        "mode": "automated_adapter",
        "purpose": "organization-research",
        "data_category": "organization_metadata",
        "estimated_cost": 1.0,
        "risk_level": "low",
        "target_url": "https://missing.example.test/results?q=acme",
        "query_text": "acme security",
    }
