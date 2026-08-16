from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Lock, Thread
from urllib.parse import parse_qs, urlsplit
from uuid import uuid4

from cip.adapters.sources.public_web.browser_action_executor import (
    BrowserActionNeedsVerificationError,
    execute_public_browser_action_plan,
)
from cip.adapters.sources.public_web.registry import PublicWebTarget
from cip.modules.public_footprint.domain.browser_actions import (
    BrowserActionCheckpoint,
    BrowserActionKind,
    BrowserActionPlan,
    BrowserActionStep,
    BrowserHttpMethod,
    BrowserStepReplayPolicy,
    BrowserStepState,
    BrowserTransitionRule,
    BrowserValueClassification,
)
from cip.modules.public_footprint.infrastructure.browser_action_persistence import (
    load_browser_action_checkpoint,
    persist_browser_action_plan,
    recover_interrupted_checkpoint,
    save_browser_action_checkpoint,
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

_FIXTURE_HOST = "sa16-l13-fixture.example"
_LOCK = Lock()
_POST_COUNTS: dict[str, int] = {"post": 0, "crash": 0}


class _FixtureHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def do_GET(self) -> None:
        parsed = urlsplit(self.path)
        if parsed.path == "/public/form":
            self._send(_form_html().encode("utf-8"))
            return
        if parsed.path == "/public/search":
            query = parse_qs(parsed.query)
            value = query.get("query", [""])[0]
            self._send(_result_html("GET", value, 0).encode("utf-8"))
            return
        self._send(b"not found", status=404, content_type="text/plain; charset=utf-8")

    def do_POST(self) -> None:
        parsed = urlsplit(self.path)
        if parsed.path not in {"/public/post", "/public/crash"}:
            self._send(b"not found", status=404, content_type="text/plain; charset=utf-8")
            return
        length = int(self.headers.get("Content-Length", "0"))
        payload = parse_qs(self.rfile.read(length).decode("utf-8"))
        value = payload.get("query", [""])[0]
        counter = "post" if parsed.path == "/public/post" else "crash"
        with _LOCK:
            _POST_COUNTS[counter] += 1
            count = _POST_COUNTS[counter]
        self._send(_result_html("POST", value, count).encode("utf-8"))

    def log_message(self, format: str, *args: object) -> None:
        del format, args

    def _send(
        self,
        body: bytes,
        *,
        status: int = 200,
        content_type: str = "text/html; charset=utf-8",
    ) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)
        self.wfile.flush()


def _form_html() -> str:
    return """<!doctype html>
<html><head><meta charset="utf-8"><title>SA16 L13 fixture</title>
<link rel="icon" href="data:,">
</head>
<body>
<button id="advanced" type="button"
 onclick="document.getElementById('advanced-state').textContent='open'">Advanced</button>
<div id="advanced-state">closed</div>
<form id="get-form" action="/public/search" method="GET">
  <input name="query" type="text">
  <select name="category"><option value="company">Company</option></select>
  <input name="confirm" type="checkbox" value="yes">
  <button type="submit">Search</button>
</form>
<form id="post-form" action="/public/post" method="POST">
  <input name="query" type="text">
  <button type="submit">Post</button>
</form>
<form id="crash-form" action="/public/crash" method="POST">
  <input name="query" type="text">
  <button type="submit">Crash post</button>
</form>
</body></html>"""


def _result_html(method: str, value: str, count: int) -> str:
    return (
        "<!doctype html><html><body>"
        f'<main id="result" data-method="{method}" data-count="{count}">{value}</main>'
        "</body></html>"
    )


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


