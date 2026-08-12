from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

from cip.adapters.sources.patentsview_patents.registry import PatentsViewPatentTarget
from cip.modules.collection_orchestration.application.patentsview_patent_adapter import (
    PatentsViewPatentAdapter,
)
from cip.modules.public_footprint.domain.models import PublicResourceKind, ResourceRetrievalState
from cip.modules.source_governance.infrastructure.registry import load_source_registry

_POLICY_PATH = Path("policies/sources.search_archives.yml")
_ORG_ID = UUID("15712d0d-9054-50b4-8a26-e25d9ea1f509")
_MAX_RESULTS = 20


def main() -> None:
    token = _required_env("PATENTSVIEW_API_KEY")
    assignee = _required_env("SA15_PATENTSVIEW_ASSIGNEE")
    canonical_name = os.environ.get("SA15_PATENTSVIEW_CANONICAL_NAME", assignee).strip()
    if not canonical_name:
        raise RuntimeError("SA15_PATENTSVIEW_CANONICAL_NAME cannot be empty")
    target = PatentsViewPatentTarget(
        target_id="sa15-controlled-patentsview-assignee",
        organization_id=_ORG_ID,
        canonical_name=canonical_name,
        assignee_organization=assignee,
        enabled=True,
    )
    entry = next(
        item
        for item in load_source_registry(_POLICY_PATH)
        if item.policy.id == "patentsview-patent-metadata"
    )
    now = datetime.now(UTC)
    batch = PatentsViewPatentAdapter(
        entry,
        (target,),
        token_provider=lambda: token,
        timeout_seconds=60,
    ).collect(
        collection_job_id=uuid4(),
        checkpoint_payload=None,
        collected_at=now,
        retention_until=now + timedelta(days=365),
    )
    _validate_batch(batch)
    print(
        "SA-15 L03 live validation passed: "
        f"assignee={assignee!r} "
        f"patentsview_observations={len(batch.observations)} "
        f"patentsview_projections={len(batch.public_footprint_projections)} claims=0 bodies=0"
    )


def _validate_batch(batch: object) -> None:
    observations = getattr(batch, "observations")
    projections = getattr(batch, "public_footprint_projections")
    if not 1 <= len(observations) <= _MAX_RESULTS or len(projections) != len(observations):
        raise RuntimeError("PatentsView live validation returned invalid result counts")
    if any(observation.source_id != "patentsview-patent-metadata" for observation in observations):
        raise RuntimeError("PatentsView live validation lost source provenance")
    if any(projection.claims for projection in projections):
        raise RuntimeError("PatentsView patent metadata unexpectedly produced claims")
    if any(
        projection.resource.kind is not PublicResourceKind.SEARCH_RESULT
        or projection.resource.retrieval_state is not ResourceRetrievalState.QUARANTINED
        for projection in projections
    ):
        raise RuntimeError("PatentsView results escaped discovery quarantine")
    if getattr(batch, "checkpoint_payload") != {"target_index": 0}:
        raise RuntimeError("PatentsView live validation checkpoint did not converge")


def _required_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"{name} is required for controlled live validation")
    return value


if __name__ == "__main__":
    main()
