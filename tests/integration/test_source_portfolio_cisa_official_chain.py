from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from cip.modules.collection_orchestration.application import adapters as adapters_module
from cip.modules.collection_orchestration.application.adapters import CisaKevAdapter
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
from cip.modules.raw_observations.infrastructure.models import RawObservationRecord
from cip.modules.source_governance.infrastructure.persistence import sync_source_registry
from cip.modules.source_governance.infrastructure.registry import load_source_registry
from cip.modules.source_portfolio.application.service import (
    get_source_health,
    summarize_source_value,
    sync_source_portfolio,
)
from cip.modules.source_portfolio.domain.models import FreshnessState
from cip.modules.source_portfolio.infrastructure.registry import load_source_portfolio
from cip.shared.persistence.metadata import get_metadata
from cip.shared.persistence.session import session_scope

NOW = datetime(2026, 8, 5, 10, 0, tzinfo=UTC)


def test_cisa_official_adapter_runs_end_to_end_without_external_network(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    factory = _factory()
    entries = load_source_registry(Path("policies/sources.example.yml"))
    cisa_entry = next(entry for entry in entries if entry.policy.id == "cisa-kev")
    with session_scope(factory) as session:
        sync_source_registry(session, entries)
        sync_source_portfolio(
            session,
            load_source_portfolio(Path("policies/source_portfolio.yml")),
            now=NOW,
        )
        schedule = SourceSchedule(
            source_id="cisa-kev",
            adapter_id="cisa-kev-feed",
            interval_seconds=900,
        )
        assert enqueue_job(
            session,
            CollectionJob.from_schedule(schedule, scheduled_for=NOW),
        )

    requests: list[httpx.Request] = []
    real_client = httpx.Client

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200,
            request=request,
            headers={
                "content-type": "application/json",
                "etag": '"kev-v1"',
                "last-modified": "Wed, 05 Aug 2026 09:00:00 GMT",
            },
            json={
                "title": "CISA Known Exploited Vulnerabilities Catalog",
                "catalogVersion": "2026.08.05",
                "dateReleased": "2026-08-05T09:00:00Z",
                "count": 1,
                "vulnerabilities": [
                    {
                        "cveID": "CVE-2026-12345",
                        "vendorProject": "Example Vendor",
                        "product": "Example Product",
                        "vulnerabilityName": "Example vulnerability",
                        "dateAdded": "2026-08-01",
                        "shortDescription": "A validated KEV test record.",
                        "requiredAction": "Apply vendor mitigations.",
                        "dueDate": "2026-08-22",
                        "knownRansomwareCampaignUse": "Unknown",
                        "notes": "",
                        "cwes": ["CWE-79"],
                    }
                ],
            },
        )

    def client_factory(*args: object, **kwargs: object) -> httpx.Client:
        kwargs.pop("transport", None)
        return real_client(
            *args,
            **kwargs,
            transport=httpx.MockTransport(handler),
        )

    monkeypatch.setattr(adapters_module.httpx, "Client", client_factory)
    adapter = CisaKevAdapter(cisa_entry, timeout_seconds=5)
    outcome = run_worker_once(
        factory,
        worker_id="cisa-official-test",
        adapters={(adapter.source_id, adapter.adapter_id): adapter},
        retention_policy=load_retention_policy(Path("policies/retention.yml")),
        clock=lambda: NOW + timedelta(seconds=1),
    )

    assert outcome.status is WorkerStatus.SUCCEEDED
    assert outcome.observations_written == 1
    assert len(requests) == 1
    assert requests[0].headers["accept"] == "application/json"
    with factory() as session:
        observation = session.scalar(select(RawObservationRecord))
        assert observation is not None
        assert observation.source_record_key == "CVE-2026-12345"
        checkpoint = session.get(
            CollectionCheckpointRecord,
            ("cisa-kev", "cisa-kev-feed"),
        )
        assert checkpoint is not None
        assert checkpoint.payload == {
            "etag": '"kev-v1"',
            "last_modified": "Wed, 05 Aug 2026 09:00:00 GMT",
            "catalog_version": "2026.08.05",
        }
        assert session.scalar(select(func.count(RawObservationRecord.id))) == 1
        health = get_source_health(session, "cisa-kev")
        assert health.freshness_state is FreshnessState.FRESH
        value = summarize_source_value(session, source_id="cisa-kev")
        assert value.executions == 1
        assert value.observations_written == 1


def _factory() -> sessionmaker[Session]:
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    get_metadata().create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)
