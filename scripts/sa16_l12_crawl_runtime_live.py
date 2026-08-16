from __future__ import annotations

from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Lock, Thread
from time import sleep
from urllib.parse import urlsplit
from uuid import NAMESPACE_URL, uuid4, uuid5

from cip.adapters.sources.public_web.provisioning import (
    AutomaticPublicWebPolicy,
    provision_public_web_target,
)
from cip.modules.collection_orchestration.application.ports import (
    AdapterOperationalMetrics,
    AdapterPartialExecutionError,
)
from cip.modules.collection_orchestration.application.public_web_adapter import PublicWebAdapter
from cip.modules.organizations.domain.entities import Organization

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
    ).encode("utf-8")


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
        concurrent = _adapter(provisioned.source_entry, concurrency_target).collect(
            collection_job_id=uuid4(),
            checkpoint_payload=None,
            collected_at=now,
            retention_until=now + timedelta(days=30),
        )
        concurrent_values = _metric_values(concurrent.operational_metrics)
        if concurrent_values["fetched_pages"] != 4:
            raise RuntimeError("SA16-L12 did not fetch all admitted concurrent pages")
        if concurrent_values["effective_concurrency"] != 4:
            raise RuntimeError("SA16-L12 did not apply configured static concurrency")
        if concurrent_values["max_concurrency_used"] != 4:
            raise RuntimeError("SA16-L12 did not admit the expected deterministic wave")
        if _max_active_requests < 2:
            raise RuntimeError("SA16-L12 live fixture observed no real parallel requests")
        if concurrent_values["deadline_exceeded"] is not False:
            raise RuntimeError("SA16-L12 healthy concurrent crawl hit its deadline")

        deadline_target = replace(
            provisioned.target,
            seed_urls=(f"{origin}00-fast", f"{origin}{_SLOW_PATH.lstrip('/')}"),
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
        if not isinstance(pages, dict) or tuple(pages) != (f"{origin}00-fast",):
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
        f"real_parallelism={_max_active_requests} fetched=4 "
        "partial_checkpoint_pages=1 deadline_retryable=1",
        flush=True,
    )


def _adapter(entry: object, target: object) -> PublicWebAdapter:
    return PublicWebAdapter(entry, target, timeout_seconds=10.0)  # type: ignore[arg-type]


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
        discover_security_txt=False,
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


if __name__ == "__main__":
    main()
