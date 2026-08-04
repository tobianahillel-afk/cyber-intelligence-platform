from __future__ import annotations

import json
from datetime import UTC, datetime
from hashlib import sha256
from uuid import NAMESPACE_URL, UUID, uuid5

from cip.adapters.sources.procurement_signals import matched_procurement_terms
from cip.adapters.sources.ted_search.schemas import TedNotice
from cip.modules.collection_orchestration.application.ports import CommercialProjection
from cip.modules.evidence.domain.entities import Evidence
from cip.modules.opportunities.domain.entities import CommercialSignal, SignalType
from cip.modules.organizations.domain.entities import Organization
from cip.modules.raw_observations.domain.entities import RawObservation
from cip.modules.source_governance.domain.models import DataCategory
from cip.shared.kernel.time import require_aware_utc

ADAPTER_ID = "ted-search-api"
ADAPTER_VERSION = "1.0.0"
SOURCE_ID = "ted-search"
COUNTRY_CODES = {
    "AUT": "AT",
    "BEL": "BE",
    "BGR": "BG",
    "CHE": "CH",
    "CYP": "CY",
    "CZE": "CZ",
    "DEU": "DE",
    "DNK": "DK",
    "ESP": "ES",
    "EST": "EE",
    "FIN": "FI",
    "FRA": "FR",
    "GRC": "GR",
    "HRV": "HR",
    "HUN": "HU",
    "IRL": "IE",
    "ISL": "IS",
    "ITA": "IT",
    "LTU": "LT",
    "LUX": "LU",
    "LVA": "LV",
    "MLT": "MT",
    "NLD": "NL",
    "NOR": "NO",
    "POL": "PL",
    "PRT": "PT",
    "ROU": "RO",
    "SVK": "SK",
    "SVN": "SI",
    "SWE": "SE",
}


def map_ted_notice(
    notice: TedNotice,
    *,
    collection_job_id: UUID,
    collected_at: datetime,
    retention_until: datetime,
) -> tuple[RawObservation, CommercialProjection] | None:
    collected = require_aware_utc(collected_at, field_name="collected_at")
    title = notice.title()
    matched_terms = matched_procurement_terms(title)
    if not matched_terms:
        return None
    buyer = notice.buyer()
    country = COUNTRY_CODES.get(notice.country() or "")
    notice_url = f"https://ted.europa.eu/en/notice/{notice.publication_number}/html"
    payload_hash = _payload_hash(notice)
    published_at = _aware(notice.publication_timestamp())
    deadline = _aware(notice.deadline_timestamp())
    usable_deadline = deadline if deadline is not None and deadline > collected else None
    organization_id = uuid5(
        NAMESPACE_URL,
        f"ted:buyer:{country or 'unknown'}:{' '.join(buyer.casefold().split())}",
    )
    evidence_id = uuid5(NAMESPACE_URL, f"ted:notice:{notice.publication_number}")
    summary = _summary(title, buyer, usable_deadline)
    organization = Organization(
        id=organization_id,
        canonical_name=buyer,
        legal_name=buyer,
        country_code=country,
        created_at=collected,
        updated_at=collected,
    )
    evidence = Evidence(
        id=evidence_id,
        source_id=SOURCE_ID,
        source_record_key=notice.publication_number,
        source_url=notice_url,
        summary=summary,
        confidence=0.9,
        collected_at=collected,
        published_at=published_at,
        content_hash_sha256=payload_hash,
        raw_storage_permitted=False,
        retention_until=retention_until,
    )
    signal = CommercialSignal(
        id=uuid5(NAMESPACE_URL, f"ted:signal:{notice.publication_number}"),
        organization_id=organization_id,
        evidence_id=evidence_id,
        signal_type=SignalType.PUBLIC_TENDER,
        title=title,
        summary=summary,
        confidence=0.9,
        matched_terms=matched_terms,
        published_at=published_at,
        collected_at=collected,
        expires_at=usable_deadline,
        created_at=collected,
    )
    observation = RawObservation(
        source_id=SOURCE_ID,
        adapter_id=ADAPTER_ID,
        adapter_version=ADAPTER_VERSION,
        collection_job_id=collection_job_id,
        source_record_type="procurement_notice",
        source_record_key=notice.publication_number,
        source_url=notice_url,
        payload_hash_sha256=payload_hash,
        data_categories=frozenset({DataCategory.PUBLIC_TENDER}),
        collected_at=collected,
        published_at=published_at,
        schema_fingerprint="ted-search-v3-selected-fields-1",
        classification="internal",
        retention_until=retention_until,
    )
    return observation, CommercialProjection(organization, evidence, signal)


def _payload_hash(notice: TedNotice) -> str:
    payload = notice.model_dump(mode="json", by_alias=True)
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return sha256(encoded).hexdigest()


def _summary(title: str, buyer: str, deadline: datetime | None) -> str:
    result = f"TED public procurement notice from {buyer}: {title}."
    if deadline is not None:
        result += f" Response deadline: {deadline.isoformat()}."
    return result


def _aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