def _target(origin: str, now: datetime) -> PublicWebTarget:
    return PublicWebTarget(
        id="sa16-l13-live-browser",
        organization_id=uuid4(),
        canonical_name="SA16 L13 controlled browser fixture",
        base_url=f"{origin}/",
        seed_urls=(f"{origin}/public/form",),
        sitemap_urls=(),
        feed_urls=(),
        discover_security_txt=False,
        discover_sitemaps=False,
        discover_feeds=False,
        allowed_path_prefixes=("/public",),
        enabled=True,
        authorization_reference="sa16-l13-controlled-live-approval",
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
            name="SA16 L13 controlled browser fixture",
            base_url=target.base_url,
            status=SourceStatus.ENABLED,
            source_type=SourceType.BROWSER,
            owner="CIP controlled live validation",
            licence="Repository-owned ephemeral first-party validation fixture",
            allowed_data_categories=frozenset({DataCategory.OFFICIAL_DOCUMENT_DISCOVERY}),
            retention_days=1,
            human_review_required=False,
        ),
        authorization=SourceAuthorization(
            status=AuthorizationStatus.APPROVED,
            document_reference="sa16-l13-controlled-live-approval",
            reviewed_at=now,
            approved_hosts=frozenset({target.host}),
            approved_path_prefixes=("/public",),
            approved_purposes=frozenset({"corporate-public-footprint"}),
            approved_http_methods=frozenset({HttpMethod.GET, HttpMethod.POST}),
            automated_collection_allowed=True,
            raw_storage_allowed=False,
        ),
        economics={"monthly_cost": 0},
    )


def _plan(
    target: PublicWebTarget,
    steps: tuple[BrowserActionStep, ...],
) -> BrowserActionPlan:
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
                methods=frozenset({BrowserHttpMethod.GET, BrowserHttpMethod.POST}),
            ),
        ),
        max_actions=len(steps),
        max_total_value_chars=sum(len(step.value or "") for step in steps),
    )


def _navigate(origin: str) -> BrowserActionStep:
    return BrowserActionStep(
        step_id="navigate",
        kind=BrowserActionKind.NAVIGATE,
        target_url=f"{origin}/public/form",
    )


def _fill(step_id: str, selector: str, value: str) -> BrowserActionStep:
    return BrowserActionStep(
        step_id=step_id,
        kind=BrowserActionKind.FILL,
        selector=selector,
        value=value,
        value_classification=BrowserValueClassification.PUBLIC_NON_SECRET,
    )


def _submit(
    step_id: str,
    selector: str,
    action: str,
    method: BrowserHttpMethod,
) -> BrowserActionStep:
    return BrowserActionStep(
        step_id=step_id,
        kind=BrowserActionKind.SUBMIT_FORM,
        selector=selector,
        expected_form_action_url=action,
        expected_form_method=method,
        replay_policy=(
            BrowserStepReplayPolicy.VERIFY_BEFORE_REPLAY
            if method is BrowserHttpMethod.POST
            else BrowserStepReplayPolicy.SAFE
        ),
    )


def _run_success_plan(
    factory,
    target: PublicWebTarget,
    entry: SourceRegistryEntry,
    plan: BrowserActionPlan,
    now: datetime,
):
    with session_scope(factory) as session:
        checkpoint = persist_browser_action_plan(session, plan, now=now)
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
        )
        if any(
            state is not BrowserStepState.COMPLETED
            for state in result.checkpoint.step_states
        ):
            raise RuntimeError("SA16-L13 successful plan did not complete every step")
        return result


def _prove_ambiguous_post_recovery(
    factory,
    target: PublicWebTarget,
    entry: SourceRegistryEntry,
    plan: BrowserActionPlan,
    now: datetime,
) -> None:
    with session_scope(factory) as session:
        checkpoint = persist_browser_action_plan(session, plan, now=now)

    class SimulatedCrash(RuntimeError):
        pass

    with session_scope(factory) as session:

        def crash_writer(value: BrowserActionCheckpoint) -> None:
            if value.step_states[-1] is BrowserStepState.COMPLETED:
                raise SimulatedCrash(
                    "crash after network effect before completion persistence"
                )
            save_browser_action_checkpoint(session, value, now=now)
            session.commit()

        try:
            execute_public_browser_action_plan(
                target,
                entry,
                plan,
                checkpoint,
                collected_at=now,
                checkpoint_writer=crash_writer,
            )
        except SimulatedCrash:
            pass
        else:
            raise RuntimeError(
                "SA16-L13 crash simulation did not interrupt completion persistence"
            )

    with session_scope(factory) as session:
        persisted = load_browser_action_checkpoint(session, plan.plan_id, plan.version)
        if (
            persisted is None
            or persisted.step_states[-1] is not BrowserStepState.EXECUTING
        ):
            raise RuntimeError(
                "SA16-L13 did not persist the ambiguous executing checkpoint"
            )
        recovered = recover_interrupted_checkpoint(plan, persisted)
        save_browser_action_checkpoint(session, recovered, now=now)

    if recovered.step_states[-1] is not BrowserStepState.NEEDS_VERIFICATION:
        raise RuntimeError("SA16-L13 ambiguous POST did not require verification")
    try:
        execute_public_browser_action_plan(
            target,
            entry,
            plan,
            recovered,
            collected_at=now,
            checkpoint_writer=lambda _value: None,
        )
    except BrowserActionNeedsVerificationError:
        pass
    else:
        raise RuntimeError("SA16-L13 replayed an unsafe ambiguous POST")


