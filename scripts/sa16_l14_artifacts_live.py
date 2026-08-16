from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from tempfile import gettempdir
from threading import Thread
from urllib.parse import urlsplit
from uuid import UUID, uuid4

import httpx
from sqlalchemy import select

from cip.adapters.sources.public_web.artifact_context import BrowserArtifactExecutionContext
from cip.adapters.sources.public_web.browser_action_executor import (
    execute_public_browser_action_plan,
)
from cip.adapters.sources.public_web.registry import PublicWebTarget
from cip.modules.organizations.infrastructure.models import OrganizationRecord
from cip.modules.public_footprint.domain.artifacts import (
    BrowserArtifactKind,
    BrowserScreenshotMode,
)
from cip.modules.public_footprint.domain.browser_actions import (
    BrowserActionKind,
    BrowserActionPlan,
    BrowserActionStep,
    BrowserHttpMethod,
    BrowserStepState,
    BrowserTransitionRule,
)
from cip.modules.public_footprint.domain.models import PublicResourceKind
from cip.modules.public_footprint.infrastructure.artifact_persistence import (
    load_browser_artifacts_for_plan,
    persist_browser_artifact,
)
from cip.modules.public_footprint.infrastructure.browser_action_persistence import (
    persist_browser_action_plan,
    save_browser_action_checkpoint,
)
from cip.modules.public_footprint.infrastructure.models import PublicResourceRecord
from cip.modules.public_footprint.infrastructure.projections import (
    persist_public_footprint_projections,
)
from cip.modules.source_governance.domain.models import (
    AuthorizationStatus,
    DataCategory,
    HttpMethod,
    SourceAuthorization,
    SourcePolicy,
    SourceStatus,
    SourceType,
)
from cip.modules.source_governance.infrastructure.registry import SourceRegistryEntry
from cip.shared.persistence.metadata import get_metadata
from cip.shared.persistence.session import (
    create_database_engine,
    create_session_factory,
    session_scope,
)

_FIXTURE_HOST = "sa16-l14-fixture.example"
_REPORT = b"SA16-L14 controlled public document\nquarantine parser projection proof\n"


class _FixtureHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def do_GET(self) -> None:
        path = urlsplit(self.path).path
        if path == "/public/page":
            self._send(
                _page_html().encode("utf-8"),
                content_type="text/html; charset=utf-8",
            )
            return
        if path == "/public/report.txt":
            self._send(_REPORT, content_type="text/plain; charset=utf-8")
            return
        self._send(b"not found", status=404, content_type="text/plain; charset=utf-8")

    def log_message(self, format: str, *args: object) -> None:
        del format, args

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


def _page_html() -> str:
    return """<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>SA16 L14 fixture</title>
<link rel="icon" href="data:,">
</head>
<body>
<main id="evidence">
<h1>Controlled public evidence</h1>
<p>Neutral first-party fixture.</p>
</main>
<a id="report" href="/public/report.txt">Public report</a>
</body>
</html>"""


@contextmanager
def _serve_fixture() -> Iterator[str]:
    server = ThreadingHTTPServer(("127.0.0.1", 0), _FixtureHandler)
    port = int(server.server_address[1])
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://{_FIXTURE_HOST}:{port}"
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()


def _target(origin: str, organization_id: UUID, now: datetime) -> PublicWebTarget:
    return PublicWebTarget(
        id="sa16-l14-live-browser",
        organization_id=organization_id,
        canonical_name="SA16 L14 controlled artifact fixture",
        base_url=f"{origin}/",
        seed_urls=(f"{origin}/public/page",),
        sitemap_urls=(),
        feed_urls=(),
        discover_security_txt=False,
        discover_sitemaps=False,
        discover_feeds=False,
        allowed_path_prefixes=("/public",),
        enabled=True,
        authorization_reference="sa16-l14-controlled-live-approval",
        authorization_reviewed_at=now,
        max_link_depth=0,
        max_pages=10,
        max_total_bytes=2_000_000,
        max_resource_bytes=1_000_000,
        max_redirects=2,
    )


def _entry(target: PublicWebTarget, now: datetime) -> SourceRegistryEntry:
    return SourceRegistryEntry(
        policy=SourcePolicy(
            id=target.id,
            name="SA16 L14 controlled artifact fixture",
            base_url=target.base_url,
            status=SourceStatus.ENABLED,
            source_type=SourceType.BROWSER,
            owner="CIP controlled live validation",
            licence="Repository-owned ephemeral first-party validation fixture",
            allowed_data_categories=frozenset(
                {DataCategory.OFFICIAL_DOCUMENT_DISCOVERY}
            ),
            retention_days=1,
            raw_content_storage=False,
            human_review_required=False,
        ),
        authorization=SourceAuthorization(
            status=AuthorizationStatus.APPROVED,
            document_reference="sa16-l14-controlled-live-approval",
            reviewed_at=now,
            approved_hosts=frozenset({target.host}),
            approved_path_prefixes=("/public",),
            approved_purposes=frozenset({"corporate-public-footprint"}),
            approved_http_methods=frozenset({HttpMethod.GET}),
            automated_collection_allowed=True,
            raw_storage_allowed=False,
        ),
        economics={"monthly_cost": 0},
    )


