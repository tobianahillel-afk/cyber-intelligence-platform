from __future__ import annotations

import json
from contextlib import contextmanager
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from typing import Iterator
from urllib.parse import urlsplit
from uuid import NAMESPACE_URL, uuid4, uuid5

import httpx
from sqlalchemy import select

from cip.adapters.sources.public_web.browser_client import BrowserPublicWebClient
from cip.adapters.sources.public_web.browser_fallback_governance import (
    AutomaticBrowserFallbackPolicy,
    build_browser_fallback_entry,
)
from cip.adapters.sources.public_web.browser_runtime import BrowserRenderLimits
from cip.adapters.sources.public_web.mapper import map_public_page
from cip.adapters.sources.public_web.provisioning import (
    AutomaticPublicWebPolicy,
    provision_public_web_target,
)
from cip.adapters.sources.public_web.structured_fetch_result import (
    structured_states_for_result,
)
from cip.adapters.sources.public_web.structured_state_capture import (
    PUBLIC_SCRIPT_STATE_EXTRACTOR_ID,
    StructuredStateCaptureLimits,
)
from cip.modules.organizations.domain.entities import Organization
from cip.modules.organizations.infrastructure.models import OrganizationRecord
from cip.modules.public_footprint.domain import PublicStructuredStateKind
from cip.modules.public_footprint.domain.scope import CrawlUsage
from cip.modules.public_footprint.infrastructure.models import PublicStructuredStateRecord
from cip.modules.public_footprint.infrastructure.projections import (
    persist_public_footprint_projections,
)
from cip.shared.persistence.metadata import get_metadata
from cip.shared.persistence.session import (
    create_database_engine,
    create_session_factory,
    session_scope,
)

_OFF_ORIGIN_HOST = "example.com"
_SECRET_MARKERS = ("accesstoken", "sessionid", "must-drop", "password", "cookie")
_HTML = """<!doctype html>
<html><head><meta charset="utf-8"><title>SA16 L11 live</title></head>
<body><h1>SA16 L11 rendered structured state</h1>
<script>
window.__INITIAL_STATE__ = {
  company: "SA16 Live Fixture",
  accessToken: "must-drop",
  nested: {region: "eu", sessionId: "must-drop"}
};
fetch("/json").then(r => r.json()).then(v => { window.fetchDone = !!v; });
const xhr = new XMLHttpRequest();
xhr.open("GET", "/xhr?source=sa16-l11");
xhr.send();
fetch("https://example.com/off-origin.json").catch(() => {});
</script></body></html>"""


class _FixtureHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def do_GET(self) -> None:  # noqa: N802 - stdlib handler contract
        path = urlsplit(self.path).path
        if path == "/robots.txt":
            self._send(
                b"User-agent: *\nAllow: /\n",
                content_type="text/plain; charset=utf-8",
            )
            return
        if path == "/app":
            self._send(_HTML.encode("utf-8"), content_type="text/html; charset=utf-8")
            return
        if path == "/json":
            self._send_json(
                {
                    "provider": "controlled-live-fixture",
                    "technology": "browser-fetch",
                    "accessToken": "must-drop",
                    "nested": {"region": "eu", "sessionId": "must-drop"},
                }
            )
            return
        if path == "/xhr":
            self._send_json(
                {
                    "provider": "controlled-live-fixture",
                    "transport": "xhr",
                    "password": "must-drop",
                    "evidence": {"kind": "public-json"},
                },
                content_type="application/problem+json",
            )
            return
        self._send(b"not found", status=404, content_type="text/plain")

    def log_message(self, format: str, *args: object) -> None:
        del format, args

    def _send_json(
        self,
        payload: object,
        *,
        content_type: str = "application/json",
    ) -> None:
        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        self._send(body, content_type=content_type)

    def _send(
        self,
        body: bytes,
        *,
        status: int = 200,
        content_type: str,
    ) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)
        self.wfile.flush()


@contextmanager
def _serve_fixture() -> Iterator[str]:
    server = ThreadingHTTPServer(("127.0.0.1", 0), _FixtureHandler)
    host, port = server.server_address[:2]
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://{host}:{port}/"
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()


def main() -> None:
    now = datetime.now(UTC)
    with _serve_fixture() as origin:
        fixture_url = f"{origin}app"
        organization = _organization(now, origin)
        target, browser_entry = _governed_browser_target(
            organization,
            fixture_url,
            now,
        )
        with httpx.Client(timeout=30.0, follow_redirects=False) as http_client:
            client = BrowserPublicWebClient(
                http_client,
                browser_entry,
                collected_at=now,
                limits=BrowserRenderLimits(
                    max_requests=24,
                    navigation_timeout_ms=20_000,
                    settle_timeout_ms=1_500,
                    structured_state=StructuredStateCaptureLimits(
                        max_json_responses=8,
                        max_response_bytes=32_768,
                        max_total_json_bytes=131_072,
                        max_script_states=5,
                        max_script_state_bytes=32_768,
                        max_total_script_bytes=65_536,
                    ),
                ),
            )
            robots = client.fetch_robots(target)
            result = client.fetch_page(
                target,
                fixture_url,
                robots,
                usage=CrawlUsage(),
            )
        states = structured_states_for_result(result)
        network_count, script_count = _assert_capture(states, origin)
        mapped = map_public_page(
            target,
            result,
            collection_job_id=uuid4(),
            collected_at=now,
            retention_until=now + timedelta(days=30),
            previous=None,
            adapter_id="public-web-browser",
        )
        if mapped.observation is None or mapped.observation.adapter_id != "public-web-browser":
            raise RuntimeError("SA16-L11 lost browser acquisition provenance")
        if len(mapped.projection.structured_states) != len(states):
            raise RuntimeError("SA16-L11 mapper lost captured structured state")
        persisted_count = _persist_and_verify(organization, mapped.projection, now)
    print(
        "SA-16 L11 live validation passed: "
        f"network_json={network_count} script_state={script_count} "
        f"persisted={persisted_count} off_origin_captured=0 secrets_promoted=0",
        flush=True,
    )


