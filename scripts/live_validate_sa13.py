from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

from cip.adapters.sources.ashby.registry import load_ashby_boards
from cip.adapters.sources.recruitee.registry import load_recruitee_sites
from cip.modules.collection_orchestration.application.ashby_adapter import AshbyAdapter
from cip.modules.collection_orchestration.application.recruitee_adapter import RecruiteeAdapter
from cip.modules.source_governance.infrastructure.registry import (
    SourceRegistryEntry,
    load_source_registry,
)

POLICY_PATH = Path("policies/sources.ats_expansion.yml")


def main() -> None:
    entries = {entry.policy.id: entry for entry in load_source_registry(POLICY_PATH)}
    now = datetime.now(UTC)
    retention_until = now + timedelta(days=365)
    ashby = AshbyAdapter(
        _entry(entries, "ashby-job-board"),
        load_ashby_boards(Path("policies/ashby_boards.yml")),
        timeout_seconds=30,
    )
    recruitee = RecruiteeAdapter(
        _entry(entries, "recruitee-careers-site"),
        load_recruitee_sites(Path("policies/recruitee_sites.yml")),
        timeout_seconds=30,
    )
    ashby_batch = ashby.collect(
        collection_job_id=uuid4(),
        checkpoint_payload=None,
        collected_at=now,
        retention_until=retention_until,
    )
    recruitee_batch = recruitee.collect(
        collection_job_id=uuid4(),
        checkpoint_payload=None,
        collected_at=now,
        retention_until=retention_until,
    )
    ashby_count = _checkpoint_item_count(ashby_batch.checkpoint_payload)
    recruitee_count = _checkpoint_item_count(recruitee_batch.checkpoint_payload)
    if ashby_count < 1:
        raise RuntimeError("Ashby live validation returned no public jobs")
    if recruitee_count < 1:
        raise RuntimeError("Recruitee live validation returned no public jobs")
    print(
        "SA-13 live validation passed: "
        f"ashby_jobs={ashby_count} recruitee_jobs={recruitee_count} "
        f"ashby_relevant={len(ashby_batch.commercial_projections)} "
        f"recruitee_relevant={len(recruitee_batch.commercial_projections)}"
    )


def _entry(
    entries: dict[str, SourceRegistryEntry],
    source_id: str,
) -> SourceRegistryEntry:
    try:
        return entries[source_id]
    except KeyError as exc:
        raise RuntimeError(f"missing live validation source policy: {source_id}") from exc


def _checkpoint_item_count(payload: dict[str, object] | None) -> int:
    if payload is None:
        return 0
    raw = payload.get("fingerprints")
    if not isinstance(raw, dict):
        return 0
    total = 0
    for values in raw.values():
        if isinstance(values, dict):
            total += len(values)
    return total


if __name__ == "__main__":
    main()
