from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
from uuid import NAMESPACE_URL, UUID, uuid5

from cip.adapters.sources.gleif.schemas import (
    GleifRecordResponse,
    GleifRelationshipResponse,
)
from cip.adapters.sources.organization_identity.registry import OrganizationIdentityTarget
from cip.modules.evidence.domain.entities import Evidence
from cip.modules.organizations.application.identity import IdentityProjection
from cip.modules.organizations.domain.entities import Organization
from cip.modules.organizations.domain.identifiers import IdentifierScheme, OfficialIdentifier
from cip.modules.organizations.domain.identity import (
    IdentityKind,
    IdentityRelationship,
    IdentityStatus,
    MatchState,
    OrganizationIdentity,
    RelationshipType,
)
from cip.modules.organizations.domain.matching import build_merge_candidate
from cip.modules.raw_observations.domain.entities import RawObservation
from cip.modules.source_governance.domain.models import DataCategory
from cip.shared.kernel.time import require_aware_utc

SOURCE_ID = "gleif"
ADAPTER_ID = "gleif-lei-api"
ADAPTER_VERSION = "1.0.0"
SCHEMA_FINGERPRINT = "gleif-lei-json-api-v1"


@dataclass(frozen=True, slots=True)
class GleifMappedRecord:
    observation: RawObservation
    projection: IdentityProjection
    fingerprint: str


def map_gleif_record(
    response: GleifRecordResponse,
    *,
    request_url: str,
    collection_job_id: UUID,
    collected_at: datetime,
    retention_until: datetime,
    target: OrganizationIdentityTarget | None = None,
) -> GleifMappedRecord:
    collected = require_aware_utc(collected_at, field_name="collected_at")
    attributes = response.data.attributes
    lei = OfficialIdentifier(
        scheme=IdentifierScheme.LEI,
        value=attributes.lei,
        source_id=SOURCE_ID,
        verified_at=collected,
    )
    country = _country_code(attributes.entity.jurisdiction, attributes.entity.legalAddress)
    identifiers = [lei]
    local_identifier = _local_identifier(
        attributes.entity.registeredAs,
        country=country,
        verified_at=collected,
    )
    if local_identifier is not None:
        identifiers.append(local_identifier)
    identity = OrganizationIdentity(
        id=OrganizationIdentity.deterministic_id(lei.exact_key),
        kind=IdentityKind.LEGAL_UNIT,
        official_name=attributes.entity.legalName.name,
        country_code=country,
        source_id=SOURCE_ID,
        source_record_key=f"lei:{lei.value}",
        source_url=request_url,
        confidence=0.99,
        observed_at=collected,
        status=_status(attributes.entity.status),
        identifiers=tuple(identifiers),
        aliases=tuple(name.name for name in attributes.entity.otherNames),
        legal_form=(
            attributes.entity.legalForm.label()
            if attributes.entity.legalForm is not None
            else None
        ),
        address=(
            attributes.entity.legalAddress.formatted()
            if attributes.entity.legalAddress is not None
            else None
        ),
        postal_code=(
            attributes.entity.legalAddress.postalCode
            if attributes.entity.legalAddress is not None
            else None
        ),
        city=(
            attributes.entity.legalAddress.city
            if attributes.entity.legalAddress is not None
            else None
        ),
        valid_from=attributes.entity.creationDate,
    )
    target_organization = _target_organization(target, collected) if target else None
    candidate = (
        build_merge_candidate(
            identity,
            target_organization,
            known_identifiers=target.known_identifiers(
                source_id="target-registry",
                verified_at=collected,
            ),
            target_postal_code=target.postal_code,
        )
        if target and target_organization
        else None
    )
    attached = (
        target_organization
        if candidate is not None and candidate.state is MatchState.AUTO_CONFIRMED
        else None
    )
    candidate_organizations = (
        (target_organization,) if target_organization is not None and attached is None else ()
    )
    fingerprint = _fingerprint(response)
    evidence = Evidence(
        id=uuid5(NAMESPACE_URL, f"{SOURCE_ID}:evidence:{lei.value}"),
        source_id=SOURCE_ID,
        source_record_key=identity.source_record_key,
        source_url=request_url,
        summary=(
            f"GLEIF Golden Copy record for {identity.official_name} "
            f"with LEI {lei.value}."
        ),
        confidence=0.99,
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
        source_record_type="organization_identity",
        source_record_key=identity.source_record_key,
        source_url=request_url,
        payload_hash_sha256=fingerprint,
        data_categories=frozenset({DataCategory.ORGANIZATION_METADATA}),
        collected_at=collected,
        source_updated_at=_source_updated_at(response, collected),
        schema_fingerprint=SCHEMA_FINGERPRINT,
        content_language=attributes.entity.legalName.language,
        classification="internal",
        retention_until=retention_until,
    )
    return GleifMappedRecord(
        observation=observation,
        projection=IdentityProjection(
            identity=identity,
            evidence=evidence,
            attached_organization=attached,
            candidate_organizations=candidate_organizations,
            merge_candidates=(candidate,) if candidate else (),
        ),
        fingerprint=fingerprint,
    )


