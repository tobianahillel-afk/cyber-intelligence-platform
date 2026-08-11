from __future__ import annotations

import json
from datetime import UTC, date, datetime, timedelta
from hashlib import sha256
from uuid import UUID

from cip.adapters.sources.ademe_funding.schemas import AdemeFundingLine
from cip.modules.corporate_changes.domain.models import (
    ChangeClaimSnapshot,
    ChangeClaimType,
    ChangeEventType,
    ChangeSourceKind,
    OrganizationLinkStatus,
)
from cip.modules.raw_observations.domain.entities import RawObservation
from cip.modules.source_governance.domain.models import DataCategory
from cip.shared.kernel.time import require_aware_utc

SOURCE_ID = "ademe-financial-aid"
ADAPTER_ID = "ademe-data-fair-financial-aid-api"
ADAPTER_VERSION = "1.0.0"
DATASET_URL = "https://data.ademe.fr/datasets/les-aides-financieres-de-l%27ademe"


def map_ademe_funding_line(
    line: AdemeFundingLine,
    *,
    collection_job_id: UUID,
    collected_at: datetime,
    retention_until: datetime,
) -> tuple[RawObservation, ChangeClaimSnapshot]:
    collected = require_aware_utc(collected_at, field_name="collected_at")
    payload_hash = _payload_hash(line)
    event_at = _event_timestamp(line.date)
    observation = RawObservation(
        source_id=SOURCE_ID,
        adapter_id=ADAPTER_ID,
        adapter_version=ADAPTER_VERSION,
        collection_job_id=collection_job_id,
        source_record_type="public_funding_award",
        source_record_key=line.id,
        source_url=DATASET_URL,
        payload_hash_sha256=payload_hash,
        data_categories=frozenset({DataCategory.PUBLIC_RESULT_METADATA}),
        collected_at=collected,
        published_at=event_at,
        source_updated_at=event_at,
        schema_fingerprint="ademe-financial-aid-selected-fields-1",
        content_language="fr",
        classification="internal",
        retention_until=retention_until,
    )
    claim = ChangeClaimSnapshot(
        source_id=SOURCE_ID,
        source_kind=ChangeSourceKind.REGULATOR,
        source_record_key=line.id,
        article_id=line.id,
        source_url=DATASET_URL,
        event_key=f"ademe-funding:{line.id}",
        claim_type=ChangeClaimType.CONFIRMATION,
        event_type=ChangeEventType.FUNDING,
        title=f"Aide ADEME — {line.nom}",
        excerpt=_excerpt(line),
        claimed_organization_name=line.nom,
        organization_id=None,
        organization_link_status=OrganizationLinkStatus.UNRESOLVED,
        published_at=collected,
        modified_at=collected,
        event_at=event_at,
        independence_key=SOURCE_ID,
        confidence=0.92,
        historical_only=(
            event_at is None or event_at < collected - timedelta(days=180)
        ),
        metadata_only=True,
    )
    return observation, claim


def _excerpt(line: AdemeFundingLine) -> str:
    text = (
        f"Bénéficiaire: {line.nom}. Nature: {line.nature}. "
        f"Montant: {line.montant} EUR. Objet: {line.objet}. Date: {line.date}."
    )
    return text[:500]


def _event_timestamp(value: str) -> datetime | None:
    candidate = value.strip()[:10]
    try:
        parsed = date.fromisoformat(candidate)
    except ValueError:
        return None
    return datetime.combine(parsed, datetime.min.time(), UTC)


def _payload_hash(line: AdemeFundingLine) -> str:
    encoded = json.dumps(
        line.model_dump(mode="json", by_alias=True),
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    return sha256(encoded).hexdigest()
