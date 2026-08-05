from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from cip.modules.collection_orchestration.application.ports import AdapterCollectionBatch
from cip.modules.collection_orchestration.application.worker import (
    WorkerStatus,
    run_worker_once,
)
from cip.modules.collection_orchestration.domain.models import CollectionJob, SourceSchedule
from cip.modules.collection_orchestration.infrastructure.models import (
    CollectionCheckpointRecord,
)
from cip.modules.collection_orchestration.infrastructure.repository import enqueue_job
from cip.modules.data_governance.infrastructure.retention_loader import load_retention_policy
from cip.modules.opportunities.infrastructure.models import (
    CommercialSignalRecord,
    OpportunityRecord,
)
from cip.modules.organizations.infrastructure.models import OrganizationRecord
from cip.modules.public_footprint.domain import (
    ClaimEvidenceBasis,
    ClaimResolutionStatus,
    DiscoveryMethod,
    PublicClaim,
    PublicClaimType,
    PublicFootprintProjection,
    PublicResource,
    PublicResourceKind,
    PublicResourceVersion,
    ResourceRetrievalState,
)
from cip.modules.public_footprint.infrastructure.models import (
    PublicClaimRecord,
    PublicResourceRecord,
    PublicResourceVersionRecord,
)
from cip.modules.raw_observations.domain.entities import RawObservation
from cip.modules.raw_observations.infrastructure.models import RawObservationRecord
from cip.modules.source_governance.domain.models import DataCategory
from cip.modules.source_governance.infrastructure.persistence import sync_source_registry
from cip.modules.source_governance.infrastructure.registry import load_source_registry
from cip.modules.source_portfolio.application.service import sync_source_portfolio
from cip.modules.source_portfolio.infrastructure.registry import load_source_portfolio
from cip.shared.persistence.metadata import get_metadata
from cip.shared.persistence.session import session_scope

NOW = datetime(2026, 8, 5, 21, 30, tzinfo=UTC)
ORGANIZATION_ID = UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")
CONTENT_HASH = "a" * 64


def test_public_footprint_runs_through_durable_worker_without_current_opportunity() -> None:
    factory = _factory()
    with session_scope(factory) as session:
        sync_source_registry(
            session,
            load_source_registry(Path("policies/sources.example.yml")),
        )
        sync_source_portfolio(
            session,
            load_source_portfolio(Path("policies/source_portfolio.yml")),
            now=NOW,
        )
        session.add(
            OrganizationRecord(
                id=ORGANIZATION_ID,
                canonical_name="Cybersecurity and Infrastructure Security Agency",
                legal_name=None,
                country_code="US",
                website_url="https://www.cisa.gov",
                registration_ids=[],
                created_at=NOW,
                updated_at=NOW,
            )
        )
        schedule = SourceSchedule(
            source_id="cisa-kev",
            adapter_id="public-footprint-reference",
            interval_seconds=3_600,
        )
        assert enqueue_job(
            session,
            CollectionJob.from_schedule(schedule, scheduled_for=NOW),
        )

    adapter = PublicFootprintReferenceAdapter()
    outcome = run_worker_once(
        factory,
        worker_id="public-footprint-worker-test",
        adapters={(adapter.source_id, adapter.adapter_id): adapter},
        retention_policy=load_retention_policy(Path("policies/retention.yml")),
        clock=lambda: NOW + timedelta(seconds=1),
    )

    assert outcome.status is WorkerStatus.SUCCEEDED
    assert outcome.observations_written == 1
    with factory() as session:
        assert _count(session, RawObservationRecord) == 1
        assert _count(session, PublicResourceRecord) == 1
        assert _count(session, PublicResourceVersionRecord) == 1
        assert _count(session, PublicClaimRecord) == 1
        assert _count(session, CommercialSignalRecord) == 0
        assert _count(session, OpportunityRecord) == 0

        resource = session.scalar(select(PublicResourceRecord))
        version = session.scalar(select(PublicResourceVersionRecord))
        claim = session.scalar(select(PublicClaimRecord))
        assert resource is not None
        assert version is not None
        assert claim is not None
        assert resource.organization_id == ORGANIZATION_ID
        assert resource.canonical_url == (
            "https://www.cisa.gov/known-exploited-vulnerabilities-catalog"
        )
        assert version.resource_id == resource.id
        assert version.content_hash_sha256 == CONTENT_HASH
        assert claim.resource_version_id == version.id
        assert claim.resolution_status == ClaimResolutionStatus.OBSERVED.value

        checkpoint = session.get(
            CollectionCheckpointRecord,
            ("cisa-kev", "public-footprint-reference"),
        )
        assert checkpoint is not None
        assert checkpoint.payload == {"fixture_revision": 1}


