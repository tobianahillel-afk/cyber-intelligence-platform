from __future__ import annotations

from datetime import UTC, datetime, timedelta
from hashlib import sha256
from uuid import uuid4

import pytest

from cip.modules.public_footprint.domain.artifacts import (
    BrowserArtifactKind,
    BrowserArtifactState,
    BrowserEvidenceArtifact,
    BrowserScreenshotMode,
)
from cip.modules.public_footprint.domain.browser_actions import (
    BrowserActionKind,
    BrowserActionPlan,
    BrowserActionStep,
    BrowserHttpMethod,
    BrowserTransitionRule,
)
from cip.modules.public_footprint.infrastructure.artifact_persistence import (
    _coerce_utc,
    load_browser_artifacts_for_plan,
    persist_browser_artifact,
)
from cip.modules.public_footprint.infrastructure.browser_action_persistence import (
    load_browser_action_plan,
    persist_browser_action_plan,
)
from cip.shared.persistence.metadata import get_metadata
from cip.shared.persistence.session import create_database_engine, create_session_factory

NOW = datetime(2026, 8, 16, 18, 30, tzinfo=UTC)


def _plan() -> BrowserActionPlan:
    return BrowserActionPlan(
        plan_id=uuid4(),
        version=1,
        source_id="public-web",
        provider_id="fixture-provider",
        target_id="fixture-target",
        purpose="corporate-public-footprint",
        steps=(
            BrowserActionStep(
                "shot",
                BrowserActionKind.SCREENSHOT,
                screenshot_mode=BrowserScreenshotMode.VIEWPORT,
                retain_raw_artifact=True,
            ),
            BrowserActionStep(
                "download",
                BrowserActionKind.DOWNLOAD,
                selector="a#report",
                expected_download_url="https://example.com/public/report.txt",
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


def _artifact(plan: BrowserActionPlan, **overrides: object) -> BrowserEvidenceArtifact:
    values: dict[str, object] = {
        "source_id": plan.source_id,
        "provider_id": plan.provider_id,
        "target_id": plan.target_id,
        "job_id": uuid4(),
        "plan_id": plan.plan_id,
        "plan_version": plan.version,
        "step_id": "shot",
        "kind": BrowserArtifactKind.SCREENSHOT,
        "state": BrowserArtifactState.PROCESSED,
        "page_url": "https://example.com/public/page",
        "source_url": "https://example.com/public/page",
        "captured_at": NOW,
        "content_hash_sha256": sha256(b"png").hexdigest(),
        "byte_size": 3,
        "media_type": "image/png",
        "source_locator": f"browser-action:{plan.plan_id}:1:shot",
        "raw_retention_allowed": True,
        "raw_retained": True,
        "storage_uri": "s3://bucket/object",
        "retention_until": NOW + timedelta(days=7),
        "screenshot_mode": BrowserScreenshotMode.VIEWPORT,
        "viewport_width": 800,
        "viewport_height": 600,
    }
    values.update(overrides)
    return BrowserEvidenceArtifact(**values)  # type: ignore[arg-type]


def _session_factory():
    engine = create_database_engine("sqlite+pysqlite:///:memory:")
    get_metadata().create_all(engine)
    return create_session_factory(engine)


def test_artifact_action_fields_roundtrip_with_plan() -> None:
    factory = _session_factory()
    plan = _plan()
    with factory() as session:
        persist_browser_action_plan(session, plan, now=NOW)
        session.commit()
        loaded = load_browser_action_plan(session, plan.plan_id, plan.version)

    assert loaded == plan
    assert loaded is not None
    assert loaded.steps[0].screenshot_mode is BrowserScreenshotMode.VIEWPORT
    assert loaded.steps[0].retain_raw_artifact is True
    assert loaded.steps[1].expected_download_url.endswith("report.txt")


def test_artifact_metadata_roundtrip_is_idempotent() -> None:
    factory = _session_factory()
    plan = _plan()
    artifact = _artifact(plan)
    with factory() as session:
        persist_browser_action_plan(session, plan, now=NOW)
        persist_browser_artifact(session, artifact, now=NOW)
        persist_browser_artifact(session, artifact, now=NOW + timedelta(seconds=1))
        session.commit()
        loaded = load_browser_artifacts_for_plan(session, plan.plan_id, plan.version)

    assert loaded == (artifact,)


def test_artifact_identity_collision_is_rejected() -> None:
    factory = _session_factory()
    plan = _plan()
    artifact = _artifact(plan)
    conflicting = _artifact(plan, job_id=uuid4(), id=uuid4())
    assert conflicting.identity_key == artifact.identity_key

    with factory() as session:
        persist_browser_action_plan(session, plan, now=NOW)
        persist_browser_artifact(session, artifact, now=NOW)
        with pytest.raises(ValueError, match="identity collision"):
            persist_browser_artifact(session, conflicting, now=NOW)


def test_artifact_query_is_scoped_to_plan_version() -> None:
    factory = _session_factory()
    plan = _plan()
    with factory() as session:
        persist_browser_action_plan(session, plan, now=NOW)
        persist_browser_artifact(session, _artifact(plan), now=NOW)
        session.commit()
        assert load_browser_artifacts_for_plan(session, uuid4(), 1) == ()


def test_artifact_persistence_coerces_aware_timestamp_to_utc() -> None:
    offset = NOW.astimezone(UTC)
    assert _coerce_utc(offset) == NOW
    assert _coerce_utc(offset).tzinfo is UTC
