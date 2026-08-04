from __future__ import annotations

from collections.abc import Sequence
from datetime import date, datetime
from uuid import NAMESPACE_URL, UUID, uuid5

from sqlalchemy import select
from sqlalchemy.orm import Session

from cip.modules.organizations.application.identity import IdentityProjection
from cip.modules.organizations.infrastructure.identity_models import (
    OrganizationIdentityClaimRecord,
    OrganizationIdentityRecord,
)

_SOURCE_PRIORITY = {
    "sirene-api": 100,
    "recherche-entreprises": 95,
    "inpi-rne": 95,
    "gleif": 90,
    "bodacc-identity": 80,
}
_CONFLICT_FIELDS = (
    "official_name",
    "status",
    "legal_form",
    "activity_code",
    "address",
    "postal_code",
    "city",
)


def persist_identity_claims(
    session: Session,
    projections: Sequence[IdentityProjection],
) -> None:
    if not projections:
        return
    identity_ids: set[UUID] = set()
    for projection in projections:
        upsert_identity_claim(session, projection)
        identity_ids.add(projection.identity.id)
    session.flush()
    reconcile_identity_claims(session, identity_ids)


def upsert_identity_claim(session: Session, projection: IdentityProjection) -> None:
    identity = projection.identity
    claim_id = uuid5(
        NAMESPACE_URL,
        f"organization-identity-claim:{identity.source_id}:{identity.source_record_key}",
    )
    record = session.get(OrganizationIdentityClaimRecord, claim_id)
    selected_fields = _selected_fields(projection)
    if record is None:
        session.add(
            OrganizationIdentityClaimRecord(
                id=claim_id,
                identity_id=identity.id,
                source_id=identity.source_id,
                source_record_key=identity.source_record_key,
                source_url=identity.source_url,
                selected_fields=selected_fields,
                confidence=identity.confidence,
                observed_at=identity.observed_at,
                content_hash_sha256=projection.evidence.content_hash_sha256,
                conflict_fields=[],
            )
        )
        return
    if record.identity_id != identity.id:
        raise RuntimeError("identity claim source record is linked to another identity")
    record.source_url = identity.source_url
    record.selected_fields = selected_fields
    record.confidence = identity.confidence
    record.observed_at = identity.observed_at
    record.content_hash_sha256 = projection.evidence.content_hash_sha256


def reconcile_identity_claims(session: Session, identity_ids: set[UUID]) -> None:
    for identity_id in identity_ids:
        claims = session.scalars(
            select(OrganizationIdentityClaimRecord).where(
                OrganizationIdentityClaimRecord.identity_id == identity_id
            )
        ).all()
        if not claims:
            continue
        conflicts = _conflict_fields(claims)
        for claim in claims:
            claim.conflict_fields = list(conflicts)
        identity = session.get(OrganizationIdentityRecord, identity_id)
        if identity is None:
            raise RuntimeError("identity claim references a missing identity")
        best = max(claims, key=_claim_rank)
        _apply_selected_fields(identity, best.selected_fields)


def _selected_fields(projection: IdentityProjection) -> dict[str, object]:
    identity = projection.identity
    return {
        "kind": identity.kind.value,
        "official_name": identity.official_name,
        "country_code": identity.country_code,
        "status": identity.status.value,
        "legal_form": identity.legal_form,
        "activity_code": identity.activity_code,
        "address": identity.address,
        "postal_code": identity.postal_code,
        "city": identity.city,
        "is_headquarters": identity.is_headquarters,
        "valid_from": _date_value(identity.valid_from),
        "valid_until": _date_value(identity.valid_until),
        "identifiers": sorted(identifier.exact_key for identifier in identity.identifiers),
        "aliases": sorted(identity.aliases, key=str.casefold),
    }


def _conflict_fields(
    claims: Sequence[OrganizationIdentityClaimRecord],
) -> tuple[str, ...]:
    conflicts: list[str] = []
    for field_name in _CONFLICT_FIELDS:
        values = {
            _normalized_claim_value(claim.selected_fields.get(field_name))
            for claim in claims
            if claim.selected_fields.get(field_name) not in {None, "", "unknown"}
        }
        if len(values) > 1:
            conflicts.append(field_name)
    return tuple(conflicts)


def _normalized_claim_value(value: object) -> str:
    if isinstance(value, str):
        return " ".join(value.strip().casefold().split())
    return str(value)


def _claim_rank(
    claim: OrganizationIdentityClaimRecord,
) -> tuple[int, float, datetime]:
    return (
        _SOURCE_PRIORITY.get(claim.source_id, 50),
        claim.confidence,
        claim.observed_at,
    )


def _apply_selected_fields(
    identity: OrganizationIdentityRecord,
    fields: dict[str, object],
) -> None:
    identity.kind = str(fields["kind"])
    identity.official_name = str(fields["official_name"])
    identity.country_code = str(fields["country_code"])
    identity.status = str(fields["status"])
    identity.legal_form = _optional_string(fields.get("legal_form"))
    identity.activity_code = _optional_string(fields.get("activity_code"))
    identity.address = _optional_string(fields.get("address"))
    identity.postal_code = _optional_string(fields.get("postal_code"))
    identity.city = _optional_string(fields.get("city"))
    identity.is_headquarters = bool(fields.get("is_headquarters", False))
    identity.valid_from = _parse_date(fields.get("valid_from"))
    identity.valid_until = _parse_date(fields.get("valid_until"))


def _date_value(value: date | None) -> str | None:
    return value.isoformat() if value is not None else None


def _parse_date(value: object) -> date | None:
    if not isinstance(value, str) or not value:
        return None
    return date.fromisoformat(value)


def _optional_string(value: object) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None