class PublicFootprintReferenceAdapter:
    source_id = "cisa-kev"
    adapter_id = "public-footprint-reference"
    data_category = DataCategory.VULNERABILITY_METADATA

    def collect(
        self,
        *,
        collection_job_id: UUID,
        checkpoint_payload: Mapping[str, object] | None,
        collected_at: datetime,
        retention_until: datetime,
    ) -> AdapterCollectionBatch:
        del checkpoint_payload
        resource = PublicResource(
            organization_id=ORGANIZATION_ID,
            source_id=self.source_id,
            source_record_key="kev-catalog",
            canonical_url=(
                "https://www.cisa.gov/known-exploited-vulnerabilities-catalog"
            ),
            source_url=(
                "https://www.cisa.gov/sites/default/files/feeds/"
                "known_exploited_vulnerabilities.json"
            ),
            kind=PublicResourceKind.WEB_PAGE,
            discovery_method=DiscoveryMethod.DIRECT,
            first_discovered_at=collected_at,
            last_seen_at=collected_at,
            retrieval_state=ResourceRetrievalState.FETCHED,
            title="Known Exploited Vulnerabilities Catalog",
        )
        version = PublicResourceVersion(
            resource_key=resource.identity_key,
            source_url=resource.canonical_url,
            content_hash_sha256=CONTENT_HASH,
            fetched_at=collected_at,
            mime_type="text/html",
            byte_size=1_024,
            title="Known Exploited Vulnerabilities Catalog",
            extracted_text_hash_sha256="b" * 64,
            excerpt="Catalog of vulnerabilities known to be exploited in the wild.",
            source_locator="main content",
        )
        claim = PublicClaim(
            organization_id=ORGANIZATION_ID,
            resource_version_id=version.id,
            claim_type=PublicClaimType.SECURITY_OR_COMPLIANCE_OBJECTIVE,
            statement="CISA publishes a catalog of known exploited vulnerabilities.",
            evidence_basis=ClaimEvidenceBasis.TARGET_CONTENT,
            resolution_status=ClaimResolutionStatus.OBSERVED,
            confidence=1.0,
            corroboration_group_key=resource.corroboration_group_key,
            source_locator="main content",
            excerpt="Known Exploited Vulnerabilities Catalog",
        )
        observation = RawObservation(
            source_id=self.source_id,
            adapter_id=self.adapter_id,
            adapter_version="1",
            collection_job_id=collection_job_id,
            source_record_type="public_resource",
            source_record_key="kev-catalog",
            source_url=resource.source_url,
            payload_hash_sha256=CONTENT_HASH,
            data_categories=frozenset({self.data_category}),
            collected_at=collected_at,
            observed_at=collected_at,
            source_updated_at=collected_at,
            schema_fingerprint="public-footprint-reference-v1",
            content_language="en",
            retention_until=retention_until,
        )
        return AdapterCollectionBatch(
            observations=(observation,),
            checkpoint_payload={"fixture_revision": 1},
            not_modified=False,
            public_footprint_projections=(
                PublicFootprintProjection(
                    resource=resource,
                    version=version,
                    claims=(claim,),
                ),
            ),
        )


def _factory() -> sessionmaker[Session]:
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    get_metadata().create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)


def _count(session: Session, record_type: type[object]) -> int:
    return int(session.scalar(select(func.count()).select_from(record_type)) or 0)