def _plan(target: PublicWebTarget, origin: str) -> BrowserActionPlan:
    steps = (
        BrowserActionStep(
            step_id="navigate",
            kind=BrowserActionKind.NAVIGATE,
            target_url=f"{origin}/public/page",
        ),
        BrowserActionStep(
            step_id="screenshot",
            kind=BrowserActionKind.SCREENSHOT,
            selector="main#evidence",
            screenshot_mode=BrowserScreenshotMode.ELEMENT,
        ),
        BrowserActionStep(
            step_id="download",
            kind=BrowserActionKind.DOWNLOAD,
            selector="a#report",
            expected_download_url=f"{origin}/public/report.txt",
        ),
    )
    return BrowserActionPlan(
        plan_id=uuid4(),
        version=1,
        source_id=target.id,
        provider_id="controlled-live-fixture",
        target_id=target.id,
        purpose="corporate-public-footprint",
        steps=steps,
        allowed_transitions=(
            BrowserTransitionRule(
                host=target.host,
                path_prefix="/public",
                methods=frozenset({BrowserHttpMethod.GET}),
            ),
        ),
        max_actions=len(steps),
        max_total_value_chars=0,
    )


def _persist_organization(factory, organization_id: UUID, now: datetime) -> None:
    with session_scope(factory) as session:
        session.add(
            OrganizationRecord(
                id=organization_id,
                canonical_name="SA16 L14 fixture organization",
                legal_name=None,
                country_code=None,
                website_url=None,
                registration_ids=[],
                created_at=now,
                updated_at=now,
            )
        )


def _verify_persisted_result(factory, plan: BrowserActionPlan) -> None:
    with session_scope(factory) as session:
        artifacts = load_browser_artifacts_for_plan(
            session,
            plan.plan_id,
            plan.version,
        )
        resources = session.scalars(select(PublicResourceRecord)).all()
    if len(artifacts) != 2:
        raise RuntimeError("SA16-L14 did not persist both artifact metadata records")
    screenshot = next(
        item for item in artifacts if item.kind is BrowserArtifactKind.SCREENSHOT
    )
    download = next(
        item for item in artifacts if item.kind is BrowserArtifactKind.DOWNLOAD
    )
    if not screenshot.viewport_width or not screenshot.viewport_height:
        raise RuntimeError("SA16-L14 screenshot dimensions were not recorded")
    if screenshot.raw_retained or screenshot.storage_uri is not None:
        raise RuntimeError("SA16-L14 retained raw screenshot bytes against source policy")
    if download.raw_retained or download.storage_uri is not None:
        raise RuntimeError("SA16-L14 retained raw download bytes against source policy")
    if download.excerpt is None or "controlled public document" not in download.excerpt:
        raise RuntimeError("SA16-L14 download parser did not produce permitted evidence")
    if len(resources) != 1 or resources[0].kind != PublicResourceKind.DOCUMENT.value:
        raise RuntimeError("SA16-L14 document projection was not persisted")


def main() -> None:
    now = datetime.now(UTC)
    organization_id = uuid4()
    quarantine_before = set(Path(gettempdir()).glob("cip-artifact-*"))
    with _serve_fixture() as origin:
        target = _target(origin, organization_id, now)
        entry = _entry(target, now)
        plan = _plan(target, origin)
        engine = create_database_engine("sqlite+pysqlite:///:memory:")
        get_metadata().create_all(engine)
        factory = create_session_factory(engine)
        _persist_organization(factory, organization_id, now)
        with session_scope(factory) as session:
            checkpoint = persist_browser_action_plan(session, plan, now=now)
        with httpx.Client(follow_redirects=False, trust_env=False) as download_client:
            artifact_context = BrowserArtifactExecutionContext(
                job_id=uuid4(),
                captured_at=now,
                retention_until=now + timedelta(days=1),
                download_client=download_client,
            )
            with session_scope(factory) as session:
                result = execute_public_browser_action_plan(
                    target,
                    entry,
                    plan,
                    checkpoint,
                    collected_at=now,
                    checkpoint_writer=lambda value: save_browser_action_checkpoint(
                        session,
                        value,
                        now=now,
                    ),
                    artifact_context=artifact_context,
                )
                for artifact in result.artifacts:
                    persist_browser_artifact(session, artifact, now=now)
                persist_public_footprint_projections(
                    session,
                    result.public_footprint_projections,
                    now=now,
                )
        if any(
            state is not BrowserStepState.COMPLETED
            for state in result.checkpoint.step_states
        ):
            raise RuntimeError("SA16-L14 browser artifact plan did not complete")
        if len(result.artifacts) != 2 or len(result.public_footprint_projections) != 1:
            raise RuntimeError("SA16-L14 artifact execution returned an invalid result shape")
        _verify_persisted_result(factory, plan)
    quarantine_after = set(Path(gettempdir()).glob("cip-artifact-*"))
    if quarantine_after != quarantine_before:
        raise RuntimeError("SA16-L14 left quarantine artifacts behind")
    print(
        "SA-16 L14 live validation passed: "
        "real_chromium=1 screenshots=1 downloads=1 document_projections=1 "
        "quarantine_leaks=0 raw_retained=0 arbitrary_js=0 auth=0 native_downloads=0",
        flush=True,
    )


if __name__ == "__main__":
    main()
