from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID

_MAX_IDENTITY = 200
_MAX_PURPOSE = 500
_MAX_SELECTOR = 1_000
_MAX_VALUE = 4_000
_MAX_STEPS = 32
_MAX_TRANSITIONS = 32
_MAX_TIMEOUT_MS = 120_000


class BrowserActionKind(StrEnum):
    NAVIGATE = "navigate"
    CLICK = "click"
    FILL = "fill"
    SELECT = "select"
    CHECK = "check"
    UNCHECK = "uncheck"
    SUBMIT_FORM = "submit_form"
    WAIT_FOR_NAVIGATION = "wait_for_navigation"
    WAIT_FOR_DOM_CONDITION = "wait_for_dom_condition"


class BrowserHttpMethod(StrEnum):
    GET = "GET"
    POST = "POST"


class BrowserStepReplayPolicy(StrEnum):
    SAFE = "safe"
    VERIFY_BEFORE_REPLAY = "verify_before_replay"


class BrowserStepState(StrEnum):
    PENDING = "pending"
    EXECUTING = "executing"
    COMPLETED = "completed"
    NEEDS_VERIFICATION = "needs_verification"


class BrowserValueClassification(StrEnum):
    PUBLIC_NON_SECRET = "public_non_secret"


@dataclass(frozen=True, slots=True)
class BrowserTransitionRule:
    host: str
    path_prefix: str
    methods: frozenset[BrowserHttpMethod]

    def __post_init__(self) -> None:
        host = self.host.strip().casefold()
        if not host or len(host) > _MAX_IDENTITY or "://" in host or "/" in host:
            raise ValueError("browser transition host is invalid")
        if not self.path_prefix.startswith("/") or len(self.path_prefix) > _MAX_SELECTOR:
            raise ValueError("browser transition path_prefix is invalid")
        if not self.methods:
            raise ValueError("browser transition methods cannot be empty")
        object.__setattr__(self, "host", host)
        object.__setattr__(self, "methods", frozenset(self.methods))


@dataclass(frozen=True, slots=True)
class BrowserActionStep:
    step_id: str
    kind: BrowserActionKind
    selector: str | None = None
    value: str | None = None
    value_classification: BrowserValueClassification | None = None
    target_url: str | None = None
    expected_form_action_url: str | None = None
    expected_form_method: BrowserHttpMethod | None = None
    timeout_ms: int | None = None
    replay_policy: BrowserStepReplayPolicy = BrowserStepReplayPolicy.SAFE

    def __post_init__(self) -> None:
        _bounded_text(self.step_id, field_name="step_id", maximum=_MAX_IDENTITY)
        _optional_bounded_text(self.selector, field_name="selector", maximum=_MAX_SELECTOR)
        _optional_bounded_text(self.value, field_name="value", maximum=_MAX_VALUE)
        _optional_bounded_text(
            self.target_url,
            field_name="target_url",
            maximum=_MAX_VALUE,
        )
        _optional_bounded_text(
            self.expected_form_action_url,
            field_name="expected_form_action_url",
            maximum=_MAX_VALUE,
        )
        if self.timeout_ms is not None and not 1 <= self.timeout_ms <= _MAX_TIMEOUT_MS:
            raise ValueError("timeout_ms must be between 1 and 120000")
        _validate_step_shape(self)


@dataclass(frozen=True, slots=True)
class BrowserActionPlan:
    plan_id: UUID
    version: int
    source_id: str
    provider_id: str
    target_id: str
    purpose: str
    steps: tuple[BrowserActionStep, ...]
    allowed_transitions: tuple[BrowserTransitionRule, ...]
    max_actions: int
    max_total_value_chars: int

    def __post_init__(self) -> None:
        if self.version < 1:
            raise ValueError("browser action plan version must be positive")
        for field_name, value in (
            ("source_id", self.source_id),
            ("provider_id", self.provider_id),
            ("target_id", self.target_id),
        ):
            _bounded_text(value, field_name=field_name, maximum=_MAX_IDENTITY)
        _bounded_text(self.purpose, field_name="purpose", maximum=_MAX_PURPOSE)
        if not self.steps or len(self.steps) > _MAX_STEPS:
            raise ValueError("browser action plan must contain between 1 and 32 steps")
        if not self.allowed_transitions or len(self.allowed_transitions) > _MAX_TRANSITIONS:
            raise ValueError("browser action plan must contain between 1 and 32 transitions")
        if not 1 <= self.max_actions <= _MAX_STEPS:
            raise ValueError("max_actions must be between 1 and 32")
        if len(self.steps) > self.max_actions:
            raise ValueError("browser action plan exceeds max_actions")
        if not 0 <= self.max_total_value_chars <= _MAX_VALUE * _MAX_STEPS:
            raise ValueError("max_total_value_chars is outside the reviewed bound")
        total_value_chars = sum(len(step.value or "") for step in self.steps)
        if total_value_chars > self.max_total_value_chars:
            raise ValueError("browser action plan exceeds max_total_value_chars")
        step_ids = [step.step_id for step in self.steps]
        if len(step_ids) != len(set(step_ids)):
            raise ValueError("browser action step ids must be unique")


