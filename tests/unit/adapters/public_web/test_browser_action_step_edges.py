from __future__ import annotations

from types import SimpleNamespace
from typing import Any, cast

import pytest

from cip.adapters.sources.public_web import browser_action_steps as steps
from cip.modules.public_footprint.domain.browser_actions import (
    BrowserActionKind,
    BrowserActionStep,
    BrowserHttpMethod,
    BrowserValueClassification,
)


class _Locator:
    def __init__(
        self,
        *,
        count: int = 1,
        attributes: dict[str, str | None] | None = None,
        is_button: bool = False,
        is_form: bool = False,
        fields: list[_Locator] | None = None,
        controls: int = 1,
    ) -> None:
        self._count = count
        self.attributes = attributes or {}
        self.is_button = is_button
        self.is_form = is_form
        self.fields = fields or []
        self.controls = controls
        self.calls: list[tuple[str, object]] = []

    def count(self) -> int:
        return self._count

    def get_attribute(self, name: str) -> str | None:
        return self.attributes.get(name)

    def locator(self, selector: str) -> _Locator:
        if selector == "xpath=self::button":
            return _Locator(count=1 if self.is_button else 0)
        if selector == "xpath=self::form":
            return _Locator(count=1 if self.is_form else 0)
        if selector == "input, textarea, select":
            result = _Locator()
            result.fields = self.fields
            return result
        if selector.startswith('button[type="submit"]'):
            return _Locator(count=self.controls)
        return _Locator(count=0)

    def all(self) -> list[_Locator]:
        return self.fields

    @property
    def first(self) -> _Locator:
        return self

    def click(self, *, timeout: int) -> None:
        self.calls.append(("click", timeout))

    def fill(self, value: str, *, timeout: int) -> None:
        self.calls.append(("fill", (value, timeout)))

    def select_option(self, value: str, *, timeout: int) -> None:
        self.calls.append(("select", (value, timeout)))

    def check(self, *, timeout: int) -> None:
        self.calls.append(("check", timeout))

    def uncheck(self, *, timeout: int) -> None:
        self.calls.append(("uncheck", timeout))

    def wait_for(self, *, state: str, timeout: int) -> None:
        self.calls.append(("wait", (state, timeout)))


class _Page:
    def __init__(self, locator: _Locator | None = None) -> None:
        self.url = "https://example.com/public/form"
        self._locator = locator or _Locator()
        self.calls: list[tuple[str, object]] = []

    def locator(self, selector: str) -> _Locator:
        del selector
        return self._locator

    def goto(self, url: str, *, wait_until: str, timeout: int) -> None:
        self.calls.append(("goto", (url, wait_until, timeout)))

    def wait_for_load_state(self, state: str, *, timeout: int) -> None:
        self.calls.append(("load", (state, timeout)))


def _page(locator: _Locator | None = None) -> Any:
    return cast(Any, _Page(locator))


def _step(**values: object) -> BrowserActionStep:
    defaults: dict[str, object] = {
        "step_id": "step",
        "kind": BrowserActionKind.CLICK,
        "selector": "#target",
    }
    defaults.update(values)
    return BrowserActionStep(**defaults)  # type: ignore[arg-type]


def test_exact_locator_and_dispatch_fail_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(steps.BrowserActionExecutionError, match="selector_missing"):
        steps.exact_locator(_page(), None)
    with pytest.raises(steps.BrowserActionPolicyDeniedError, match="selector_not_unique"):
        steps.exact_locator(_page(_Locator(count=2)), "#target")

    monkeypatch.delitem(steps._STEP_HANDLERS, BrowserActionKind.CLICK)
    with pytest.raises(steps.BrowserActionExecutionError, match="unsupported_browser_action_kind"):
        steps.execute_step(
            _page(),
            _step(),
            timeout=100,
            state=steps.BrowserActionRuntimeState(),
        )


