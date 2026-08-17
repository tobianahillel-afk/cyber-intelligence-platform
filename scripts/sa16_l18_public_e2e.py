from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory, gettempdir
from uuid import NAMESPACE_URL, uuid5

from sa16_l18_public_fixture import FIXTURE_HOST, FixtureState, serve_fixture
from sa16_l18_public_support import (
    artifact_plan,
    build_factory,
    health_values,
    prepare_worker_source,
    run_artifact_plan,
    runtime_config,
    verify_artifacts,
    verify_public_persistence,
)

from cip.modules.collection_orchestration.application.automatic_public_web_runtime import (
    build_automatic_public_web_runtime,
)
from cip.modules.collection_orchestration.application.scheduler import schedule_due_jobs
from cip.modules.collection_orchestration.application.worker import WorkerStatus, run_worker_once
from cip.modules.data_governance.infrastructure.retention_loader import load_retention_policy
from cip.shared.persistence.session import session_scope


def main() -> None:
    now = datetime.now(UTC)
    quarantine_before = set(Path(gettempdir()).glob("cip-artifact-*"))
    with serve_fixture() as origin, TemporaryDirectory(prefix="cip-l18-public-") as root:
        organization_id = uuid5(NAMESPACE_URL, origin)
        factory = build_factory(Path(root), organization_id, origin, now)
        with session_scope(factory) as session:
            bundle = build_automatic_public_web_runtime(
                session,
                runtime_config(organization_id, now),
                now=now,
                timeout_seconds=15.0,
            )
        if len(bundle.targets) != 1 or len(bundle.schedules) != 1:
            raise RuntimeError("L18 automatic runtime did not build exactly one target")
        target = bundle.targets[0]
        schedule = bundle.schedules[0]
        prepare_worker_source(
            factory,
            target.id,
            schedule.adapter_id,
            FIXTURE_HOST,
            now,
        )

        with session_scope(factory) as session:
            if schedule_due_jobs(session, bundle.schedules, now=now) != 1:
                raise RuntimeError("L18 did not automatically schedule the first crawl job")
        first = run_worker_once(
            factory,
            worker_id="sa16-l18-public-first",
            adapters=bundle.adapters,
            retention_policy=load_retention_policy(Path("policies/retention.yml")),
            clock=lambda: now + timedelta(seconds=1),
        )
        if first.status is not WorkerStatus.SUCCEEDED:
            raise RuntimeError(
                "L18 first public worker failed: "
                f"status={first.status.value} error_code={first.error_code}"
            )
        first_metrics = health_values(factory, target.id)
        _assert_first_run_metrics(first_metrics)
        verify_public_persistence(
            factory,
            organization_id,
            target.id,
            schedule.adapter_id,
        )

        with session_scope(factory) as session:
            if schedule_due_jobs(session, bundle.schedules, now=now) != 0:
                raise RuntimeError("L18 scheduler duplicated an already completed crawl slot")
            if schedule_due_jobs(
                session,
                bundle.schedules,
                now=now + timedelta(seconds=301),
            ) != 1:
                raise RuntimeError("L18 did not schedule the incremental recrawl")
        second = run_worker_once(
            factory,
            worker_id="sa16-l18-public-recrawl",
            adapters=bundle.adapters,
            retention_policy=load_retention_policy(Path("policies/retention.yml")),
            clock=lambda: now + timedelta(seconds=302),
        )
        if second.status not in {WorkerStatus.SUCCEEDED, WorkerStatus.NOT_MODIFIED}:
            raise RuntimeError(
                "L18 public recrawl failed: "
                f"status={second.status.value} error_code={second.error_code}"
            )
        second_metrics = health_values(factory, target.id)
        if int(second_metrics.get("not_modified_pages", 0)) <= 0:
            raise RuntimeError("L18 recrawl persisted no HTTP-not-modified telemetry")
        if FixtureState.not_modified <= 0:
            raise RuntimeError("L18 fixture observed no conditional 304 request")

        plan = artifact_plan(target.id, origin, FIXTURE_HOST)
        run_artifact_plan(factory, target, plan, now)
        verify_artifacts(factory, plan)

    _assert_final_fixture_state(quarantine_before)
    print(
        "SA-16 L18 public composite passed: automatic_target=1 automatic_schedule=1 "
        "robots=1 sitemap_index=1 feed=1 security_txt=1 recursive=1 surfaces=1 "
        "browser_fallback=1 network_json=1 script_state=1 document=1 tombstone=1 "
        "checkpoint=1 recrawl_304=1 health=1 screenshot=1 download=1 "
        "quarantine_leaks=0",
        flush=True,
    )


def _assert_first_run_metrics(values: dict[str, object]) -> None:
    if values.get("browser_fallback_count") != 1:
        raise RuntimeError("L18 first crawl did not persist browser fallback telemetry")
    if values.get("configured_concurrency") != 3:
        raise RuntimeError("L18 configured crawl concurrency was not persisted")
    if values.get("effective_concurrency") != 1:
        raise RuntimeError("L18 browser-safe effective concurrency is not explicit")


def _assert_final_fixture_state(quarantine_before: set[Path]) -> None:
    if set(Path(gettempdir()).glob("cip-artifact-*")) != quarantine_before:
        raise RuntimeError("L18 public proof left quarantine bytes behind")
    if FixtureState.json_hits < 1 or FixtureState.xhr_hits < 1:
        raise RuntimeError("L18 rendered application endpoints were not exercised")
    if FixtureState.document_hits < 1 or FixtureState.artifact_download_hits != 1:
        raise RuntimeError("L18 document acquisition counters are inconsistent")


if __name__ == "__main__":
    main()
