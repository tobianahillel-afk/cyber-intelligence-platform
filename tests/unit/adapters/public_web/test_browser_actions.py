from __future__ import annotations

from datetime import UTC, datetime
from typing import Callable
from uuid import uuid4

import pytest

from cip.adapters.sources.public_web import browser_action_executor
from cip.adapters.sources.public_web.browser_action_executor import (
    BrowserActionExecutionError,
    BrowserActionNeedsVerificationError,
    BrowserActionPolicyDeniedError,
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
    recover_interrupted_checkpoint,
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

NOW = datetime(2026, 8, 16, 15, 0, tzinfo=UTC)


class _FakePlaywrightError(Exception):
    pass


class _FakeRequest:
    def __init__(self, url: str, method: str = "GET") -> None:
        self.url = url
        self.method = method
        self.resource_type = "document"

    def is_navigation_request(self) -> bool:
        return True


class _FakeRoute:
    def __init__(self, request: _FakeRequest) -> None:
        self.request = request
        self.aborted = False
        self.continued = False

    def abort(self) -> None:
        self.aborted = True

    def continue_(self) -> None:
        self.continued = True


class _FakeLocatorSet:
    def __init__(self, locators: list[_FakeLocator]) -> None:
        self._locators = locators

    def count(self) -> int:
        return len(self._locators)

    def all(self) -> list[_FakeLocator]:
        return list(self._locators)

    @property
    def first(self) -> _FakeLocator:
        if not self._locators:
            raise _FakePlaywrightError("no locator")
        return self._locators[0]

    def get_attribute(self, name: str) -> str | None:
        return self.first.get_attribute(name)

    def locator(self, query: str) -> _FakeLocatorSet:
        return self.first.locator(query)

    def click(self, *, timeout: int) -> None:
        self.first.click(timeout=timeout)

    def fill(self, value: str, *, timeout: int) -> None:
        self.first.fill(value, timeout=timeout)

    def select_option(self, value: str, *, timeout: int) -> None:
        self.first.select_option(value, timeout=timeout)

    def check(self, *, timeout: int) -> None:
        self.first.check(timeout=timeout)

    def uncheck(self, *, timeout: int) -> None:
        self.first.uncheck(timeout=timeout)

    def wait_for(self, *, state: str, timeout: int) -> None:
        self.first.wait_for(state=state, timeout=timeout)


class _FakeLocator:
    def __init__(
        self,
        *,
        kind: str,
        attributes: dict[str, str] | None = None,
        fields: list[_FakeLocator] | None = None,
        on_click: Callable[[], None] | None = None,
        fail: bool = False,
    ) -> None:
        self.kind = kind
        self.attributes = attributes or {}
        self.fields = fields or []
        self.submit_controls: list[_FakeLocator] = []
        self.on_click = on_click
        self.fail = fail
        self.value: str | None = None
        self.checked = False
        self.waited = False

    def count(self) -> int:
        return 1

    def get_attribute(self, name: str) -> str | None:
        return self.attributes.get(name)

    def locator(self, query: str) -> _FakeLocatorSet:
        if query == "xpath=self::button":
            return _FakeLocatorSet([self] if self.kind == "button" else [])
        if query == "xpath=self::form":
            return _FakeLocatorSet([self] if self.kind == "form" else [])
        if query == "input, textarea, select":
            return _FakeLocatorSet(self.fields)
        if "button[type=" in query or "input[type=" in query:
            return _FakeLocatorSet(self.submit_controls)
        return _FakeLocatorSet([])

    def click(self, *, timeout: int) -> None:
        del timeout
        if self.fail:
            raise _FakePlaywrightError("click timeout")
        if self.on_click is not None:
            self.on_click()

    def fill(self, value: str, *, timeout: int) -> None:
        del timeout
        self.value = value

    def select_option(self, value: str, *, timeout: int) -> None:
        del timeout
        self.value = value

    def check(self, *, timeout: int) -> None:
        del timeout
        self.checked = True

    def uncheck(self, *, timeout: int) -> None:
        del timeout
        self.checked = False

    def wait_for(self, *, state: str, timeout: int) -> None:
        del state, timeout
        self.waited = True


class _FakePage:
    def __init__(self) -> None:
        self.url = "about:blank"
        self.route_handler: Callable[[_FakeRoute], None] | None = None
        self.locators: dict[str, _FakeLocatorSet] = {}
        self.html = "<html><body>fixture</body></html>"
        self.load_waited = False

    def route(self, _pattern: str, handler: Callable[[_FakeRoute], None]) -> None:
        self.route_handler = handler

    def goto(self, url: str, **_kwargs: object) -> None:
        self._navigate(url, "GET")

    def _navigate(self, url: str, method: str) -> None:
        assert self.route_handler is not None
        route = _FakeRoute(_FakeRequest(url, method))
        self.route_handler(route)
        if route.aborted:
            raise _FakePlaywrightError("navigation blocked")
        self.url = url

    def locator(self, selector: str) -> _FakeLocatorSet:
        return self.locators.get(selector, _FakeLocatorSet([]))

    def wait_for_load_state(self, _state: str, *, timeout: int) -> None:
        del timeout
        self.load_waited = True

    def content(self) -> str:
        return self.html


class _FakeContext:
    def __init__(self, page: _FakePage) -> None:
        self.page = page
        self.kwargs: dict[str, object] = {}
        self.closed = False

    def new_page(self) -> _FakePage:
        return self.page

    def close(self) -> None:
        self.closed = True


class _FakeBrowser:
    def __init__(self, page: _FakePage) -> None:
        self.context = _FakeContext(page)
        self.closed = False

    def new_context(self, **kwargs: object) -> _FakeContext:
        self.context.kwargs = kwargs
        return self.context

    def close(self) -> None:
        self.closed = True


class _FakeChromium:
    def __init__(self, page: _FakePage) -> None:
        self.browser = _FakeBrowser(page)
        self.launch_kwargs: dict[str, object] = {}

    def launch(self, **kwargs: object) -> _FakeBrowser:
        self.launch_kwargs = kwargs
        return self.browser


class _FakeManager:
    def __init__(self, page: _FakePage) -> None:
        self.chromium = _FakeChromium(page)

    def __enter__(self) -> _FakeManager:
        return self

    def __exit__(self, *_args: object) -> None:
        return None


def _install(monkeypatch: pytest.MonkeyPatch, page: _FakePage) -> _FakeManager:
    manager = _FakeManager(page)
    monkeypatch.setattr(browser_action_executor, "sync_playwright", lambda: manager)
    monkeypatch.setattr(browser_action_executor, "PlaywrightError", _FakePlaywrightError)
    return manager


def _target() -> PublicWebTarget:
    return PublicWebTarget(
        id="browser-actions",
        organization_id=uuid4(),
        canonical_name="Browser Actions",
        base_url="https://example.com/",
        seed_urls=("https://example.com/public/form",),
        sitemap_urls=(),
        feed_urls=(),
        discover_security_txt=False,
        discover_sitemaps=False,
        discover_feeds=False,
        allowed_path_prefixes=("/public",),
        enabled=True,
        authorization_reference="L13-test-approval",
        authorization_reviewed_at=NOW,
        max_pages=10,
        max_total_bytes=100_000,
        max_resource_bytes=50_000,
        max_redirects=2,
    )


def _entry(target: PublicWebTarget) -> SourceRegistryEntry:
    return SourceRegistryEntry(
        policy=SourcePolicy(
            id=target.id,
            name="Browser Actions",
            base_url=target.base_url,
            status=SourceStatus.ENABLED,
            source_type=SourceType.BROWSER,
            owner="tests",
            licence="controlled L13 fixture",
            allowed_data_categories=frozenset({DataCategory.OFFICIAL_DOCUMENT_DISCOVERY}),
            human_review_required=False,
        ),
        authorization=SourceAuthorization(
            status=AuthorizationStatus.APPROVED,
            document_reference="L13-test-approval",
            reviewed_at=NOW,
            approved_hosts=frozenset({target.host}),
            approved_path_prefixes=("/public",),
            approved_purposes=frozenset({"corporate-public-footprint"}),
            approved_http_methods=frozenset({HttpMethod.GET, HttpMethod.POST}),
            automated_collection_allowed=True,
        ),
        economics={"monthly_cost": 0},
    )


def _plan(target: PublicWebTarget, steps: tuple[BrowserActionStep, ...]) -> BrowserActionPlan:
    return BrowserActionPlan(
        plan_id=uuid4(),
        version=1,
        source_id=target.id,
        provider_id="fixture-provider",
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


def _checkpoint(plan: BrowserActionPlan) -> BrowserActionCheckpoint:
    return BrowserActionCheckpoint(
        plan_id=plan.plan_id,
        plan_version=plan.version,
        step_states=tuple(BrowserStepState.PENDING for _ in plan.steps),
    )


def _navigate_step() -> BrowserActionStep:
    return BrowserActionStep(
        step_id="navigate",
        kind=BrowserActionKind.NAVIGATE,
        target_url="https://example.com/public/form",
    )


def test_typed_actions_execute_with_isolated_browser(monkeypatch: pytest.MonkeyPatch) -> None:
    page = _FakePage()
    page.locators["button#toggle"] = _FakeLocatorSet(
        [_FakeLocator(kind="button", attributes={"type": "button"})]
    )
    text = _FakeLocator(kind="input", attributes={"type": "text"})
    select = _FakeLocator(kind="select")
    checkbox = _FakeLocator(kind="input", attributes={"type": "checkbox"})
    result = _FakeLocator(kind="div")
    page.locators['input[name="query"]'] = _FakeLocatorSet([text])
    page.locators["select#kind"] = _FakeLocatorSet([select])
    page.locators["input#enabled"] = _FakeLocatorSet([checkbox])
    page.locators["main#result"] = _FakeLocatorSet([result])
    manager = _install(monkeypatch, page)
    target = _target()
    steps = (
        _navigate_step(),
        BrowserActionStep("toggle", BrowserActionKind.CLICK, selector="button#toggle"),
        BrowserActionStep(
            "fill",
            BrowserActionKind.FILL,
            selector='input[name="query"]',
            value="public value",
            value_classification=BrowserValueClassification.PUBLIC_NON_SECRET,
        ),
        BrowserActionStep(
            "select",
            BrowserActionKind.SELECT,
            selector="select#kind",
            value="company",
            value_classification=BrowserValueClassification.PUBLIC_NON_SECRET,
        ),
        BrowserActionStep("check", BrowserActionKind.CHECK, selector="input#enabled"),
        BrowserActionStep("uncheck", BrowserActionKind.UNCHECK, selector="input#enabled"),
        BrowserActionStep(
            "wait",
            BrowserActionKind.WAIT_FOR_DOM_CONDITION,
            selector="main#result",
        ),
    )
    plan = _plan(target, steps)
    writes: list[BrowserActionCheckpoint] = []

    executed = execute_public_browser_action_plan(
        target,
        _entry(target),
        plan,
        _checkpoint(plan),
        collected_at=NOW,
        checkpoint_writer=writes.append,
    )

    assert text.value == "public value"
    assert select.value == "company"
    assert checkbox.checked is False
    assert result.waited is True
    assert all(state is BrowserStepState.COMPLETED for state in executed.checkpoint.step_states)
    assert manager.chromium.launch_kwargs == {"headless": True, "chromium_sandbox": True}
    assert manager.chromium.browser.context.kwargs["accept_downloads"] is False


@pytest.mark.parametrize("method", [BrowserHttpMethod.GET, BrowserHttpMethod.POST])
def test_governed_form_submission_uses_inspected_metadata(
    monkeypatch: pytest.MonkeyPatch,
    method: BrowserHttpMethod,
) -> None:
    page = _FakePage()
    target = _target()
    action = "https://example.com/public/search"
    form = _FakeLocator(kind="form", attributes={"action": action, "method": method.value})
    submit = _FakeLocator(kind="button", attributes={"type": "submit"})
    submit.on_click = lambda: page._navigate(action, method.value)
    form.submit_controls.append(submit)
    form.fields.append(_FakeLocator(kind="input", attributes={"type": "text", "name": "query"}))
    page.locators["form#search"] = _FakeLocatorSet([form])
    _install(monkeypatch, page)
    replay = (
        BrowserStepReplayPolicy.VERIFY_BEFORE_REPLAY
        if method is BrowserHttpMethod.POST
        else BrowserStepReplayPolicy.SAFE
    )
    plan = _plan(
        target,
        (
            _navigate_step(),
            BrowserActionStep(
                "submit",
                BrowserActionKind.SUBMIT_FORM,
                selector="form#search",
                expected_form_action_url=action,
                expected_form_method=method,
                replay_policy=replay,
            ),
        ),
    )

    executed = execute_public_browser_action_plan(
        target,
        _entry(target),
        plan,
        _checkpoint(plan),
        collected_at=NOW,
        checkpoint_writer=lambda _checkpoint: None,
    )

    assert executed.final_url == action
    assert executed.requests_seen == 2


def test_off_origin_form_is_denied_before_submission(monkeypatch: pytest.MonkeyPatch) -> None:
    page = _FakePage()
    form = _FakeLocator(
        kind="form",
        attributes={"action": "https://other.example/public/search", "method": "POST"},
    )
    form.submit_controls.append(_FakeLocator(kind="button", attributes={"type": "submit"}))
    page.locators["form#search"] = _FakeLocatorSet([form])
    _install(monkeypatch, page)
    target = _target()
    plan = _plan(
        target,
        (
            _navigate_step(),
            BrowserActionStep(
                "submit",
                BrowserActionKind.SUBMIT_FORM,
                selector="form#search",
                expected_form_action_url="https://other.example/public/search",
                expected_form_method=BrowserHttpMethod.POST,
                replay_policy=BrowserStepReplayPolicy.VERIFY_BEFORE_REPLAY,
            ),
        ),
    )

    with pytest.raises(BrowserActionExecutionError):
        execute_public_browser_action_plan(
            target,
            _entry(target),
            plan,
            _checkpoint(plan),
            collected_at=NOW,
            checkpoint_writer=lambda _checkpoint: None,
        )


@pytest.mark.parametrize(
    ("field_type", "message"),
    [("password", "password_field_denied"), ("file", "file_input_denied")],
)
def test_sensitive_form_fields_are_denied(
    monkeypatch: pytest.MonkeyPatch,
    field_type: str,
    message: str,
) -> None:
    page = _FakePage()
    action = "https://example.com/public/search"
    form = _FakeLocator(kind="form", attributes={"action": action, "method": "POST"})
    form.fields.append(_FakeLocator(kind="input", attributes={"type": field_type}))
    form.submit_controls.append(_FakeLocator(kind="button", attributes={"type": "submit"}))
    page.locators["form#search"] = _FakeLocatorSet([form])
    _install(monkeypatch, page)
    target = _target()
    plan = _plan(
        target,
        (
            _navigate_step(),
            BrowserActionStep(
                "submit",
                BrowserActionKind.SUBMIT_FORM,
                selector="form#search",
                expected_form_action_url=action,
                expected_form_method=BrowserHttpMethod.POST,
                replay_policy=BrowserStepReplayPolicy.VERIFY_BEFORE_REPLAY,
            ),
        ),
    )

    with pytest.raises(BrowserActionPolicyDeniedError, match=message):
        execute_public_browser_action_plan(
            target,
            _entry(target),
            plan,
            _checkpoint(plan),
            collected_at=NOW,
            checkpoint_writer=lambda _checkpoint: None,
        )


def test_submission_guard_blocks_last_moment_target_change(monkeypatch: pytest.MonkeyPatch) -> None:
    page = _FakePage()
    expected = "https://example.com/public/search"
    form = _FakeLocator(kind="form", attributes={"action": expected, "method": "POST"})
    submit = _FakeLocator(kind="button", attributes={"type": "submit"})
    submit.on_click = lambda: page._navigate("https://example.com/public/other", "POST")
    form.submit_controls.append(submit)
    page.locators["form#search"] = _FakeLocatorSet([form])
    _install(monkeypatch, page)
    target = _target()
    plan = _plan(
        target,
        (
            _navigate_step(),
            BrowserActionStep(
                "submit",
                BrowserActionKind.SUBMIT_FORM,
                selector="form#search",
                expected_form_action_url=expected,
                expected_form_method=BrowserHttpMethod.POST,
                replay_policy=BrowserStepReplayPolicy.VERIFY_BEFORE_REPLAY,
            ),
        ),
    )

    with pytest.raises(BrowserActionPolicyDeniedError, match="submission_guard_denied"):
        execute_public_browser_action_plan(
            target,
            _entry(target),
            plan,
            _checkpoint(plan),
            collected_at=NOW,
            checkpoint_writer=lambda _checkpoint: None,
        )


def test_playwright_timeout_is_wrapped(monkeypatch: pytest.MonkeyPatch) -> None:
    page = _FakePage()
    page.locators["button#slow"] = _FakeLocatorSet(
        [_FakeLocator(kind="button", attributes={"type": "button"}, fail=True)]
    )
    _install(monkeypatch, page)
    target = _target()
    plan = _plan(
        target,
        (
            _navigate_step(),
            BrowserActionStep("slow", BrowserActionKind.CLICK, selector="button#slow", timeout_ms=100),
        ),
    )

    with pytest.raises(BrowserActionExecutionError, match="execution_failed"):
        execute_public_browser_action_plan(
            target,
            _entry(target),
            plan,
            _checkpoint(plan),
            collected_at=NOW,
            checkpoint_writer=lambda _checkpoint: None,
        )


def test_crash_after_post_side_effect_never_blindly_replays(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    page = _FakePage()
    action = "https://example.com/public/search"
    form = _FakeLocator(kind="form", attributes={"action": action, "method": "POST"})
    submit = _FakeLocator(kind="button", attributes={"type": "submit"})
    submit.on_click = lambda: page._navigate(action, "POST")
    form.submit_controls.append(submit)
    page.locators["form#search"] = _FakeLocatorSet([form])
    _install(monkeypatch, page)
    target = _target()
    plan = _plan(
        target,
        (
            _navigate_step(),
            BrowserActionStep(
                "submit",
                BrowserActionKind.SUBMIT_FORM,
                selector="form#search",
                expected_form_action_url=action,
                expected_form_method=BrowserHttpMethod.POST,
                replay_policy=BrowserStepReplayPolicy.VERIFY_BEFORE_REPLAY,
            ),
        ),
    )
    persisted = _checkpoint(plan)

    class CrashAfterPost(RuntimeError):
        pass

    def writer(checkpoint: BrowserActionCheckpoint) -> None:
        nonlocal persisted
        if checkpoint.step_states[-1] is BrowserStepState.COMPLETED:
            raise CrashAfterPost
        persisted = checkpoint

    with pytest.raises(CrashAfterPost):
        execute_public_browser_action_plan(
            target,
            _entry(target),
            plan,
            persisted,
            collected_at=NOW,
            checkpoint_writer=writer,
        )

    recovered = recover_interrupted_checkpoint(plan, persisted)
    assert recovered.step_states[-1] is BrowserStepState.NEEDS_VERIFICATION

    called = False

    def no_browser() -> _FakeManager:
        nonlocal called
        called = True
        return _FakeManager(page)

    monkeypatch.setattr(browser_action_executor, "sync_playwright", no_browser)
    with pytest.raises(BrowserActionNeedsVerificationError):
        execute_public_browser_action_plan(
            target,
            _entry(target),
            plan,
            recovered,
            collected_at=NOW,
            checkpoint_writer=lambda _checkpoint: None,
        )
    assert called is False


def test_crash_before_step_leaves_pending_step_replayable() -> None:
    target = _target()
    plan = _plan(target, (_navigate_step(),))
    checkpoint = _checkpoint(plan)

    assert recover_interrupted_checkpoint(plan, checkpoint) == checkpoint
