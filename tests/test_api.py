from fastapi.testclient import TestClient

from cip.main import app

client = TestClient(app)


def test_health() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": "0.1.0"}


def test_validate_source_policy() -> None:
    response = client.post(
        "/v1/source-policies/validate",
        json={
            "id": "official-api",
            "name": "Official API",
            "base_url": "https://example.org",
            "status": "allowed",
            "source_type": "api",
            "owner": "Example Authority",
            "terms_url": "https://example.org/terms",
            "allowed_data_categories": ["public_incident_metadata"],
            "prohibited_data_categories": ["credentials"],
            "rate_limit_per_minute": 10,
            "attribution_required": True,
            "raw_content_storage": False,
            "human_review_required": True,
            "notes": "Test fixture",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["id"] == "official-api"
    assert payload["status"] == "allowed"