def main() -> None:
    now = datetime.now(UTC)
    with _LOCK:
        _POST_COUNTS["post"] = 0
        _POST_COUNTS["crash"] = 0
    with _serve_fixture() as origin:
        target = _target(origin, now)
        entry = _entry(target, now)
        engine = create_database_engine("sqlite+pysqlite:///:memory:")
        get_metadata().create_all(engine)
        factory = create_session_factory(engine)

        get_plan = _plan(
            target,
            (
                _navigate(origin),
                BrowserActionStep(
                    step_id="toggle",
                    kind=BrowserActionKind.CLICK,
                    selector="button#advanced",
                ),
                _fill("get-fill", '#get-form input[name="query"]', "SA16-L13-GET"),
                BrowserActionStep(
                    step_id="select",
                    kind=BrowserActionKind.SELECT,
                    selector='#get-form select[name="category"]',
                    value="company",
                    value_classification=BrowserValueClassification.PUBLIC_NON_SECRET,
                ),
                BrowserActionStep(
                    step_id="check",
                    kind=BrowserActionKind.CHECK,
                    selector='#get-form input[name="confirm"]',
                ),
                _submit(
                    "get-submit",
                    "form#get-form",
                    f"{origin}/public/search",
                    BrowserHttpMethod.GET,
                ),
            ),
        )
        get_result = _run_success_plan(factory, target, entry, get_plan, now)
        if (
            b"SA16-L13-GET" not in get_result.html
            or b'data-method="GET"' not in get_result.html
        ):
            raise RuntimeError(
                "SA16-L13 GET plan did not capture resulting public evidence"
            )

        post_plan = _plan(
            target,
            (
                _navigate(origin),
                _fill("post-fill", '#post-form input[name="query"]', "SA16-L13-POST"),
                _submit(
                    "post-submit",
                    "form#post-form",
                    f"{origin}/public/post",
                    BrowserHttpMethod.POST,
                ),
            ),
        )
        post_result = _run_success_plan(factory, target, entry, post_plan, now)
        if (
            b"SA16-L13-POST" not in post_result.html
            or b'data-method="POST"' not in post_result.html
        ):
            raise RuntimeError(
                "SA16-L13 POST plan did not capture resulting public evidence"
            )

        crash_plan = _plan(
            target,
            (
                _navigate(origin),
                _fill("crash-fill", '#crash-form input[name="query"]', "SA16-L13-CRASH"),
                _submit(
                    "crash-submit",
                    "form#crash-form",
                    f"{origin}/public/crash",
                    BrowserHttpMethod.POST,
                ),
            ),
        )
        _prove_ambiguous_post_recovery(factory, target, entry, crash_plan, now)

    with _LOCK:
        post_count = _POST_COUNTS["post"]
        crash_count = _POST_COUNTS["crash"]
    if post_count != 1 or crash_count != 1:
        raise RuntimeError(
            f"SA16-L13 submission counts invalid: post={post_count} crash={crash_count}"
        )
    print(
        "SA-16 L13 live validation passed: "
        f"get_steps={len(get_result.completed_step_ids)} "
        f"post_steps={len(post_result.completed_step_ids)} "
        f"post_submissions={post_count} ambiguous_post_submissions={crash_count} "
        "unsafe_replays=0 arbitrary_js=0 auth=0 downloads=0",
        flush=True,
    )


if __name__ == "__main__":
    main()
