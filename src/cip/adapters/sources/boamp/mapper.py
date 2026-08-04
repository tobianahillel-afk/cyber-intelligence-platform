from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
from uuid import NAMESPACE_URL, UUID, uuid5

from cip.adapters.sources.boamp.schemas import BoampNotice
from cip.adapters.sources.procurement_signals import matched_procurement_terms
from cip.modules.collection_orchestration.application.ports import CommercialProjection
from cip.modules.evidence.domain.entities import Evidence
from cip.modules.opportunities.domain.entities import CommercialSignal, SignalType
from cip.modules.organizations.domain.entities import Organization
from cip.modules.raw_observations.domain.entities import RawObservation
from cip.modules.source_governance.domain.models import DataCategory
from cip.shared.kernel.time import require_aware_utc

SOURCE_ID = "boamp"
ADAPTER_ID = "boamp-explore-api"
ADAPTER_VERSION = "1.0.0"


@dataclass(frozen=True, slots=True)
class BoampMapping:
    observation: RawObservation
    projection: CommercialProjection | None


def map_boamp_notice(
    notice: BoampNotice,
    *,
    collection_job_id: UUID,
    collected_at: datetime,
    retention_until: datetime,
) -> BoampMapping | None:
    collected = require_aware_utc(collected_at, field_name="collected_at")
    matched_terms = matched_procurement_terms(notice.searchable_text())
    if not matched_terms:
        return None
    published_at = _aware(notice.publication_timestamp())
    deadline = _aware(notice.deadline_timestamp())
    usable_deadline = deadline if deadline is not None and deadline > collected else None
    payload_hash = _payload_hash(notice)
    state = _normalized_state(notice.etat)
    record_type = _record_type(notice, state)
    observation = RawObservation(
        source_id=SOURCE_ID,
        adapter_id=ADAPTER_ID,
        adapter_version=ADAPTER_VERSION,
        collection_job_id=collection_job_id,
        source_record_type=record_type,
        source_record_key=notice.idweb,
        source_url=notice.notice_url(),
        payload_hash_sha256=payload_hash,
        data_categories=frozenset({DataCategory.PUBLIC_TENDER}),
        collected_at=collected,
        published_at=published_at,
        schema_fingerprint="boamp-explore-v2-selected-fields-1",
        content_language="fr",
        classification="internal",
        retention_until=retention_until,
    )
    if not _is_actionable(record_type, deadline=deadline, collected_at=collected):
        return BoampMapping(observation=observation, projection=None)
    projection = _commercial_projection(
        notice,
        matched_terms=matched_terms,
        payload_hash=payload_hash,
        published_at=published_at,
        deadline=usable_deadline,
        collected_at=collected,
        retention_until=retention_until,
    )
    return BoampMapping(observation=observation, projection=projection)


def _commercial_projection(
    notice: BoampNotice,
    *,
    matched_terms: tuple[str, ...],
    payload_hash: str,
    published_at: datetime | None,
    deadline: datetime | None,
    collected_at: datetime,
    retention_until: datetime,
) -> CommercialProjection:
    buyer = notice.nomacheteur
    organization_id = uuid5(
        NAMESPACE_URL,
        f"boamp:buyer:fr:{' '.join(buyer.casefold().split())}",
    )
    evidence_id = uuid5(NAMESPACE_URL, f"boamp:notice:{notice.idweb}")
    summary = _summary(notice, deadline=deadline)
    organization = Organization(
        id=organization_id,
        canonical_name=buyer,
        legal_name=buyer,
        country_code="FR",
        created_at=collected_at,
        updated_at=collected_at,
    )
    evidence = Evidence(
        id=evidence_id,
        source_id=SOURCE_ID,
        source_record_key=notice.idweb,
        source_url=notice.notice_url(),
        summary=summary,
        confidence=0.92,
        collected_at=collected_at,
        published_at=published_at,
        content_hash_sha256=payload_hash,
        raw_storage_permitted=False,
        retention_until=retention_until,
    )
    signal = CommercialSignal(
        id=uuid5(NAMESPACE_URL, f"boamp:signal:{notice.idweb}"),
        organization_id=organization_id,
        evidence_id=evidence_id,
        signal_type=SignalType.PUBLIC_TENDER,
        title=notice.objet,
        summary=summary,
        confidence=0.92,
        matched_terms=matched_terms,
        published_at=published_at,
        collected_at=collected_at,
        expires_at=deadline,
        created_at=collected_at,
    )
    return CommercialProjection(organization, evidence, signal)


def _record_type(notice: BoampNotice, state: str) -> str:
    searchable = notice.searchable_text().casefold()
    if state == "annulation":
        return "procurement_cancellation"
    if any(term in searchable for term in ("résultat", "resultat", "attribution")):
        return "procurement_result"
    if state == "rectificatif":
        return "procurement_rectification"
    return "procurement_notice"


def _is_actionable(
    record_type: str,
    *,
    deadline: datetime | None,
    collected_at: datetime,
) -> bool:
    if record_type in {"procurement_cancellation", "procurement_result"}:
        return False
    return deadline is None or deadline > collected_at


def _summary(notice: BoampNotice, *, deadline: datetime | None) -> str:
    state = _normalized_state(notice.etat) or "initial"
    summary = f"BOAMP {state} notice from {notice.nomacheteur}: {notice.objet}."
    if deadline is not None:
        summary += f" Response deadline: {deadline.isoformat()}."
    return summary


def _payload_hash(notice: BoampNotice) -> str:
    payload = notice.model_dump(mode="json")
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return sha256(encoded).hexdigest()


def _normalized_state(value: str | None) -> str:
    return value.strip().casefold() if value else ""


def _aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
