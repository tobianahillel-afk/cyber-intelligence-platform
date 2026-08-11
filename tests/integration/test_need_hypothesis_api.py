from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from cip.main import create_app
from cip.modules.evidence.infrastructure.models import EvidenceRecord
from cip.modules.opportunities.domain.entities import (
    CommercialSignal,
    NeedHypothesisClass,
    SignalType,
)
from cip.modules.opportunities.infrastructure.fusion_generation import (
    generate_need_hypotheses,
)
from cip.modules.opportunities.infrastructure.signals import store_commercial_signal
from cip.modules.organizations.infrastructure.models import OrganizationRecord
from cip.modules.service_taxonomy.domain.models import CyberServiceFamily
from cip.shared.config.settings import Settings, get_settings
from cip.shared.persistence.dependencies import get_database_session
from cip.shared.persistence.metadata import get_metadata

NOW = datetime(2026, 8, 11, 10, 30, tzinfo=UTC)
ORG_ID = UUID("20000000-0000-0000-0000-000000000001")
MISSING_ORG_ID = UUID("20000000-0000-0000-0000-000000000099")
EVIDENCE_IDS = (
    UUID("20000000-0000-0000-0000-000000000002"),
    UUID("20000000-0000-0000-0000-000000000003"),
)


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
    _seed(database)
    settings = Settings(environment="test", database_url="sqlite+pysqlite://")
    application = create_app()

    def override_session() -> Iterator[Session]:
        yield database

    def override_settings() -> Settings:
        return settings

    application.dependency_overrides[get_database_session] = override_session
    application.dependency_overrides[get_settings] = override_settings
    with TestClient(application) as test_client:
        yield test_client
    database.close()


def test_hypothesis_list_filters_and_detail_expose_fusion_contract(client: TestClient) -> None:
    listed = client.get(
        "/v1/need-hypotheses",
        params={
            "organization_id": str(ORG_ID),
            "hypothesis_class": "capability_gap",
            "service_family": "cloud_security",
            "min_confidence": "0.6",
        },
    )

    assert listed.status_code == 200
    payload = listed.json()
    assert len(payload["items"]) == 1
    item = payload["items"][0]
    assert item["organization"] == "Example API Organization"
    assert item["hypothesis_class"] == "capability_gap"
    assert item["service_families"] == ["cloud_security"]
    assert item["confidence"] > 0.6
    assert len(item["signal_ids"]) == 2
    assert len(item["source_contributions"]) == 2

    detail = client.get(f"/v1/need-hypotheses/{item['id']}")
    assert detail.status_code == 200
    assert detail.json()["rule_id"] == "lot24-need-fusion"
    assert detail.json()["taxonomy_version"] == "2026.08"


def test_hypothesis_api_rejects_invalid_filters_and_missing_detail(client: TestClient) -> None:
    invalid_confidence = client.get(
        "/v1/need-hypotheses",
        params={"min_confidence": "1.5"},
    )
    invalid_family = client.get(
        "/v1/need-hypotheses",
        params={"service_family": "not_a_family"},
    )
    missing = client.get(
        "/v1/need-hypotheses/20000000-0000-0000-0000-000000000098"
    )

    assert invalid_confidence.status_code == 422
    assert invalid_family.status_code == 422
    assert missing.status_code == 404


def test_recompute_is_idempotent_and_never_requires_opportunity_creation(
    client: TestClient,
) -> None:
    first = client.post(f"/v1/need-hypotheses/organizations/{ORG_ID}/recompute")
    second = client.post(f"/v1/need-hypotheses/organizations/{ORG_ID}/recompute")
    missing = client.post(
        f"/v1/need-hypotheses/organizations/{MISSING_ORG_ID}/recompute"
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["generated_count"] == 1
    assert second.json()["hypothesis_ids"] == first.json()["hypothesis_ids"]
    assert missing.status_code == 404


def _seed(session: Session) -> None:
    session.add(
        OrganizationRecord(
            id=ORG_ID,
            canonical_name="Example API Organization",
            legal_name="Example API Organization",
            country_code="FR",
            website_url="https://example.invalid",
            registration_ids=[],
            created_at=NOW,
            updated_at=NOW,
        )
    )
    for index, evidence_id in enumerate(EVIDENCE_IDS):
        source_id = f"api-source-{index}"
        session.add(
            EvidenceRecord(
                id=evidence_id,
                source_id=source_id,
                source_record_key=f"record-{index}",
                source_url=f"https://{source_id}.example/record-{index}",
                summary="Organization-specific cloud transformation evidence",
                confidence=0.9,
                collected_at=NOW - timedelta(hours=2),
                published_at=NOW - timedelta(hours=3),
                observed_at=NOW - timedelta(hours=3),
                content_hash_sha256=str(index + 1) * 64,
                raw_storage_uri=None,
                raw_storage_permitted=False,
                retention_until=NOW + timedelta(days=365),
            )
        )
    session.flush()
    for index, evidence_id in enumerate(EVIDENCE_IDS):
        store_commercial_signal(
            session,
            CommercialSignal(
                organization_id=ORG_ID,
                evidence_id=evidence_id,
                signal_type=SignalType.CORPORATE_CHANGE,
                title="Cloud security transformation",
                summary="Independent evidence for a cloud security capability gap.",
                confidence=0.82 - index * 0.02,
                collected_at=NOW - timedelta(hours=2),
                published_at=NOW - timedelta(hours=3),
                service_families=(CyberServiceFamily.CLOUD_SECURITY,),
                hypothesis_classes=(NeedHypothesisClass.CAPABILITY_GAP,),
                independence_key=f"source:api-source-{index}",
                mapping_rule_id="lot24-api-test-map",
                mapping_rule_version="1.0.0",
            ),
        )
    generate_need_hypotheses(session, ORG_ID, now=NOW)
    session.commit()
