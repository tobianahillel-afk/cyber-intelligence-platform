from __future__ import annotations

from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Lock, Thread
from time import sleep
from urllib.parse import urlsplit
from uuid import NAMESPACE_URL, uuid4, uuid5

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from cip.adapters.sources.public_web.provisioning import (
    AutomaticPublicWebPolicy,
    provision_public_web_target,
)
from cip.adapters.sources.public_web.registry import PublicWebTarget
from cip.modules.collection_orchestration.application.ports import (
    AdapterOperationalMetrics,
    AdapterPartialExecutionError,
)
from cip.modules.collection_orchestration.application.public_web_adapter import PublicWebAdapter
from cip.modules.collection_orchestration.application.worker import WorkerStatus, run_worker_once
from cip.modules.collection_orchestration.domain.models import CollectionJob, SourceSchedule
from cip.modules.collection_orchestration.infrastructure.repository import enqueue_job
from cip.modules.data_governance.infrastructure.retention_loader import load_retention_policy
from cip.modules.organizations.domain.entities import Organization
from cip.modules.organizations.infrastructure.models import OrganizationRecord
from cip.modules.source_governance.infrastructure.persistence import sync_source_registry
from cip.modules.source_governance.infrastructure.registry import SourceRegistryEntry
from cip.modules.source_portfolio.application.service import get_source_health, sync_source_portfolio
from cip.modules.source_portfolio.domain.models import (
    AdapterCapabilityManifest,
    CatalogStatus,
    CollectionMode,
    SourceCatalogEntry,
)
from cip.shared.persistence.metadata import get_metadata
from cip.shared.persistence.session import session_scope

_FIXTURE_HOST = "sa16-l12-fixture.example"
_FAST_PATHS = ("/00-fast", "/01-fast", "/02-fast", "/03-fast")
_SLOW_PATH = "/99-deadline"
_counter_lock = Lock()
_active_requests = 0
_max_active_requests = 0


class _LiveServer(ThreadingHTTPServer):
    daemon_threads = True


class _FixtureHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def do_GET(self) -> None:
        path = urlsplit(self.path).path
        if path == "/robots.txt":
            self._send(b"User-agent: *\nAllow: /\n", content_type="text/plain")
            return
        if path in _FAST_PATHS:
            self._tracked_delay(0.30)
            self._send(_page(path), content_type="text/html; charset=utf-8")
            return
        if path == _SLOW_PATH:
            sleep(1.50)
            self._send(_page(path), content_type="text/html; charset=utf-8")
            return
        self._send(b"not found", status=404, content_type="text/plain")

    def log_message(self, format: str, *args: object) -> None:
        del format, args

    def _tracked_delay(self, seconds: float) -> None:
        global _active_requests, _max_active_requests
        with _counter_lock:
            _active_requests += 1
            _max_active_requests = max(_max_active_requests, _active_requests)
        try:
            sleep(seconds)
        finally:
            with _counter_lock:
                _active_requests -= 1

    def _send(
        self,
        body: bytes,
        *,
        status: int = 200,
        content_type: str,
    ) -> None:
        try:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)
            self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            return


def _page(path: str) -> bytes:
    return (
        "<!doctype html><html><head><title>SA16 L12</title></head>"
        f"<body><h1>{path}</h1><p>controlled public crawl evidence</p></body></html>"
    ).encode()


@contextmanager
def _serve_fixture() -> Iterator[str]:
    server = _LiveServer(("127.0.0.1", 0), _FixtureHandler)
    port = int(server.server_address[1])
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://{_FIXTURE_HOST}:{port}/"
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()


def main() -> None:
    global _max_active_requests
    now = datetime.now(UTC)
    with _serve_fixture() as origin:
        organization = _organization(now, origin)
        provisioned = provision_public_web_target(
            organization,
            _base_policy(now),
            first_crawl_at=now,
        )
        concurrency_target = replace(
            provisioned.target,
            id=provisioned.target.source_id,
            seed_urls=tuple(f"{origin}{path.lstrip('/')}" for path in _FAST_PATHS),
            discover_security_txt=False,
            discover_sitemaps=False,
            discover_feeds=False,
            max_link_depth=0,
            max_pages=4,
            max_crawl_concurrency=4,
            crawl_deadline_seconds=10,
        )
        _max_active_requests = 0
        concurrent_values = _run_worker_live(
            provisioned.source_entry,
            concurrency_target,
            organization,
            now,
        )
        if concurrent_values["fetched_pages"] != 4:
            raise RuntimeError("SA16-L12 did not persist all concurrent page metrics")
        if concurrent_values["effective_concurrency"] != 4:
            raise RuntimeError("SA16-L12 did not persist effective concurrency")
        if concurrent_values["max_concurrency_used"] != 4:
            raise RuntimeError("SA16-L12 did not persist actual concurrency")
        if _max_active_requests < 2:
            raise RuntimeError("SA16-L12 live fixture observed no real parallel requests")
        if concurrent_values["deadline_exceeded"] is not False:
            raise RuntimeError("SA16-L12 healthy concurrent crawl hit its deadline")

        fast_url = f"{origin}00-fast"
        deadline_target = replace(
            provisioned.target,
            seed_urls=(fast_url, f"{origin}{_SLOW_PATH.lstrip('/')}"),
            discover_security_txt=False,
            discover_sitemaps=False,
            discover_feeds=False,
            max_link_depth=0,
            max_pages=2,
            max_crawl_concurrency=1,
            crawl_deadline_seconds=1,
        )
        partial = _expect_partial_deadline(
            _adapter(provisioned.source_entry, deadline_target),
            now,
        )
        pages = partial.batch.checkpoint_payload.get("pages")
        if not isinstance(pages, dict) or set(pages) != {fast_url}:
            raise RuntimeError("SA16-L12 checkpoint included incomplete deadline work")
        partial_values = _metric_values(partial.batch.operational_metrics)
        if partial_values["deadline_exceeded"] is not True:
            raise RuntimeError("SA16-L12 partial result lost deadline telemetry")
        if partial_values["fetched_pages"] != 1:
            raise RuntimeError("SA16-L12 partial result lost completed work")
        if partial.error_code != "crawl_deadline_exceeded" or not partial.retryable:
            raise RuntimeError("SA16-L12 deadline classification is not retryable")

    print(
        "SA-16 L12 live validation passed: "
        f"real_parallelism={_max_active_requests} fetched=4 metrics_persisted=1 "
        "partial_checkpoint_pages=1 deadline_retryable=1",
        flush=True,
    )


