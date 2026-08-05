from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from hashlib import sha256
from uuid import UUID

from cip.modules.collection_orchestration.application.ports import AdapterCollectionBatch
from cip.modules.raw_observations.domain.entities import RawObservation
from cip.modules.source_governance.domain.models import DataCategory


class ReferencePortfolioAdapter:
    """Deterministic no-network adapter used to validate the common lifecycle."""

    source_id = "reference-synthetic"
    adapter_id = "reference-synthetic-adapter"
    data_category = DataCategory.PUBLIC_RESULT_METADATA

    def collect(
        self,
        *,
        collection_job_id: UUID,
        checkpoint_payload: Mapping[str, object] | None,
        collected_at: datetime,
        retention_until: datetime,
    ) -> AdapterCollectionBatch:
        sequence = _sequence(checkpoint_payload) + 1
        material = f"reference-synthetic:{sequence}"
        digest = sha256(material.encode("utf-8")).hexdigest()
        observation = RawObservation(
            source_id=self.source_id,
            adapter_id=self.adapter_id,
            adapter_version="1",
            collection_job_id=collection_job_id,
            source_record_type="synthetic_reference_record",
            source_record_key=str(sequence),
            source_url=f"https://example.invalid/source-portfolio-reference/{sequence}",
            payload_hash_sha256=digest,
            schema_fingerprint="synthetic-v1",
            data_categories=frozenset({self.data_category}),
            collected_at=collected_at,
            observed_at=collected_at,
            source_updated_at=collected_at,
            retention_until=retention_until,
        )
        return AdapterCollectionBatch(
            observations=(observation,),
            checkpoint_payload={"sequence": sequence},
            not_modified=False,
        )


def _sequence(payload: Mapping[str, object] | None) -> int:
    if payload is None:
        return 0
    value = payload.get("sequence", 0)
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError("reference adapter sequence must be a non-negative integer")
    return value
