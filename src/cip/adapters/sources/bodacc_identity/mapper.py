from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
from uuid import NAMESPACE_URL, UUID, uuid5

from cip.adapters.sources.bodacc_identity.schemas import BodaccIdentityAnnouncement
from cip.adapters.sources.organization_identity.registry import OrganizationIdentityTarget
from cip.modules.evidence.domain.entities import Evidence
from cip.modules.organizations.application.identity import IdentityProjection
from cip.modules.organizations.domain.entities import Organization
from cip.modules.organizations.domain.identifiers import IdentifierScheme, OfficialIdentifier
from cip.modules.organizations.domain.identity import (
    IdentityKind,
    IdentityStatus,
    MatchState,
    OrganizationIdentity,
)
from cip.modules.organizations.domain.matching import build_merge_candidate
from cip.modules.raw_observations.domain.entities import RawObservation
from cip.modules.source_governance.domain.models import DataCategory
from cip.shared.kernel.time import require_aware_utc

SOURCE_ID = "bodacc-identity"
ADAPTER_ID = "bodacc-commercial-announcements"
ADAPTER_VERSION = "1.0.0"
SCHEMA_FINGERPRINT = "bodacc-identity-selected-fields-v1"


@dataclass(frozen=True, slots=True)
class BodaccMappedIdentity:
    observation: RawObservation
    projection: IdentityProjection
    fingerprint: str


def map_bodacc_identity(
    target: OrganizationIdentityTarget,
    announcements: tuple[BodaccIdentityAnnouncement, ...],
    *,
    request_url: str,
    collection_job_id: UUID,
    collected_at: datetime,
    retention_until: datetime,
) -> BodaccMappedIdentity:
    collected = require_aware_utc(collected_at, field_name="collected_at")
    if target.siren is None:
        raise ValueError("BODACC identity mapping requires target SIREN")
    relevant = tuple(
        announcement
        for announcement in announcements
        if target.siren in announcement.registration_text().replace(" ", "")
    )
    if announcements and not relevant:
        raise ValueError("BODACC records do not reference the requested SIREN")
    ordered = tuple(sorted(relevant, key=lambda item: (item.dateparution, item.id), reverse=True))
    latest = ordered[0] if ordered else None
    identifier = OfficialIdentifier(
        scheme=IdentifierScheme.SIREN,
        value=target.siren,
        source_id=SOURCE_ID,
        verified_at=collected,
        issuing_country="FR",
    )
    identity = OrganizationIdentity(
        id=OrganizationIdentity.deterministic_id(identifier.exact_key),
        kind=IdentityKind.LEGAL_UNIT,
        official_name=_official_name(latest, target.canonical_name),
        country_code="FR",
        source_id=SOURCE_ID,
        source_record_key=f"legal-unit:{identifier.value}",
        source_url=request_url,
        confidence=0.9 if latest else 0.7,
        observed_at=collected,
        status=_status(latest),
        identifiers=(identifier,),
        aliases=_aliases(ordered, target.canonical_name),
        postal_code=latest.cp if latest else target.postal_code,
        city=latest.ville if latest else None,
        valid_until=(
            latest.dateparution
            if latest and _status(latest) is IdentityStatus.STRUCK_OFF
            else None
        ),
    )
    organization = _target_organization(target, collected)
    candidate = build_merge_candidate(
        identity,
        organization,
        known_identifiers=target.known_identifiers(
            source_id="target-registry",
            verified_at=collected,
        ),
        target_postal_code=target.postal_code,
    )
    if candidate is None or candidate.state is not MatchState.AUTO_CONFIRMED:
        raise ValueError("BODACC target must match by exact SIREN")
    fingerprint = _fingerprint(ordered)
    summary = (
        f"BODACC commercial-announcement history for SIREN {identifier.value}; "
        f"latest family={latest.status_family() or 'unknown'} on {latest.dateparution}."
        if latest
        else f"No BODACC commercial announcement found for SIREN {identifier.value}."
    )
    evidence = Evidence(
        id=uuid5(NAMESPACE_URL, f"{SOURCE_ID}:evidence:{identifier.value}"),
        source_id=SOURCE_ID,
        source_record_key=identity.source_record_key,
        source_url=request_url,
        summary=summary,
        confidence=identity.confidence,
        collected_at=collected,
        observed_at=collected,
        content_hash_sha256=fingerprint,
        raw_storage_permitted=False,
        retention_until=retention_until,
    )
    observation = RawObservation(
        source_id=SOURCE_ID,
        adapter_id=ADAPTER_ID,
        adapter_version=ADAPTER_VERSION,
        collection_job_id=collection_job_id,
        source_record_type="organization_identity_event_history",
        source_record_key=identity.source_record_key,
        source_url=request_url,
        payload_hash_sha256=fingerprint,
        data_categories=frozenset({DataCategory.ORGANIZATION_METADATA}),
        collected_at=collected,
        source_updated_at=(
            datetime.combine(latest.dateparution, datetime.min.time(), tzinfo=collected.tzinfo)
            if latest
            else collected
        ),
        schema_fingerprint=SCHEMA_FINGERPRINT,
        content_language="fr",
        classification="internal",
        retention_until=retention_until,
    )
    return BodaccMappedIdentity(
        observation=observation,
        projection=IdentityProjection(
            identity=identity,
            evidence=evidence,
            attached_organization=organization,
            merge_candidates=(candidate,),
        ),
        fingerprint=fingerprint,
    )


def _target_organization(
    target: OrganizationIdentityTarget,
    collected_at: datetime,
) -> Organization:
    assert target.siren is not None
    return Organization(
        id=target.organization_id,
        canonical_name=target.canonical_name,
        legal_name=target.canonical_name,
        country_code=target.country_code,
        registration_ids=(f"SIREN:{target.siren}",),
        created_at=collected_at,
        updated_at=collected_at,
    )


def _official_name(
    latest: BodaccIdentityAnnouncement | None,
    fallback: str,
) -> str:
    if latest and latest.commercant and latest.commercant.strip():
        return latest.commercant.strip()
    return fallback


def _aliases(
    announcements: tuple[BodaccIdentityAnnouncement, ...],
    fallback: str,
) -> tuple[str, ...]:
    values = [fallback]
    values.extend(
        item.commercant.strip()
        for item in announcements
        if item.commercant and item.commercant.strip()
    )
    return tuple(dict.fromkeys(values))


def _status(
    latest: BodaccIdentityAnnouncement | None,
) -> IdentityStatus:
    if latest is None:
        return IdentityStatus.UNKNOWN
    family = latest.status_family()
    if "radiation" in family:
        return IdentityStatus.STRUCK_OFF
    if "creation" in family or "immatriculation" in family:
        return IdentityStatus.ACTIVE
    if "dissolution" in family:
        return IdentityStatus.DISSOLVED
    return IdentityStatus.UNKNOWN


def _fingerprint(announcements: tuple[BodaccIdentityAnnouncement, ...]) -> str:
    payload = [item.model_dump(mode="json", exclude_none=True) for item in announcements]
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return sha256(encoded).hexdigest()
