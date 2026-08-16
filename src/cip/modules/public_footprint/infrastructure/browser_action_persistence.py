from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

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
from cip.modules.public_footprint.infrastructure.browser_action_models import (
    BrowserActionCheckpointRecord,
    BrowserActionPlanRecord,
)
from cip.shared.kernel.time import require_aware_utc


def persist_browser_action_plan(
    session: Session,
    plan: BrowserActionPlan,
    *,
    now: datetime,
) -> BrowserActionCheckpoint:
    created_at = require_aware_utc(now, field_name="now")
    payload_json = _serialize_plan(plan)
    payload_hash = hashlib.sha256(payload_json.encode("utf-8")).hexdigest()
    existing = session.get(BrowserActionPlanRecord, (plan.plan_id, plan.version))
    if existing is None:
        session.add(
            BrowserActionPlanRecord(
                plan_id=plan.plan_id,
                plan_version=plan.version,
                source_id=plan.source_id,
                provider_id=plan.provider_id,
                target_id=plan.target_id,
                purpose=plan.purpose,
                payload_hash_sha256=payload_hash,
                payload_json=payload_json,
                created_at=created_at,
            )
        )
        checkpoint = BrowserActionCheckpoint(
            plan_id=plan.plan_id,
            plan_version=plan.version,
            step_states=tuple(BrowserStepState.PENDING for _ in plan.steps),
        )
        session.add(
            BrowserActionCheckpointRecord(
                plan_id=plan.plan_id,
                plan_version=plan.version,
                step_states=[state.value for state in checkpoint.step_states],
                updated_at=created_at,
            )
        )
        session.flush()
        return checkpoint
    _validate_existing_plan(existing, plan, payload_json, payload_hash)
    checkpoint = load_browser_action_checkpoint(session, plan.plan_id, plan.version)
    if checkpoint is None:
        raise ValueError("browser action plan is missing its checkpoint")
    return checkpoint


def load_browser_action_plan(
    session: Session,
    plan_id: UUID,
    plan_version: int,
) -> BrowserActionPlan | None:
    record = session.get(BrowserActionPlanRecord, (plan_id, plan_version))
    if record is None:
        return None
    payload = json.loads(record.payload_json)
    if not isinstance(payload, dict):
        raise ValueError("stored browser action plan payload is invalid")
    return _decode_plan(payload)


def load_browser_action_checkpoint(
    session: Session,
    plan_id: UUID,
    plan_version: int,
) -> BrowserActionCheckpoint | None:
    record = session.get(BrowserActionCheckpointRecord, (plan_id, plan_version))
    if record is None:
        return None
    return BrowserActionCheckpoint(
        plan_id=record.plan_id,
        plan_version=record.plan_version,
        step_states=tuple(BrowserStepState(value) for value in record.step_states),
    )


def save_browser_action_checkpoint(
    session: Session,
    checkpoint: BrowserActionCheckpoint,
    *,
    now: datetime,
) -> None:
    updated_at = require_aware_utc(now, field_name="now")
    plan = load_browser_action_plan(session, checkpoint.plan_id, checkpoint.plan_version)
    if plan is None:
        raise ValueError("browser action checkpoint references an unknown plan")
    if len(checkpoint.step_states) != len(plan.steps):
        raise ValueError("browser action checkpoint step count does not match plan")
    record = session.get(
        BrowserActionCheckpointRecord,
        (checkpoint.plan_id, checkpoint.plan_version),
    )
    if record is None:
        session.add(
            BrowserActionCheckpointRecord(
                plan_id=checkpoint.plan_id,
                plan_version=checkpoint.plan_version,
                step_states=[state.value for state in checkpoint.step_states],
                updated_at=updated_at,
            )
        )
    else:
        record.step_states = [state.value for state in checkpoint.step_states]
        record.updated_at = updated_at
    session.flush()


def recover_interrupted_checkpoint(
    plan: BrowserActionPlan,
    checkpoint: BrowserActionCheckpoint,
) -> BrowserActionCheckpoint:
    if checkpoint.plan_id != plan.plan_id or checkpoint.plan_version != plan.version:
        raise ValueError("browser action checkpoint does not belong to plan")
    if len(checkpoint.step_states) != len(plan.steps):
        raise ValueError("browser action checkpoint step count does not match plan")
    states = list(checkpoint.step_states)
    for index, state in enumerate(states):
        if state is not BrowserStepState.EXECUTING:
            continue
        step = plan.steps[index]
        states[index] = (
            BrowserStepState.PENDING
            if step.replay_policy is BrowserStepReplayPolicy.SAFE
            else BrowserStepState.NEEDS_VERIFICATION
        )
        for following in range(index + 1, len(states)):
            states[following] = BrowserStepState.PENDING
        break
    return BrowserActionCheckpoint(
        plan_id=checkpoint.plan_id,
        plan_version=checkpoint.plan_version,
        step_states=tuple(states),
    )


