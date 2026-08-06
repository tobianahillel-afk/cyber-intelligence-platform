from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID

import httpx
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from cip.adapters.sources.public_web.registry import PublicWebTarget
from cip.modules.collection_orchestration.application.public_web_adapter import (
    PublicWebAdapter,
)
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
from cip.modules.public_footprint.infrastructure.models import (
    PublicClaimRecord,
    PublicResourceRecord,
    PublicResourceVersionRecord,
)
from cip.modules.raw_observations.infrastructure.models import RawObservationRecord
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
from cip.shared.persistence.metadata import get_metadata
from cip.shared.persistence.session import session_scope

NOW = datetime(2026, 8, 5, 22, 30, tzinfo=UTC)
ORGANIZATION_ID = UUID("eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee")
SOURCE_ID = "public-web-example"
SITEMAP = b"""<?xml version="1.0"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://example.com/public/security</loc></url>
</urlset>
"""
PAGE = b"""<html lang="en"><head><title>Security program</title></head>
<body>Our architecture uses Azure and follows a zero trust objective.</body></html>"""


def test_public_web_adapter_persists_once_and_replays_without_duplicates() -> None:
    factory = _factory()
    entry = _entry()
    target = _target()
    with session_scope(factory) as session:
        sync_source_registry(session, (entry,))
        session.add(
            OrganizationRecord(
                id=ORGANIZATION_ID,
                canonical_name="Example Corp",
                legal_name="Example Corp SAS",
                country_code="FR",
                website_url="https://example.com",
                registration_ids=[],
                created_at=NOW,
                updated_at=NOW,
            )
        )
        _enqueue(session, scheduled_for=NOW)

    first = run_worker_once(
        factory,
        worker_id="public-web-adapter-test",
        adapters={
            (SOURCE_ID, PublicWebAdapter.adapter_id): _adapter(entry, target),
        },
        retention_policy=load_retention_policy(Path("policies/retention.yml")),
        clock=lambda: NOW + timedelta(seconds=1),
    )

    assert first.status is WorkerStatus.SUCCEEDED
    assert first.observations_written == 1
    with session_scope(factory) as session:
        _enqueue(session, scheduled_for=NOW + timedelta(hours=1))

    replay = run_worker_once(
        factory,
        worker_id="public-web-adapter-test",
        adapters={
            (SOURCE_ID, PublicWebAdapter.adapter_id): _adapter(entry, target),
        },
        retention_policy=load_retention_policy(Path("policies/retention.yml")),
        clock=lambda: NOW + timedelta(hours=1, seconds=1),
    )

    assert replay.status is WorkerStatus.NOT_MODIFIED
    assert replay.observations_written == 0
    with factory() as session:
        assert _count(session, RawObservationRecord) == 1
        assert _count(session, PublicResourceRecord) == 1
        assert _count(session, PublicResourceVersionRecord) == 1
        assert _count(session, PublicClaimRecord) == 2
        assert _count(session, CommercialSignalRecord) == 0
        assert _count(session, OpportunityRecord) == 0

        resource = session.scalar(select(PublicResourceRecord))
        assert resource is not None
        assert resource.canonical_url == "https://example.com/public/security"
        checkpoint = session.get(
            CollectionCheckpointRecord,
            (SOURCE_ID, PublicWebAdapter.adapter_id),
        )
        assert checkpoint is not None
        pages = checkpoint.payload["pages"]
        assert isinstance(pages, dict)
        page_state = pages["https://example.com/public/security"]
        assert isinstance(page_state, dict)
        assert page_state["canonical_url"] == (
            "https://example.com/public/security"
        )


def _adapter(
    entry: SourceRegistryEntry,
    target: PublicWebTarget,
) -> PublicWebAdapter:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(
                200,
                headers={"content-type": "text/plain"},
                content=b"User-agent: *\nAllow: /\n",
            )
        if request.url.path == "/sitemap.xml":
            return httpx.Response(
                200,
                headers={"content-type": "application/xml"},
                content=SITEMAP,
            )
        if request.url.path == "/public/security":
            return httpx.Response(
                200,
                headers={"content-type": "text/html; charset=utf-8"},
                content=PAGE,
            )
        raise AssertionError(f"unexpected request: {request.url}")

    return PublicWebAdapter(
        entry,
        target,
        transport=httpx.MockTransport(handler),
    )


def _entry() -> SourceRegistryEntry:
    return SourceRegistryEntry(
        policy=SourcePolicy(
            id=SOURCE_ID,
            name="Example public website",
            base_url="https://example.com",
            status=SourceStatus.ENABLED,
            source_type=SourceType.STATIC_HTTP,
            owner="Example Corp",
            terms_url="https://example.com/terms",
            allowed_data_categories=frozenset(
                {
                    DataCategory.OFFICIAL_DOCUMENT_DISCOVERY,
                    DataCategory.TECHNOLOGY_OBSERVATION,
                }
            ),
            prohibited_data_categories=frozenset(
                {
                    DataCategory.CREDENTIAL,
                    DataCategory.PRIVATE_COMMUNICATION,
                    DataCategory.PRIVATE_PERSONAL_DATA,
                    DataCategory.RESTRICTED_CONTENT,
                    DataCategory.VICTIM_FILE,
                }
            ),
            raw_content_storage=False,
            human_review_required=False,
        ),
        authorization=SourceAuthorization(
            status=AuthorizationStatus.APPROVED,
            document_reference="approval:public-web-example",
            reviewed_at=NOW - timedelta(days=1),
            expires_at=NOW + timedelta(days=30),
            approved_hosts=frozenset({"example.com"}),
            approved_path_prefixes=("/",),
            approved_purposes=frozenset({"corporate-public-footprint"}),
            automated_collection_allowed=True,
            raw_storage_allowed=False,
        ),
        economics={"cost_model": "free"},
    )


def _target() -> PublicWebTarget:
    return PublicWebTarget(
        id=SOURCE_ID,
        organization_id=ORGANIZATION_ID,
        canonical_name="Example Corp",
        base_url="https://example.com",
        sitemap_urls=("https://example.com/sitemap.xml",),
        allowed_path_prefixes=("/public",),
        enabled=True,
        authorization_reference="approval:public-web-example",
        authorization_reviewed_at=NOW - timedelta(days=1),
        authorization_expires_at=NOW + timedelta(days=30),
        terms_url="https://example.com/terms",
        max_pages=10,
        max_total_bytes=1_000_000,
        max_resource_bytes=100_000,
        max_redirects=2,
    )


def _enqueue(session: Session, *, scheduled_for: datetime) -> None:
    schedule = SourceSchedule(
        source_id=SOURCE_ID,
        adapter_id=PublicWebAdapter.adapter_id,
        interval_seconds=3_600,
    )
    assert enqueue_job(
        session,
        CollectionJob.from_schedule(schedule, scheduled_for=scheduled_for),
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
