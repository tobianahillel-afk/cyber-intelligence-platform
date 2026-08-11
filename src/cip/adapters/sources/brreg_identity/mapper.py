from __future__ import annotations

import json
from datetime import datetime
from hashlib import sha256
from uuid import NAMESPACE_URL, UUID, uuid5

from cip.adapters.sources.brreg_identity.schemas import BrregEntity
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

SOURCE_ID = "brreg-enhetsregisteret"
ADAPTER_ID = "brreg-enhetsregisteret-entity"
ADAPTER_VERSION = "1.0.0"
SCHEMA_FINGERPRINT = "brreg-enhet-v2-selected-v1"


def map_brreg_entity(
    target: OrganizationIdentityTarget,
    entity: BrregEntity,
    *,
    request_url: str,
    collection_job_id: UUID,
    collected_at: datetime,
    retention_until: datetime,
) -> tuple[RawObservation, IdentityProjection, str]:
    collected = require_aware_utc(collected_at, field_name="collected_at")
    identifier = OfficialIdentifier(
        scheme=IdentifierScheme.FOREIGN_REGISTRATION,
        value=entity.organisasjonsnummer,
        source_id=SOURCE_ID,
        verified_at=collected,
        issuing_country="NO",
    )
    if target.country_code != "NO":
        raise ValueError("BRREG mapping requires a Norwegian target")
    if target.foreign_registration != identifier.value:
        raise ValueError("BRREG response organisation number does not match target")
    address = entity.business_address()
    identity = OrganizationIdentity(
        id=OrganizationIdentity.deterministic_id(identifier.exact_key),
        kind=IdentityKind.LEGAL_UNIT,
        official_name=entity.navn,
        country_code="NO",
        source_id=SOURCE_ID,
        source_record_key=f"legal-unit:{identifier.value}",
        source_url=request_url,
        confidence=0.99,
        observed_at=collected,
        status=IdentityStatus.CEASED if entity.slettedato else IdentityStatus.ACTIVE,
        identifiers=(identifier,),
        aliases=entity.aliases(),
        legal_form=entity.organisasjonsform.kode,
        activity_code=entity.naeringskode1.kode if entity.naeringskode1 else None,
        address=address.single_line() if address else None,
        postal_code=address.postnummer if address else None,
        city=address.poststed if address else None,
        valid_from=entity.registreringsdatoEnhetsregisteret or entity.stiftelsesdato,
        valid_until=entity.slettedato,
    )
    target_organization = Organization(
        id=target.organization_id,
        canonical_name=target.canonical_name,
        legal_name=target.canonical_name,
        country_code=target.country_code,
        created_at=collected,
        updated_at=collected,
    )
    candidate = build_merge_candidate(
        identity,
        target_organization,
        known_identifiers=target.known_identifiers(
            source_id="target-registry",
            verified_at=collected,
        ),
        target_postal_code=target.postal_code,
    )
    attached = (
        target_organization
        if candidate is not None and candidate.state is MatchState.AUTO_CONFIRMED
        else None
    )
    payload_hash = _fingerprint(entity)
    evidence = Evidence(
        id=uuid5(NAMESPACE_URL, f"{SOURCE_ID}:evidence:{identifier.value}"),
        source_id=SOURCE_ID,
        source_record_key=identity.source_record_key,
        source_url=request_url,
        summary=(
            f"Official Norwegian Central Coordinating Register entity record for "
            f"{entity.navn} with organisation number {identifier.value}."
        ),
        confidence=0.99,
        collected_at=collected,
        observed_at=collected,
        content_hash_sha256=payload_hash,
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
        payload_hash_sha256=payload_hash,
        data_categories=frozenset({DataCategory.ORGANIZATION_METADATA}),
        collected_at=collected,
        source_updated_at=collected,
        schema_fingerprint=SCHEMA_FINGERPRINT,
        content_language="no",
        classification="internal",
        retention_until=retention_until,
    )
    projection = IdentityProjection(
        identity=identity,
        evidence=evidence,
        attached_organization=attached,
        candidate_organizations=() if attached else (target_organization,),
        merge_candidates=(candidate,) if candidate is not None else (),
    )
    return observation, projection, payload_hash


def _fingerprint(entity: BrregEntity) -> str:
    payload = entity.model_dump(mode="json", exclude_none=True)
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return sha256(encoded).hexdigest()
