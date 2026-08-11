from __future__ import annotations

import json
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from hashlib import sha256
from uuid import UUID

from cip.adapters.sources.cordis_funding.schemas import CordisOrganizationRecord
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
ADAPTER_ID = "cordis-horizon-bulk-csv"
ADAPTER_VERSION = "1.0.0"
SOURCE_URL = "https://cordis.europa.eu/data/cordis-HORIZONprojects-csv.zip"


def map_cordis_funding_record(
    record: CordisOrganizationRecord,
    *,
    collection_job_id: UUID,
    collected_at: datetime,
    retention_until: datetime,
) -> tuple[RawObservation, ChangeClaimSnapshot]:
    collected = require_aware_utc(collected_at, field_name="collected_at")
    participation_end = _date_timestamp(record.endOfParticipation)
    source_key = f"{record.projectID}:{record.organisationID}"
    source_updated = _bounded_source_time(record.contentUpdateDate, collected)
    observation = RawObservation(
        source_id=SOURCE_ID,
        adapter_id=ADAPTER_ID,
        adapter_version=ADAPTER_VERSION,
        collection_job_id=collection_job_id,
        source_record_type="eu_funded_project_participation",
        source_record_key=source_key,
        source_url=SOURCE_URL,
        payload_hash_sha256=_payload_hash(record),
        data_categories=frozenset({DataCategory.PUBLIC_RESULT_METADATA}),
        collected_at=collected,
        published_at=None,
        source_updated_at=source_updated,
        schema_fingerprint="cordis-horizon-organization-csv-2026-06",
        content_language="en",
        classification="internal",
        retention_until=retention_until,
    )
    claim = ChangeClaimSnapshot(
        source_id=SOURCE_ID,
        source_kind=ChangeSourceKind.REGULATOR,
        source_record_key=source_key,
        article_id=record.projectID,
        source_url=SOURCE_URL,
        event_key=f"cordis-project:{record.projectID}:{record.organisationID}",
        claim_type=ChangeClaimType.CONFIRMATION,
        event_type=ChangeEventType.FUNDING,
        title=f"EU-funded CORDIS project participation — {record.name}",
        excerpt=_excerpt(record),
        claimed_organization_name=record.name,
        organization_id=None,
        organization_link_status=OrganizationLinkStatus.UNRESOLVED,
        published_at=source_updated,
        modified_at=source_updated,
        event_at=None,
        independence_key=SOURCE_ID,
        confidence=0.95,
        historical_only=_historical(record, participation_end, collected),
        metadata_only=True,
    )
    return observation, claim


def _excerpt(record: CordisOrganizationRecord) -> str:
    acronym = record.projectAcronym or record.projectID
    role = record.role or "participant"
    contribution = _contribution_text(record.ecContribution)
    end = f" Participation end: {record.endOfParticipation}." if record.endOfParticipation else ""
    return (
        f"Organisation: {record.name}. Project: {acronym} ({record.projectID}). "
        f"Role: {role}.{contribution}{end}"
    )[:500]


def _contribution_text(value: str) -> str:
    if not value:
        return ""
    try:
        amount = Decimal(value)
    except InvalidOperation:
        return ""
    if amount < 0:
        return ""
    return f" CORDIS organisation ecContribution field: {format(amount, 'f')}."


def _bounded_source_time(value: str, collected: datetime) -> datetime:
    parsed = _date_timestamp(value)
    if parsed is None or parsed > collected:
        return collected
    return parsed


def _date_timestamp(value: str) -> datetime | None:
    if not value:
        return None
    candidate = value.strip()[:10]
    try:
        parsed = date.fromisoformat(candidate)
    except ValueError:
        return None
    return datetime.combine(parsed, datetime.min.time(), UTC)


def _historical(
    record: CordisOrganizationRecord,
    participation_end: datetime | None,
    collected: datetime,
) -> bool:
    inactive = record.active.casefold() in {"false", "0", "no"}
    expired = participation_end is not None and participation_end < collected - timedelta(days=365)
    return inactive or expired


def _payload_hash(record: CordisOrganizationRecord) -> str:
    semantic_fields = {
        "active": record.active,
        "ecContribution": record.ecContribution,
        "endOfParticipation": record.endOfParticipation,
        "name": record.name,
        "organisationID": record.organisationID,
        "projectAcronym": record.projectAcronym,
        "projectID": record.projectID,
        "role": record.role,
    }
    encoded = json.dumps(semantic_fields, sort_keys=True, separators=(",", ":")).encode()
    return sha256(encoded).hexdigest()