def _run_worker_live(
    entry: SourceRegistryEntry,
    target: PublicWebTarget,
    organization: Organization,
    now: datetime,
) -> Mapping[str, object]:
    factory = _factory()
    adapter = _adapter(entry, target)
    with session_scope(factory) as session:
        sync_source_registry(session, (entry,))
        session.add(
            OrganizationRecord(
                id=organization.id,
                canonical_name=organization.canonical_name,
                legal_name=organization.legal_name,
                country_code=organization.country_code,
                website_url=organization.website_url,
                registration_ids=list(organization.registration_ids),
                created_at=now,
                updated_at=now,
            )
        )
        sync_source_portfolio(session, (_catalog_entry(target, now),), now=now)
        schedule = SourceSchedule(
            source_id=target.id,
            adapter_id=PublicWebAdapter.adapter_id,
            interval_seconds=300,
        )
        if not enqueue_job(
            session,
            CollectionJob.from_schedule(schedule, scheduled_for=now),
        ):
            raise RuntimeError("SA16-L12 failed to enqueue live worker job")
    outcome = run_worker_once(
        factory,
        worker_id="sa16-l12-live-worker",
        adapters={(target.id, PublicWebAdapter.adapter_id): adapter},
        retention_policy=load_retention_policy(Path("policies/retention.yml")),
        clock=lambda: now + timedelta(seconds=1),
    )
    if outcome.status is not WorkerStatus.SUCCEEDED:
        raise RuntimeError(f"SA16-L12 live worker failed: {outcome.status.value}")
    with factory() as session:
        health = get_source_health(session, target.id)
        metrics = health.operational_metrics
        if metrics.get("namespace") != "public_web.crawl.v1":
            raise RuntimeError("SA16-L12 live worker did not persist crawl metrics")
        values = metrics.get("values")
        if not isinstance(values, dict):
            raise RuntimeError("SA16-L12 persisted crawl metrics are malformed")
        return values


def _catalog_entry(target: PublicWebTarget, now: datetime) -> SourceCatalogEntry:
    return SourceCatalogEntry(
        source_id=target.id,
        display_name="SA16-L12 controlled public web target",
        canonical_url=f"https://{_FIXTURE_HOST}/",
        category="public_web",
        status=CatalogStatus.EXECUTABLE,
        freshness_max_age_seconds=300,
        commercial_use_cases=("corporate_public_footprint",),
        adapter=AdapterCapabilityManifest(
            source_id=target.id,
            adapter_id=PublicWebAdapter.adapter_id,
            adapter_version="1",
            provider_schema_version="sa16-l12-live",
            modes=frozenset({CollectionMode.INCREMENTAL_CURSOR}),
            canonical_output_types=("raw_observation", "public_footprint_projection"),
            supports_corrections=True,
            supports_tombstones=True,
            cost_per_request=0,
        ),
        authorization_expires_at=now + timedelta(days=1),
        monthly_cost_limit=0,
    )


def _adapter(entry: SourceRegistryEntry, target: PublicWebTarget) -> PublicWebAdapter:
    return PublicWebAdapter(entry, target, timeout_seconds=10.0)


def _expect_partial_deadline(
    adapter: PublicWebAdapter,
    now: datetime,
) -> AdapterPartialExecutionError:
    try:
        adapter.collect(
            collection_job_id=uuid4(),
            checkpoint_payload=None,
            collected_at=now,
            retention_until=now + timedelta(days=30),
        )
    except AdapterPartialExecutionError as exc:
        return exc
    raise RuntimeError("SA16-L12 deadline path returned false success")


def _metric_values(metrics: AdapterOperationalMetrics | None) -> Mapping[str, object]:
    if metrics is None or metrics.namespace != "public_web.crawl.v1":
        raise RuntimeError("SA16-L12 crawl metrics are missing")
    return metrics.values


def _organization(now: datetime, origin: str) -> Organization:
    return Organization(
        id=uuid5(NAMESPACE_URL, origin),
        canonical_name="SA16-L12 controlled live fixture",
        legal_name=None,
        country_code=None,
        website_url=origin,
        registration_ids=(),
        created_at=now,
        updated_at=now,
    )


def _base_policy(now: datetime) -> AutomaticPublicWebPolicy:
    return AutomaticPublicWebPolicy(
        authorization_reference="sa16-l12-live-approval",
        reviewed_at=now,
        discover_sitemaps=False,
        discover_feeds=False,
        max_link_depth=0,
        max_pages=4,
        max_total_bytes=2_000_000,
        max_resource_bytes=250_000,
        max_redirects=2,
        crawl_deadline_seconds=10,
        max_crawl_concurrency=4,
    )


def _factory() -> sessionmaker[Session]:
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    get_metadata().create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)


if __name__ == "__main__":
    main()
