from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

from cip.modules.collection_orchestration.application.ademe_funding_adapter import (
    AdemeFundingAdapter,
)
from cip.modules.collection_orchestration.application.cordis_funding_adapter import (
    CordisFundingAdapter,
)
from cip.modules.collection_orchestration.application.place_awards_adapter import (
    PlaceAwardsAdapter,
)
from cip.modules.source_governance.infrastructure.registry import (
    SourceRegistryEntry,
    load_source_registry,
)

POLICY_PATH = Path("policies/sources.procurement_funding.yml")


def main() -> None:
    entries = {entry.policy.id: entry for entry in load_source_registry(POLICY_PATH)}
    now = datetime.now(UTC)
    retention_until = now + timedelta(days=3650)
    place = PlaceAwardsAdapter(_entry(entries, "place-awards"), timeout_seconds=30)
    ademe = AdemeFundingAdapter(
        _entry(entries, "ademe-financial-aid"), timeout_seconds=30
    )
    cordis = CordisFundingAdapter(
        _entry(entries, "cordis-eu-funded-projects"), timeout_seconds=30
    )

    place_batch = place.collect(
        collection_job_id=uuid4(),
        checkpoint_payload=None,
        collected_at=now,
        retention_until=retention_until,
    )
    ademe_batch = ademe.collect(
        collection_job_id=uuid4(),
        checkpoint_payload=None,
        collected_at=now,
        retention_until=retention_until,
    )
    cordis_batch = cordis.collect(
        collection_job_id=uuid4(),
        checkpoint_payload=None,
        collected_at=now,
        retention_until=retention_until,
    )

    place_count = len(place_batch.observations)
    ademe_count = len(ademe_batch.observations)
    cordis_count = len(cordis_batch.observations)
    if place_count < 1 or len(place_batch.procurement_projections) != place_count:
        raise RuntimeError("PLACE live validation did not preserve award projections")
    if ademe_count < 1 or len(ademe_batch.corporate_change_claims) != ademe_count:
        raise RuntimeError("ADEME live validation did not preserve funding claims")
    if cordis_count < 1 or len(cordis_batch.corporate_change_claims) != cordis_count:
        raise RuntimeError("CORDIS live validation did not preserve funding claims")

    print(
        "SA-12 live validation passed: "
        f"place_awards={place_count} "
        f"place_procurement={len(place_batch.procurement_projections)} "
        f"ademe_aids={ademe_count} "
        f"ademe_funding_claims={len(ademe_batch.corporate_change_claims)} "
        f"cordis_participations={cordis_count} "
        f"cordis_funding_claims={len(cordis_batch.corporate_change_claims)}"
    )


def _entry(
    entries: dict[str, SourceRegistryEntry], source_id: str
) -> SourceRegistryEntry:
    try:
        return entries[source_id]
    except KeyError as exc:
        raise RuntimeError(f"missing live validation source policy: {source_id}") from exc


if __name__ == "__main__":
    main()