@dataclass(frozen=True, slots=True)
class BrowserActionCheckpoint:
    plan_id: UUID
    plan_version: int
    step_states: tuple[BrowserStepState, ...]

    def __post_init__(self) -> None:
        if self.plan_version < 1:
            raise ValueError("browser action checkpoint version must be positive")
        if not self.step_states or len(self.step_states) > _MAX_STEPS:
            raise ValueError("browser action checkpoint step_states are invalid")
        needs_verification = False
        completed_prefix = True
        for state in self.step_states:
            if needs_verification and state is not BrowserStepState.PENDING:
                raise ValueError("steps after needs_verification must remain pending")
            if state is BrowserStepState.NEEDS_VERIFICATION:
                if not completed_prefix:
                    raise ValueError("needs_verification must follow a completed prefix")
                needs_verification = True
                completed_prefix = False
            elif state is BrowserStepState.COMPLETED:
                if not completed_prefix:
                    raise ValueError("completed steps must form a prefix")
            elif state in {BrowserStepState.EXECUTING, BrowserStepState.PENDING}:
                completed_prefix = False


def _validate_step_shape(step: BrowserActionStep) -> None:
    selector_kinds = {
        BrowserActionKind.CLICK,
        BrowserActionKind.FILL,
        BrowserActionKind.SELECT,
        BrowserActionKind.CHECK,
        BrowserActionKind.UNCHECK,
        BrowserActionKind.SUBMIT_FORM,
        BrowserActionKind.WAIT_FOR_DOM_CONDITION,
    }
    if step.kind in selector_kinds and step.selector is None:
        raise ValueError(f"{step.kind.value} requires a selector")
    if step.kind is BrowserActionKind.NAVIGATE:
        _validate_navigate(step)
    elif step.kind in {BrowserActionKind.FILL, BrowserActionKind.SELECT}:
        _validate_value_action(step)
    elif step.kind is BrowserActionKind.SUBMIT_FORM:
        _validate_submit(step)
    elif step.kind is BrowserActionKind.WAIT_FOR_NAVIGATION:
        _forbid_fields(
            step,
            "selector",
            "value",
            "value_classification",
            "target_url",
            "expected_form_action_url",
            "expected_form_method",
        )
    else:
        _forbid_fields(
            step,
            "value",
            "value_classification",
            "target_url",
            "expected_form_action_url",
            "expected_form_method",
        )


def _validate_navigate(step: BrowserActionStep) -> None:
    if step.target_url is None:
        raise ValueError("navigate requires target_url")
    _forbid_fields(
        step,
        "selector",
        "value",
        "value_classification",
        "expected_form_action_url",
        "expected_form_method",
    )


def _validate_value_action(step: BrowserActionStep) -> None:
    if (
        step.value is None
        or step.value_classification is not BrowserValueClassification.PUBLIC_NON_SECRET
    ):
        raise ValueError(f"{step.kind.value} requires an explicitly public non-secret value")
    _forbid_fields(step, "target_url", "expected_form_action_url", "expected_form_method")


def _validate_submit(step: BrowserActionStep) -> None:
    if step.expected_form_action_url is None or step.expected_form_method is None:
        raise ValueError("submit_form requires expected form action and method")
    if (
        step.expected_form_method is BrowserHttpMethod.POST
        and step.replay_policy is BrowserStepReplayPolicy.SAFE
    ):
        raise ValueError("POST submit_form cannot be blindly replayable")
    _forbid_fields(step, "value", "value_classification", "target_url")


def _forbid_fields(step: BrowserActionStep, *field_names: str) -> None:
    for field_name in field_names:
        if getattr(step, field_name) is not None:
            raise ValueError(f"{step.kind.value} does not allow {field_name}")


def _bounded_text(value: str, *, field_name: str, maximum: int) -> None:
    if not value or len(value) > maximum or "\x00" in value:
        raise ValueError(f"{field_name} is invalid")


def _optional_bounded_text(value: str | None, *, field_name: str, maximum: int) -> None:
    if value is not None:
        _bounded_text(value, field_name=field_name, maximum=maximum)
