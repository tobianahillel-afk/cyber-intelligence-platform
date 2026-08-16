from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, delete
from sqlalchemy.orm import Session

from cip.modules.public_footprint.domain.browser_actions import (
    BrowserActionCheckpoint,
    BrowserActionKind,
    BrowserActionPlan,
    BrowserActionStep,
    BrowserHttpMethod,
    BrowserStepState,
    BrowserTransitionRule,
)
from cip.modules.public_footprint.infrastructure import browser_action_persistence as persistence
from cip.modules.public_footprint.infrastructure.browser_action_models import (
    BrowserActionCheckpointRecord,
    BrowserActionPlanRecord,
)

NOW = datetime(2026, 8, 16, 17, 0, tzinfo=UTC)


def _plan() -> BrowserActionPlan:
    return BrowserActionPlan(
        plan_id=uuid4(),
        version=1,
        source_id="source",
        provider_id="provider",
        target_id="target",
        purpose="corporate-public-footprint",
        steps=(
            BrowserActionStep(
                step_id="navigate",
                kind=BrowserActionKind.NAVIGATE,
                target_url="https://example.com/public/form",
            ),
            BrowserActionStep(
                step_id="submit",
                kind=BrowserActionKind.SUBMIT_FORM,
                selector="form#search",
                expected_form_action_url="https://example.com/public/search",
                expected_form_method=BrowserHttpMethod.GET,
            ),
        ),
        allowed_transitions=(
            BrowserTransitionRule(
                host="example.com",
                path_prefix="/public",
                methods=frozenset({BrowserHttpMethod.GET}),
            ),
        ),
        max_actions=2,
        max_total_value_chars=0,
    )


def _session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    BrowserActionPlanRecord.__table__.create(engine)
    BrowserActionCheckpointRecord.__table__.create(engine)
    return Session(engine)


def test_load_missing_records_returns_none() -> None:
    with _session() as session:
        plan_id = uuid4()
        assert persistence.load_browser_action_plan(session, plan_id, 1) is None
        assert persistence.load_browser_action_checkpoint(session, plan_id, 1) is None


def test_existing_plan_without_checkpoint_fails_closed() -> None:
    plan = _plan()
    with _session() as session:
        persistence.persist_browser_action_plan(session, plan, now=NOW)
        session.execute(
            delete(BrowserActionCheckpointRecord).where(
                BrowserActionCheckpointRecord.plan_id == plan.plan_id,
                BrowserActionCheckpointRecord.plan_version == plan.version,
            )
        )
        session.commit()

        with pytest.raises(ValueError, match="missing its checkpoint"):
            persistence.persist_browser_action_plan(session, plan, now=NOW)


def test_load_rejects_non_mapping_payload() -> None:
    plan = _plan()
    with _session() as session:
        persistence.persist_browser_action_plan(session, plan, now=NOW)
        record = session.get(BrowserActionPlanRecord, (plan.plan_id, plan.version))
        assert record is not None
        record.payload_json = "[]"
        session.commit()

        with pytest.raises(ValueError, match="payload is invalid"):
            persistence.load_browser_action_plan(session, plan.plan_id, plan.version)


def test_save_rejects_step_count_and_recreates_missing_checkpoint() -> None:
    plan = _plan()
    with _session() as session:
        persistence.persist_browser_action_plan(session, plan, now=NOW)
        mismatched = BrowserActionCheckpoint(
            plan_id=plan.plan_id,
            plan_version=plan.version,
            step_states=(BrowserStepState.PENDING,),
        )
        with pytest.raises(ValueError, match="step count does not match"):
            persistence.save_browser_action_checkpoint(session, mismatched, now=NOW)

        session.execute(
            delete(BrowserActionCheckpointRecord).where(
                BrowserActionCheckpointRecord.plan_id == plan.plan_id,
                BrowserActionCheckpointRecord.plan_version == plan.version,
            )
        )
        session.flush()
        replacement = BrowserActionCheckpoint(
            plan_id=plan.plan_id,
            plan_version=plan.version,
            step_states=(BrowserStepState.COMPLETED, BrowserStepState.PENDING),
        )
        persistence.save_browser_action_checkpoint(session, replacement, now=NOW)
        assert persistence.load_browser_action_checkpoint(session, plan.plan_id, 1) == replacement


def test_recovery_rejects_step_count_mismatch() -> None:
    plan = _plan()
    mismatched = BrowserActionCheckpoint(
        plan_id=plan.plan_id,
        plan_version=plan.version,
        step_states=(BrowserStepState.PENDING,),
    )
    with pytest.raises(ValueError, match="step count does not match"):
        persistence.recover_interrupted_checkpoint(plan, mismatched)


def test_stored_payload_shape_helpers_fail_closed() -> None:
    invalid_lists: list[tuple[dict[str, Any], str]] = [
        ({"items": "not-a-list"}, "items"),
        ({"items": ["not-a-mapping"]}, "items"),
    ]
    for payload, key in invalid_lists:
        with pytest.raises(ValueError, match="items is invalid"):
            persistence._mapping_list(payload, key)

    for value in ("not-a-list", [1]):
        with pytest.raises(ValueError, match="methods is invalid"):
            persistence._required_list({"methods": value}, "methods")

    with pytest.raises(ValueError, match="source_id is invalid"):
        persistence._required_str({"source_id": 3}, "source_id")

    for value in (True, "1"):
        with pytest.raises(ValueError, match="version is invalid"):
            persistence._required_int({"version": value}, "version")

    assert persistence._optional_str(None) is None
    assert persistence._optional_str("value") == "value"
    with pytest.raises(ValueError, match="optional string is invalid"):
        persistence._optional_str(42)

    assert persistence._optional_int(None) is None
    assert persistence._optional_int(42) == 42
    for value in (True, "42"):
        with pytest.raises(ValueError, match="optional integer is invalid"):
            persistence._optional_int(value)


def test_decode_rejects_invalid_transition_and_step_collections() -> None:
    plan = _plan()
    payload = persistence._encode_plan(plan)

    bad_transitions = dict(payload)
    bad_transitions["allowed_transitions"] = ["bad"]
    with pytest.raises(ValueError, match="allowed_transitions is invalid"):
        persistence._decode_plan(bad_transitions)

    bad_steps = dict(payload)
    bad_steps["steps"] = ["bad"]
    with pytest.raises(ValueError, match="steps is invalid"):
        persistence._decode_plan(bad_steps)


def test_decode_step_rejects_invalid_optional_shapes() -> None:
    base: dict[str, Any] = {
        "step_id": "fill",
        "kind": BrowserActionKind.FILL.value,
        "selector": "#field",
        "value": "public",
        "value_classification": None,
        "target_url": None,
        "expected_form_action_url": None,
        "expected_form_method": None,
        "timeout_ms": None,
        "replay_policy": "safe",
    }
    bad_selector = dict(base)
    bad_selector["selector"] = 123
    with pytest.raises(ValueError, match="optional string is invalid"):
        persistence._decode_step(bad_selector)

    bad_timeout = dict(base)
    bad_timeout["timeout_ms"] = "100"
    with pytest.raises(ValueError, match="optional integer is invalid"):
        persistence._decode_step(bad_timeout)
