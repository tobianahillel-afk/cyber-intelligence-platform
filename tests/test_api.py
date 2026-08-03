from __future__ import annotations

from fastapi.testclient import TestClient

from cip.main import app, create_app

client = TestClient(app)


def policy_payload(**changes: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "id": "official-api",
        "name": "Official API",
        "base_url": "https://api.example.org",
        "status": "enabled",
        "source_type": "api",
        "owner": "Example Authority",
        "terms_url": "https://example.org/terms",
        "allowed_data_categories": ["public_incident_metadata"],
        "prohibited_data_categories": ["credential"],
        "rate_limit_per_minute": 10,
        "retention_days": 90,
        "attribution_required": True,
        "raw_content_storage": False,
        "human_review_required": False,
    }
    payload.update(changes)
    return payload


def evaluation_payload(**changes: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "policy": policy_payload(),
        "authorization": {
            "status": "approved",
            "document_reference": "AUTH-2026-001",
            "reviewed_at": "2026-08-02T16:00:00Z",
            "expires_at": "2026-09-03T16:00:00Z",
            "approved_hosts": ["api.example.org"],
            "approved_path_prefixes": ["/v1/"],
            "approved_purposes": ["cyber-opportunity-research"],
            "automated_collection_allowed": True,
            "raw_storage_allowed": False,
        },
        "runtime": {"remaining_requests": 5},
        "request": {
            "data_category": "public_incident_metadata",
            "target_url": "https://api.example.org/v1/incidents",
            "purpose": "cyber-opportunity-research",
            "automated": True,
            "store_raw_content": False,
            "human_review_completed": False,
        },
        "now": "2026-08-03T16:00:00Z",
    }
    payload.update(changes)
    return payload


def test_health() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": "0.2.0"}


def test_application_factory_builds_independent_app() -> None:
    application = create_app()

    assert application is not app
    assert application.version == "0.2.0"


def test_validate_source_policy() -> None:
    response = client.post(
        "/v1/source-governance/policies/validate",
        json=policy_payload(),
    )

    assert response.status_code == 200
    assert response.json()["status"] == "enabled"


def test_validate_source_policy_rejects_domain_conflict() -> None:
    response = client.post(
        "/v1/source-governance/policies/validate",
        json=policy_payload(
            allowed_data_categories=["credential"],
            prohibited_data_categories=["credential"],
        ),
    )

    assert response.status_code == 422
    assert "both allowed and prohibited" in response.json()["detail"]


def test_validate_source_policy_rejects_invalid_url() -> None:
    response = client.post(
        "/v1/source-governance/policies/validate",
        json=policy_payload(base_url="not-a-url"),
    )

    assert response.status_code == 422


def test_evaluate_collection_allows_approved_request() -> None:
    response = client.post("/v1/source-governance/evaluate", json=evaluation_payload())

    assert response.status_code == 200
    assert response.json() == {
        "allowed": True,
        "reason": "allowed",
        "requires_human_review": False,
    }


def test_evaluate_collection_denies_missing_authorization() -> None:
    response = client.post(
        "/v1/source-governance/evaluate",
        json=evaluation_payload(authorization={"status": "missing"}),
    )

    assert response.status_code == 200
    assert response.json()["reason"] == "authorization_missing"


def test_evaluate_collection_rejects_naive_timestamp() -> None:
    response = client.post(
        "/v1/source-governance/evaluate",
        json=evaluation_payload(now="2026-08-03T16:00:00"),
    )

    assert response.status_code == 422
    assert "timezone-aware" in response.json()["detail"]


def test_evaluate_collection_rejects_invalid_approved_authorization() -> None:
    response = client.post(
        "/v1/source-governance/evaluate",
        json=evaluation_payload(authorization={"status": "approved"}),
    )

    assert response.status_code == 422
    assert "document reference" in response.json()["detail"]
