from __future__ import annotations

from datetime import datetime
from hashlib import sha256
from json import dumps
from uuid import UUID

from cip.adapters.sources.cisa_kev.schemas import CisaKevCatalog, CisaKevVulnerability
from cip.modules.raw_observations.domain.entities import RawObservation
from cip.modules.source_governance.domain.models import DataCategory
from cip.shared.kernel.time import require_aware_utc


def map_vulnerability(
    vulnerability: CisaKevVulnerability,
    catalog: CisaKevCatalog,
    *,
    collection_job_id: UUID,
    source_url: str,
    collected_at: datetime,
    retention_until: datetime,
) -> RawObservation:
    collected = require_aware_utc(collected_at, field_name="collected_at")
    retention = require_aware_utc(retention_until, field_name="retention_until")
    serialized = dumps(
        vulnerability.model_dump(mode="json", by_alias=True),
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    return RawObservation(
        source_id="cisa-kev",
        adapter_id="cisa-kev-feed",
        adapter_version="1",
        collection_job_id=collection_job_id,
        source_record_key=vulnerability.cve_id,
        source_record_type="known_exploited_vulnerability",
        source_url=source_url,
        payload_hash_sha256=sha256(serialized).hexdigest(),
        data_categories=frozenset(
            {
                DataCategory.VULNERABILITY_METADATA,
                DataCategory.KNOWN_EXPLOITED_STATUS,
            }
        ),
        collected_at=collected,
        source_updated_at=catalog.date_released,
        schema_fingerprint="cisa-kev-json-v1",
        content_language="en",
        classification="public",
        retention_until=retention,
    )
