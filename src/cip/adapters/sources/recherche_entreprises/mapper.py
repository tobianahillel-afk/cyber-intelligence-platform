from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
from uuid import NAMESPACE_URL, UUID, uuid5

from cip.adapters.sources.organization_identity.registry import OrganizationIdentityTarget
from cip.adapters.sources.recherche_entreprises.schemas import (
    RechercheEntrepriseResult,
    RechercheEtablissement,
)
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

SOURCE_ID = "recherche-entreprises"
ADAPTER_ID = "recherche-entreprises-search"
ADAPTER_VERSION = "1.0.0"
SCHEMA_FINGERPRINT = "recherche-entreprises-minimal-v1"


@dataclass(frozen=True, slots=True)
class RechercheMappedResult:
    observations: tuple[RawObservation, ...]
    projections: tuple[IdentityProjection, ...]
    fingerprint: str


def map_recherche_entreprise(
    target: OrganizationIdentityTarget,
    result: RechercheEntrepriseResult,
    *,
    request_url: str,
    collection_job_id: UUID,
    collected_at: datetime,
    retention_until: datetime,
) -> RechercheMappedResult | None:
    collected = require_aware_utc(collected_at, field_name="collected_at")
    if result.statut_diffusion not in {None, "O"}:
        return None
    legal_identifier = OfficialIdentifier(
        scheme=IdentifierScheme.SIREN,
        value=result.siren,
        source_id=SOURCE_ID,
        verified_at=collected,
        issuing_country="FR",
    )
    legal_identity = OrganizationIdentity(
        id=OrganizationIdentity.deterministic_id(legal_identifier.exact_key),
        kind=IdentityKind.LEGAL_UNIT,
        official_name=result.official_name(),
        country_code="FR",
        source_id=SOURCE_ID,
        source_record_key=f"legal-unit:{legal_identifier.value}",
        source_url=request_url,
        confidence=0.98,
        observed_at=collected,
        status=_legal_status(result.etat_administratif, result.date_fermeture),
        identifiers=(legal_identifier,),
        aliases=result.public_aliases(),
        legal_form=result.nature_juridique,
        activity_code=result.activite_principale,
        valid_from=result.date_creation,
        valid_until=result.date_fermeture,
    )
    target_organization = _target_organization(target, collected)
    candidate = build_merge_candidate(
        legal_identity,
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
    candidate_organizations = () if attached else (target_organization,)
    candidates = (candidate,) if candidate is not None else ()
    legal_evidence = _evidence(
        key=f"legal-unit:{legal_identifier.value}",
        url=request_url,
        summary=(
            f"Official French company-search record for {legal_identity.official_name} "
            f"with SIREN {legal_identifier.value}."
        ),
        collected_at=collected,
        retention_until=retention_until,
        payload_hash=_fingerprint(result),
    )
    observations = [
        _observation(
            key=legal_identity.source_record_key,
            url=request_url,
            payload_hash=legal_evidence.content_hash_sha256 or _fingerprint(result),
            collection_job_id=collection_job_id,
            collected_at=collected,
            retention_until=retention_until,
        )
    ]
    projections = [
        IdentityProjection(
            identity=legal_identity,
            evidence=legal_evidence,
            attached_organization=attached,
            candidate_organizations=candidate_organizations,
            merge_candidates=candidates,
        )
    ]
    establishments = _unique_establishments(result)
    for establishment in establishments:
        mapped = _map_establishment(
            establishment,
            legal_identity=legal_identity,
            attached_organization=attached,
            request_url=request_url,
            collection_job_id=collection_job_id,
            collected_at=collected,
            retention_until=retention_until,
        )
        if mapped is None:
            continue
        observation, projection = mapped
        observations.append(observation)
        projections.append(projection)
    return RechercheMappedResult(
        observations=tuple(observations),
        projections=tuple(projections),
        fingerprint=_fingerprint(result),
    )


def _map_establishment(
    establishment: RechercheEtablissement,
    *,
    legal_identity: OrganizationIdentity,
    attached_organization: Organization | None,
    request_url: str,
    collection_job_id: UUID,
    collected_at: datetime,
    retention_until: datetime,
) -> tuple[RawObservation, IdentityProjection] | None:
    if establishment.statut_diffusion_etablissement not in {None, "O"}:
        return None
    identifier = OfficialIdentifier(
        scheme=IdentifierScheme.SIRET,
        value=establishment.siret,
        source_id=SOURCE_ID,
        verified_at=collected_at,
        issuing_country="FR",
    )
    identity = OrganizationIdentity(
        id=OrganizationIdentity.deterministic_id(identifier.exact_key),
        organization_id=attached_organization.id if attached_organization else None,
        kind=IdentityKind.ESTABLISHMENT,
        official_name=_establishment_name(establishment, legal_identity.official_name),
        country_code="FR",
        source_id=SOURCE_ID,
        source_record_key=f"establishment:{identifier.value}",
        source_url=request_url,
        confidence=0.98,
        observed_at=collected_at,
        status=_establishment_status(
            establishment.etat_administratif,
            establishment.date_fermeture,
        ),
        identifiers=(identifier,),
        aliases=_establishment_aliases(establishment),
        activity_code=establishment.activite_principale,
        address=establishment.adresse,
        postal_code=establishment.code_postal,
        city=establishment.libelle_commune,
        is_headquarters=establishment.est_siege,
        valid_from=establishment.date_creation,
        valid_until=establishment.date_fermeture,
    )
    payload_hash = _fingerprint(establishment)
    evidence = _evidence(
        key=f"establishment:{identifier.value}",
        url=request_url,
        summary=(
            f"Official French establishment record for SIRET {identifier.value}; "
            f"headquarters={establishment.est_siege}."
        ),
        collected_at=collected_at,
        retention_until=retention_until,
        payload_hash=payload_hash,
    )
    relationships = [
        _relationship(
            identity.id,
            legal_identity.id,
            RelationshipType.ESTABLISHMENT_OF,
            request_url=request_url,
            observed_at=collected_at,
        )
    ]
    if establishment.est_siege:
        relationships.append(
            _relationship(
                identity.id,
                legal_identity.id,
                RelationshipType.HEADQUARTERS_OF,
                request_url=request_url,
                observed_at=collected_at,
            )
        )
    return (
        _observation(
            key=identity.source_record_key,
            url=request_url,
            payload_hash=payload_hash,
            collection_job_id=collection_job_id,
            collected_at=collected_at,
            retention_until=retention_until,
        ),
        IdentityProjection(
            identity=identity,
            evidence=evidence,
            attached_organization=attached_organization,
            relationships=tuple(relationships),
        ),
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


def _evidence(
    *,
    key: str,
    url: str,
    summary: str,
    collected_at: datetime,
    retention_until: datetime,
    payload_hash: str,
) -> Evidence:
    return Evidence(
        id=uuid5(NAMESPACE_URL, f"{SOURCE_ID}:evidence:{key}"),
        source_id=SOURCE_ID,
        source_record_key=key,
        source_url=url,
        summary=summary,
        confidence=0.98,
        collected_at=collected_at,
        observed_at=collected_at,
        content_hash_sha256=payload_hash,
        raw_storage_permitted=False,
        retention_until=retention_until,
    )


def _observation(
    *,
    key: str,
    url: str,
    payload_hash: str,
    collection_job_id: UUID,
    collected_at: datetime,
    retention_until: datetime,
) -> RawObservation:
    return RawObservation(
        source_id=SOURCE_ID,
        adapter_id=ADAPTER_ID,
        adapter_version=ADAPTER_VERSION,
        collection_job_id=collection_job_id,
        source_record_type="organization_identity",
        source_record_key=key,
        source_url=url,
        payload_hash_sha256=payload_hash,
        data_categories=frozenset({DataCategory.ORGANIZATION_METADATA}),
        collected_at=collected_at,
        source_updated_at=collected_at,
        schema_fingerprint=SCHEMA_FINGERPRINT,
        content_language="fr",
        classification="internal",
        retention_until=retention_until,
    )


def _relationship(
    subject_id: UUID,
    object_id: UUID,
    relationship_type: RelationshipType,
    *,
    request_url: str,
    observed_at: datetime,
) -> IdentityRelationship:
    key = f"{subject_id}:{object_id}:{relationship_type.value}:{SOURCE_ID}"
    return IdentityRelationship(
        id=uuid5(NAMESPACE_URL, f"organization-relationship:{key}"),
        subject_identity_id=subject_id,
        object_identity_id=object_id,
        relationship_type=relationship_type,
        source_id=SOURCE_ID,
        source_url=request_url,
        confidence=0.99,
        observed_at=observed_at,
    )


def _unique_establishments(
    result: RechercheEntrepriseResult,
) -> tuple[RechercheEtablissement, ...]:
    values = [*(result.matching_etablissements or [])]
    if result.siege is not None:
        values.append(result.siege)
    unique: dict[str, RechercheEtablissement] = {}
    for value in values:
        unique[value.siret] = value
    return tuple(unique.values())


def _legal_status(value: str | None, closed_at) -> IdentityStatus:  # type: ignore[no-untyped-def]
    if closed_at is not None:
        return IdentityStatus.CEASED
    return IdentityStatus.ACTIVE if value == "A" else IdentityStatus.UNKNOWN


def _establishment_status(
    value: str | None,
    closed_at,  # type: ignore[no-untyped-def]
) -> IdentityStatus:
    if closed_at is not None:
        return IdentityStatus.CLOSED
    return IdentityStatus.ACTIVE if value == "A" else IdentityStatus.UNKNOWN


def _establishment_name(
    establishment: RechercheEtablissement,
    fallback: str,
) -> str:
    return (
        establishment.nom_commercial
        or next(iter(establishment.liste_enseignes), None)
        or fallback
    )


def _establishment_aliases(
    establishment: RechercheEtablissement,
) -> tuple[str, ...]:
    values = [*establishment.liste_enseignes]
    if establishment.nom_commercial:
        values.append(establishment.nom_commercial)
    return tuple(values)


def _fingerprint(value: RechercheEntrepriseResult | RechercheEtablissement) -> str:
    payload = value.model_dump(mode="json", exclude_none=True)
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return sha256(encoded).hexdigest()