def _organization(now: datetime, origin: str) -> Organization:
    return Organization(
        id=uuid5(NAMESPACE_URL, origin),
        canonical_name="SA16-L11 controlled live fixture",
        legal_name=None,
        country_code=None,
        website_url=origin,
        registration_ids=(),
        created_at=now,
        updated_at=now,
    )


def _governed_browser_target(
    organization: Organization,
    fixture_url: str,
    now: datetime,
):
    static_policy = AutomaticPublicWebPolicy(
        authorization_reference="sa16-l11-static-live-approval",
        reviewed_at=now,
        discover_sitemaps=False,
        discover_feeds=False,
        max_link_depth=0,
        max_pages=1,
        max_total_bytes=2_000_000,
        max_resource_bytes=1_000_000,
        max_redirects=2,
    )
    provisioned = provision_public_web_target(
        organization,
        static_policy,
        first_crawl_at=now,
    )
    target = replace(
        provisioned.target,
        seed_urls=(fixture_url,),
        discover_security_txt=False,
        discover_sitemaps=False,
        discover_feeds=False,
        max_pages=1,
    )
    browser_policy = AutomaticBrowserFallbackPolicy(
        authorization_reference="sa16-l11-browser-live-approval",
        reviewed_at=now,
        min_static_text_chars=1,
        max_browser_pages=1,
    )
    return (
        target,
        build_browser_fallback_entry(
            provisioned.source_entry,
            target,
            browser_policy,
        ),
    )


def _assert_capture(states, origin: str) -> tuple[int, int]:
    if not states:
        raise RuntimeError("SA16-L11 Chromium captured no structured state")
    network = [
        state for state in states if state.kind is PublicStructuredStateKind.NETWORK_JSON
    ]
    scripts = [
        state for state in states if state.kind is PublicStructuredStateKind.SCRIPT_STATE
    ]
    if len(network) < 2:
        raise RuntimeError(
            f"SA16-L11 expected at least 2 JSON responses, got {len(network)}"
        )
    if len(scripts) != 1:
        raise RuntimeError(
            f"SA16-L11 expected exactly 1 script state, got {len(scripts)}"
        )
    if scripts[0].source_locator != "window.__INITIAL_STATE__":
        raise RuntimeError("SA16-L11 captured an unexpected script-state locator")
    if scripts[0].extractor_id != PUBLIC_SCRIPT_STATE_EXTRACTOR_ID:
        raise RuntimeError("SA16-L11 lost reviewed script extractor provenance")
    source_urls = tuple(state.source_url or "" for state in network)
    if not any(url.startswith(f"{origin}json") for url in source_urls):
        raise RuntimeError("SA16-L11 did not capture the same-origin fetch JSON response")
    if not any(url.startswith(f"{origin}xhr?") for url in source_urls):
        raise RuntimeError("SA16-L11 did not capture the same-origin XHR JSON response")
    if any(_OFF_ORIGIN_HOST in url for url in source_urls):
        raise RuntimeError("SA16-L11 captured an off-origin response")
    for state in states:
        payload = state.payload_json.casefold()
        if any(marker in payload for marker in _SECRET_MARKERS):
            raise RuntimeError("SA16-L11 promoted sensitive structured state")
        json.loads(state.payload_json)
    return len(network), len(scripts)


def _persist_and_verify(organization, projection, now: datetime) -> int:
    engine = create_database_engine("sqlite+pysqlite:///:memory:")
    get_metadata().create_all(engine)
    factory = create_session_factory(engine)
    with session_scope(factory) as session:
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
        persist_public_footprint_projections(session, (projection,), now=now)
    with session_scope(factory) as session:
        records = tuple(session.scalars(select(PublicStructuredStateRecord)))
        if len(records) != len(projection.structured_states):
            raise RuntimeError("SA16-L11 persistence count differs from projection")
        for record in records:
            if record.organization_id != organization.id:
                raise RuntimeError("SA16-L11 persistence lost organization provenance")
            if record.resource_version_id != projection.version.id:
                raise RuntimeError("SA16-L11 persistence lost version provenance")
            payload = record.payload_json.casefold()
            if any(marker in payload for marker in _SECRET_MARKERS):
                raise RuntimeError("SA16-L11 persisted sensitive structured state")
        return len(records)


if __name__ == "__main__":
    main()