from __future__ import annotations

import json
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from hashlib import sha256
from uuid import UUID

from cip.adapters.sources.cordis_funding.schemas import CordisFundingBinding
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

SOURCE_ID = "cordis-eu-funded-projects"
ADAPTER_ID = "cordis-eurio-sparql-funding"
ADAPTER_VERSION = "1.0.0"
SOURCE_URL = "https://cordis.europa.eu/projects"


def map_cordis_funding_binding(
    binding: CordisFundingBinding,
    *,
    collection_job_id: UUID,
    collected_at: datetime,
    retention_until: datetime,
) -> tuple[RawObservation, ChangeClaimSnapshot]:
    collected = require_aware_utc(collected_at, field_name="collected_at")
    event_at = _event_timestamp(binding.start_date.value if binding.start_date else None)
    source_key = _source_key(binding)
    observation = RawObservation(
        source_id=SOURCE_ID,
        adapter_id=ADAPTER_ID,
        adapter_version=ADAPTER_VERSION,
        collection_job_id=collection_job_id,
        source_record_type="eu_funded_project_participation",
        source_record_key=source_key,
        source_url=SOURCE_URL,
        payload_hash_sha256=_payload_hash(binding),
        data_categories=frozenset({DataCategory.PUBLIC_RESULT_METADATA}),
        collected_at=collected,
        published_at=event_at,
        source_updated_at=event_at,
        schema_fingerprint="cordis-eurio-funding-binding-1",
        content_language="en",
        classification="internal",
        retention_until=retention_until,
    )
    claim = ChangeClaimSnapshot(
        source_id=SOURCE_ID,
        source_kind=ChangeSourceKind.REGULATOR,
        source_record_key=source_key,
        article_id=binding.project_id.value,
        source_url=SOURCE_URL,
        event_key=f"cordis-project:{binding.project_id.value}:{_name_key(binding)}",
        claim_type=ChangeClaimType.CONFIRMATION,
        event_type=ChangeEventType.FUNDING,
        title=f"EU-funded CORDIS project participation — {binding.organisation_name.value}",
        excerpt=_excerpt(binding),
        claimed_organization_name=binding.organisation_name.value,
        organization_id=None,
        organization_link_status=OrganizationLinkStatus.UNRESOLVED,
        published_at=collected,
        modified_at=collected,
        event_at=event_at,
        independence_key=SOURCE_ID,
        confidence=0.95,
        historical_only=(event_at is None or event_at < collected - timedelta(days=365)),
        metadata_only=True,
    )
    return observation, claim


def _source_key(binding: CordisFundingBinding) -> str:
    return f"{binding.project_id.value}:{_name_key(binding)}"


def _name_key(binding: CordisFundingBinding) -> str:
    return sha256(binding.organisation_name.value.casefold().encode()).hexdigest()[:16]


def _excerpt(binding: CordisFundingBinding) -> str:
    role = binding.role_label.value if binding.role_label else "participant"
    contribution = _contribution_text(binding)
    dates = _date_text(binding)
    text = (
        f"Organisation: {binding.organisation_name.value}. "
        f"Project: {binding.project_title.value} ({binding.project_id.value}). "
        f"Role: {role}.{contribution}{dates}"
    )
    return text[:500]


def _contribution_text(binding: CordisFundingBinding) -> str:
    if binding.eu_contribution is None:
        return ""
    try:
        amount = Decimal(binding.eu_contribution.value)
    except InvalidOperation:
        return ""
    if amount < 0:
        return ""
    return f" Project-level maximum EU contribution: {amount} EUR."


def _date_text(binding: CordisFundingBinding) -> str:
    start = binding.start_date.value if binding.start_date else None
    end = binding.end_date.value if binding.end_date else None
    if not start and not end:
        return ""
    return f" Project dates: {start or 'unknown'} to {end or 'unknown'}."


def _event_timestamp(value: str | None) -> datetime | None:
    if value is None:
        return None
    candidate = value.strip()[:10]
    try:
        parsed = date.fromisoformat(candidate)
    except ValueError:
        return None
    return datetime.combine(parsed, datetime.min.time(), UTC)


def _payload_hash(binding: CordisFundingBinding) -> str:
    encoded = json.dumps(
        binding.model_dump(mode="json"),
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    return sha256(encoded).hexdigest()