def _validate_existing_plan(
    record: BrowserActionPlanRecord,
    plan: BrowserActionPlan,
    payload_json: str,
    payload_hash: str,
) -> None:
    actual = (
        record.source_id,
        record.provider_id,
        record.target_id,
        record.purpose,
        record.payload_hash_sha256,
        record.payload_json,
    )
    expected = (
        plan.source_id,
        plan.provider_id,
        plan.target_id,
        plan.purpose,
        payload_hash,
        payload_json,
    )
    if actual != expected:
        raise ValueError("browser action plan identity collision")


def _serialize_plan(plan: BrowserActionPlan) -> str:
    return json.dumps(_encode_plan(plan), sort_keys=True, separators=(",", ":"))


def _encode_plan(plan: BrowserActionPlan) -> dict[str, object]:
    return {
        "plan_id": str(plan.plan_id),
        "version": plan.version,
        "source_id": plan.source_id,
        "provider_id": plan.provider_id,
        "target_id": plan.target_id,
        "purpose": plan.purpose,
        "steps": [_encode_step(step) for step in plan.steps],
        "allowed_transitions": [
            {
                "host": rule.host,
                "path_prefix": rule.path_prefix,
                "methods": sorted(method.value for method in rule.methods),
            }
            for rule in plan.allowed_transitions
        ],
        "max_actions": plan.max_actions,
        "max_total_value_chars": plan.max_total_value_chars,
    }


def _encode_step(step: BrowserActionStep) -> dict[str, object | None]:
    return {
        "step_id": step.step_id,
        "kind": step.kind.value,
        "selector": step.selector,
        "value": step.value,
        "value_classification": (
            step.value_classification.value if step.value_classification is not None else None
        ),
        "target_url": step.target_url,
        "expected_form_action_url": step.expected_form_action_url,
        "expected_form_method": (
            step.expected_form_method.value if step.expected_form_method is not None else None
        ),
        "timeout_ms": step.timeout_ms,
        "replay_policy": step.replay_policy.value,
    }


def _decode_plan(payload: dict[str, Any]) -> BrowserActionPlan:
    transitions = tuple(
        BrowserTransitionRule(
            host=_required_str(item, "host"),
            path_prefix=_required_str(item, "path_prefix"),
            methods=frozenset(BrowserHttpMethod(value) for value in _required_list(item, "methods")),
        )
        for item in _mapping_list(payload, "allowed_transitions")
    )
    steps = tuple(_decode_step(item) for item in _mapping_list(payload, "steps"))
    return BrowserActionPlan(
        plan_id=UUID(_required_str(payload, "plan_id")),
        version=_required_int(payload, "version"),
        source_id=_required_str(payload, "source_id"),
        provider_id=_required_str(payload, "provider_id"),
        target_id=_required_str(payload, "target_id"),
        purpose=_required_str(payload, "purpose"),
        steps=steps,
        allowed_transitions=transitions,
        max_actions=_required_int(payload, "max_actions"),
        max_total_value_chars=_required_int(payload, "max_total_value_chars"),
    )


def _decode_step(payload: dict[str, Any]) -> BrowserActionStep:
    classification = payload.get("value_classification")
    method = payload.get("expected_form_method")
    return BrowserActionStep(
        step_id=_required_str(payload, "step_id"),
        kind=BrowserActionKind(_required_str(payload, "kind")),
        selector=_optional_str(payload.get("selector")),
        value=_optional_str(payload.get("value")),
        value_classification=(
            BrowserValueClassification(classification) if isinstance(classification, str) else None
        ),
        target_url=_optional_str(payload.get("target_url")),
        expected_form_action_url=_optional_str(payload.get("expected_form_action_url")),
        expected_form_method=BrowserHttpMethod(method) if isinstance(method, str) else None,
        timeout_ms=_optional_int(payload.get("timeout_ms")),
        replay_policy=BrowserStepReplayPolicy(_required_str(payload, "replay_policy")),
    )


def _mapping_list(payload: dict[str, Any], key: str) -> list[dict[str, Any]]:
    value = payload.get(key)
    if not isinstance(value, list) or not all(isinstance(item, dict) for item in value):
        raise ValueError(f"stored browser action plan {key} is invalid")
    return value


def _required_list(payload: dict[str, Any], key: str) -> list[str]:
    value = payload.get(key)
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError(f"stored browser action plan {key} is invalid")
    return value


def _required_str(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str):
        raise ValueError(f"stored browser action plan {key} is invalid")
    return value


def _required_int(payload: dict[str, Any], key: str) -> int:
    value = payload.get(key)
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError(f"stored browser action plan {key} is invalid")
    return value


def _optional_str(value: object) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("stored browser action plan optional string is invalid")
    return value


def _optional_int(value: object) -> int | None:
    if value is None:
        return None
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("stored browser action plan optional integer is invalid")
    return value