def parent_lei(
    response: GleifRelationshipResponse | None,
    *,
    child_lei: str,
) -> str | None:
    if response is None or response.data is None:
        return None
    relationship = response.data.attributes.relationship
    start = relationship.startNode.nodeID.strip().upper()
    end = relationship.endNode.nodeID.strip().upper()
    child = child_lei.strip().upper()
    if start == child and end != child:
        return end
    if end == child and start != child:
        return start
    return None


def build_parent_relationship(
    child: OrganizationIdentity,
    parent: OrganizationIdentity,
    relationship_type: RelationshipType,
    *,
    request_url: str,
    observed_at: datetime,
) -> IdentityRelationship:
    key = f"{child.id}:{parent.id}:{relationship_type.value}:{SOURCE_ID}"
    return IdentityRelationship(
        id=uuid5(NAMESPACE_URL, f"organization-relationship:{key}"),
        subject_identity_id=child.id,
        object_identity_id=parent.id,
        relationship_type=relationship_type,
        source_id=SOURCE_ID,
        source_url=request_url,
        confidence=0.99,
        observed_at=observed_at,
    )


def _target_organization(
    target: OrganizationIdentityTarget,
    collected_at: datetime,
) -> Organization:
    registration_ids = tuple(
        value
        for value in (
            f"SIREN:{target.siren}" if target.siren else None,
            f"SIRET:{target.siret}" if target.siret else None,
            f"LEI:{target.lei}" if target.lei else None,
        )
        if value is not None
    )
    return Organization(
        id=target.organization_id,
        canonical_name=target.canonical_name,
        legal_name=target.canonical_name,
        country_code=target.country_code,
        registration_ids=registration_ids,
        created_at=collected_at,
        updated_at=collected_at,
    )


def _local_identifier(
    value: str | None,
    *,
    country: str,
    verified_at: datetime,
) -> OfficialIdentifier | None:
    if value is None or not value.strip():
        return None
    normalized = value.strip()
    if country == "FR" and normalized.isdigit() and len(normalized) == 9:
        try:
            return OfficialIdentifier(
                scheme=IdentifierScheme.SIREN,
                value=normalized,
                source_id=SOURCE_ID,
                verified_at=verified_at,
                issuing_country="FR",
            )
        except ValueError:
            pass
    try:
        return OfficialIdentifier(
            scheme=IdentifierScheme.FOREIGN_REGISTRATION,
            value=normalized,
            source_id=SOURCE_ID,
            verified_at=verified_at,
            issuing_country=country,
        )
    except ValueError:
        return None


def _country_code(jurisdiction: str | None, address) -> str:  # type: ignore[no-untyped-def]
    if address is not None and address.country:
        value = address.country.strip().upper()
        if len(value) == 2:
            return value
    if jurisdiction:
        value = jurisdiction.split("-", maxsplit=1)[0].strip().upper()
        if len(value) == 2:
            return value
    return "ZZ"


def _status(value: str | None) -> IdentityStatus:
    if value == "ACTIVE":
        return IdentityStatus.ACTIVE
    if value == "INACTIVE":
        return IdentityStatus.CEASED
    return IdentityStatus.UNKNOWN


def _source_updated_at(response: GleifRecordResponse, fallback: datetime) -> datetime:
    registration = response.data.attributes.registration
    if registration is None or registration.lastUpdateDate is None:
        return fallback
    return require_aware_utc(registration.lastUpdateDate, field_name="lastUpdateDate")


def _fingerprint(response: GleifRecordResponse) -> str:
    payload = response.model_dump(mode="json", exclude_none=True)
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return sha256(encoded).hexdigest()