def test_click_preflight_rejects_submit_controls_and_authorizes_links(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for input_type in ("submit", "image"):
        locator = _Locator(attributes={"type": input_type})
        with pytest.raises(steps.BrowserActionPolicyDeniedError, match="typed_submit_form"):
            steps._preflight_click(
                cast(Any, object()),
                cast(Any, object()),
                cast(Any, object()),
                _page(locator),
                cast(Any, locator),
                now=cast(Any, object()),
            )

    button = _Locator(attributes={"type": None}, is_button=True)
    with pytest.raises(steps.BrowserActionPolicyDeniedError, match="submit_button"):
        steps._preflight_click(
            cast(Any, object()),
            cast(Any, object()),
            cast(Any, object()),
            _page(button),
            cast(Any, button),
            now=cast(Any, object()),
        )

    calls: list[tuple[object, ...]] = []
    monkeypatch.setattr(
        steps,
        "authorize_browser_action_transition",
        lambda *args, **kwargs: calls.append((*args, kwargs)),
    )
    link = _Locator(attributes={"type": "button", "href": "results"})
    page = _page(link)
    steps._preflight_click(
        cast(Any, object()),
        cast(Any, object()),
        cast(Any, object()),
        page,
        cast(Any, link),
        now=cast(Any, object()),
    )
    assert calls
    assert calls[0][3] == "https://example.com/public/results"


def test_sensitive_fill_and_check_targets_are_denied() -> None:
    for field_type in ("password", "file", "hidden"):
        with pytest.raises(steps.BrowserActionPolicyDeniedError, match="sensitive_fill"):
            steps._deny_sensitive_fill(_Locator(attributes={"type": field_type}))  # type: ignore[arg-type]

    with pytest.raises(steps.BrowserActionPolicyDeniedError, match="check_target_type_denied"):
        steps._validate_check_target(  # type: ignore[arg-type]
            _Locator(attributes={"type": "text"}),
            allow_radio=True,
        )
    with pytest.raises(steps.BrowserActionPolicyDeniedError, match="check_target_type_denied"):
        steps._validate_check_target(  # type: ignore[arg-type]
            _Locator(attributes={"type": "radio"}),
            allow_radio=False,
        )
    steps._validate_check_target(  # type: ignore[arg-type]
        _Locator(attributes={"type": "checkbox"}),
        allow_radio=False,
    )


def test_form_inspection_rejects_shape_method_metadata_fields_and_control(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    step = _step(
        kind=BrowserActionKind.SUBMIT_FORM,
        selector="form#search",
        expected_form_action_url="https://example.com/public/search",
        expected_form_method=BrowserHttpMethod.POST,
    )
    common = (
        cast(Any, object()),
        cast(Any, object()),
        cast(Any, object()),
    )

    with pytest.raises(steps.BrowserActionPolicyDeniedError, match="resolve_to_form"):
        steps._inspect_form(
            *common,
            _page(),
            cast(Any, _Locator(is_form=False)),
            step,
            now=cast(Any, object()),
        )

    unsupported = _Locator(
        is_form=True,
        attributes={"action": "/public/search", "method": "PUT"},
    )
    with pytest.raises(steps.BrowserActionPolicyDeniedError, match="method_not_supported"):
        steps._inspect_form(
            *common,
            _page(),
            cast(Any, unsupported),
            step,
            now=cast(Any, object()),
        )

    mismatch = _Locator(
        is_form=True,
        attributes={"action": "/public/other", "method": "POST"},
    )
    with pytest.raises(steps.BrowserActionPolicyDeniedError, match="metadata_does_not_match"):
        steps._inspect_form(
            *common,
            _page(),
            cast(Any, mismatch),
            step,
            now=cast(Any, object()),
        )

    for field_type, reason in (("password", "password_field"), ("file", "file_input")):
        form = _Locator(
            is_form=True,
            attributes={"action": "/public/search", "method": "POST"},
            fields=[_Locator(attributes={"type": field_type})],
        )
        with pytest.raises(steps.BrowserActionPolicyDeniedError, match=reason):
            steps._inspect_form(
                *common,
                _page(),
                cast(Any, form),
                step,
                now=cast(Any, object()),
            )

    no_control = _Locator(
        is_form=True,
        attributes={"action": "/public/search", "method": "POST"},
        controls=0,
    )
    with pytest.raises(steps.BrowserActionPolicyDeniedError, match="submit_control_missing"):
        steps._inspect_form(
            *common,
            _page(),
            cast(Any, no_control),
            step,
            now=cast(Any, object()),
        )

    authorized: list[object] = []
    monkeypatch.setattr(
        steps,
        "authorize_browser_action_transition",
        lambda *args, **kwargs: authorized.append((args, kwargs)),
    )
    valid = _Locator(
        is_form=True,
        attributes={"action": "/public/search", "method": "POST"},
    )
    steps._inspect_form(
        *common,
        _page(),
        cast(Any, valid),
        step,
        now=cast(Any, object()),
    )
    assert authorized


def test_step_handlers_cover_missing_values_and_typed_operations() -> None:
    state = steps.BrowserActionRuntimeState()
    page_object = _Page(_Locator())
    page = cast(Any, page_object)

    missing_navigation = cast(
        BrowserActionStep,
        SimpleNamespace(target_url=None),
    )
    with pytest.raises(steps.BrowserActionExecutionError, match="navigation_target_missing"):
        steps._navigate(page, missing_navigation, 100, state)

    for handler in (steps._fill, steps._select):
        missing_value = cast(
            BrowserActionStep,
            SimpleNamespace(selector="#target", value=None),
        )
        with pytest.raises(steps.BrowserActionExecutionError, match="value_missing"):
            handler(page, missing_value, 100, state)

    missing_form = cast(
        BrowserActionStep,
        SimpleNamespace(
            selector="form",
            expected_form_action_url=None,
            expected_form_method=None,
        ),
    )
    with pytest.raises(steps.BrowserActionExecutionError, match="form_metadata_missing"):
        steps._submit_form(page, missing_form, 100, state)

    steps._navigate(
        page,
        _step(
            kind=BrowserActionKind.NAVIGATE,
            selector=None,
            target_url="https://example.com/public/next",
        ),
        101,
        state,
    )
    steps._wait_navigation(page, _step(), 102, state)
    steps._click(page, _step(), 103, state)
    steps._fill(
        page,
        _step(
            kind=BrowserActionKind.FILL,
            value="public",
            value_classification=BrowserValueClassification.PUBLIC_NON_SECRET,
        ),
        104,
        state,
    )
    steps._select(
        page,
        _step(
            kind=BrowserActionKind.SELECT,
            value="public",
            value_classification=BrowserValueClassification.PUBLIC_NON_SECRET,
        ),
        105,
        state,
    )
    steps._check(page, _step(kind=BrowserActionKind.CHECK), 106, state)
    steps._uncheck(page, _step(kind=BrowserActionKind.UNCHECK), 107, state)
    steps._wait_dom(
        page,
        _step(kind=BrowserActionKind.WAIT_FOR_DOM_CONDITION),
        108,
        state,
    )
    assert page_object.calls


def test_submit_guard_matching_and_submit_handler_reset_guard() -> None:
    assert steps.submit_guard_allows(
        "https://example.com/public/search?x=1",
        BrowserHttpMethod.POST,
        ("https://example.com/public/search", BrowserHttpMethod.POST),
    )
    assert not steps.submit_guard_allows(
        "https://example.com/public/other",
        BrowserHttpMethod.POST,
        ("https://example.com/public/search", BrowserHttpMethod.POST),
    )
    assert not steps.submit_guard_allows(
        "https://example.com/public/search",
        BrowserHttpMethod.GET,
        ("https://example.com/public/search", BrowserHttpMethod.POST),
    )

    state = steps.BrowserActionRuntimeState()
    form = _Locator(is_form=True)
    page = _page(form)
    step = _step(
        kind=BrowserActionKind.SUBMIT_FORM,
        selector="form",
        expected_form_action_url="https://example.com/public/search",
        expected_form_method=BrowserHttpMethod.POST,
    )
    steps._submit_form(page, step, 200, state)
    assert state.submission_guard is None
