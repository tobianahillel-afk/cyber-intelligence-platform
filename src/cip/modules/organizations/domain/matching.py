from __future__ import annotations

import re
import unicodedata
from dataclasses import replace
from datetime import datetime
from uuid import NAMESPACE_URL, UUID, uuid5

from cip.modules.organizations.domain.entities import Organization
from cip.modules.organizations.domain.identifiers import OfficialIdentifier
from cip.modules.organizations.domain.identity import (
    IdentityMergeCandidate,
    MatchMethod,
    MatchState,
    OrganizationIdentity,
)
from cip.shared.kernel.time import require_aware_utc

_NON_WORD = re.compile(r"[^A-Z0-9]+")
_LEGAL_SUFFIXES = {
    "SA",
    "SAS",
    "SASU",
    "SARL",
    "EURL",
    "SCI",
    "SCA",
    "SCS",
    "SE",
    "SOCIETE",
    "COMPANY",
    "LIMITED",
    "LTD",
    "PLC",
    "GMBH",
    "AG",
}


def build_merge_candidate(
    identity: OrganizationIdentity,
    organization: Organization,
    *,
    known_identifiers: tuple[OfficialIdentifier, ...] = (),
    target_postal_code: str | None = None,
) -> IdentityMergeCandidate | None:
    identity_keys = {identifier.exact_key for identifier in identity.identifiers}
    known_keys = {identifier.exact_key for identifier in known_identifiers}
    exact = sorted(identity_keys & known_keys)
    candidate_id = _candidate_id(identity.id, organization.id)
    if exact:
        return IdentityMergeCandidate(
            id=candidate_id,
            identity_id=identity.id,
            organization_id=organization.id,
            method=MatchMethod.EXACT_IDENTIFIER,
            score=1.0,
            reasons=(f"Exact official identifier match: {exact[0]}",),
            state=MatchState.AUTO_CONFIRMED,
            created_at=identity.observed_at,
        )
    conflicts = _identifier_conflicts(identity.identifiers, known_identifiers)
    if conflicts:
        return IdentityMergeCandidate(
            id=candidate_id,
            identity_id=identity.id,
            organization_id=organization.id,
            method=MatchMethod.CONFLICTING_IDENTIFIERS,
            score=0.1,
            reasons=tuple(conflicts),
            state=MatchState.NEEDS_REVIEW,
            created_at=identity.observed_at,
        )
    identity_names = {_normalize_name(identity.official_name)} | {
        _normalize_name(alias) for alias in identity.aliases
    }
    organization_names = {_normalize_name(organization.canonical_name)}
    if organization.legal_name:
        organization_names.add(_normalize_name(organization.legal_name))
    names_match = bool(identity_names & organization_names)
    postcode_matches = bool(
        target_postal_code
        and identity.postal_code
        and _normalize_postal_code(target_postal_code)
        == _normalize_postal_code(identity.postal_code)
    )
    if names_match and postcode_matches:
        return IdentityMergeCandidate(
            id=candidate_id,
            identity_id=identity.id,
            organization_id=organization.id,
            method=MatchMethod.EXACT_NAME_AND_POSTCODE,
            score=0.92,
            reasons=(
                "Normalized legal name matches",
                "Business postal code matches",
            ),
            state=MatchState.NEEDS_REVIEW,
            created_at=identity.observed_at,
        )
    if names_match:
        return IdentityMergeCandidate(
            id=candidate_id,
            identity_id=identity.id,
            organization_id=organization.id,
            method=MatchMethod.EXACT_NORMALIZED_NAME,
            score=0.75,
            reasons=("Normalized legal name or alias matches",),
            state=MatchState.NEEDS_REVIEW,
            created_at=identity.observed_at,
        )
    return None


def review_candidate(
    candidate: IdentityMergeCandidate,
    *,
    confirm: bool,
    actor: str,
    reviewed_at: datetime,
    note: str | None = None,
) -> IdentityMergeCandidate:
    reviewer = actor.strip()
    if not reviewer:
        raise ValueError("actor is required")
    reviewed = require_aware_utc(reviewed_at, field_name="reviewed_at")
    reviewable_states = {MatchState.NEEDS_REVIEW, MatchState.AUTO_CONFIRMED}
    if candidate.state not in reviewable_states:
        raise ValueError("candidate has already been reviewed")
    return replace(
        candidate,
        state=MatchState.CONFIRMED if confirm else MatchState.REJECTED,
        reviewed_at=reviewed,
        reviewed_by=reviewer,
        review_note=note.strip() if note and note.strip() else None,
    )


def normalized_organization_name(value: str) -> str:
    return _normalize_name(value)


def _identifier_conflicts(
    observed: tuple[OfficialIdentifier, ...],
    known: tuple[OfficialIdentifier, ...],
) -> list[str]:
    observed_by_scheme = _values_by_scheme(observed)
    known_by_scheme = _values_by_scheme(known)
    conflicts: list[str] = []
    shared_schemes = observed_by_scheme.keys() & known_by_scheme.keys()
    for scheme in sorted(shared_schemes):
        if observed_by_scheme[scheme].isdisjoint(known_by_scheme[scheme]):
            conflicts.append(
                f"Conflicting {scheme} values: observed "
                f"{sorted(observed_by_scheme[scheme])}, expected "
                f"{sorted(known_by_scheme[scheme])}"
            )
    return conflicts


def _values_by_scheme(
    identifiers: tuple[OfficialIdentifier, ...],
) -> dict[str, set[str]]:
    values: dict[str, set[str]] = {}
    for identifier in identifiers:
        values.setdefault(identifier.scheme.value, set()).add(identifier.value)
    return values


def _normalize_name(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value)
    ascii_value = "".join(
        character
        for character in decomposed
        if not unicodedata.combining(character)
    )
    tokens = [
        token
        for token in _NON_WORD.sub(" ", ascii_value.upper()).split()
        if token
    ]
    while tokens and tokens[-1] in _LEGAL_SUFFIXES:
        tokens.pop()
    return " ".join(tokens)


def _normalize_postal_code(value: str) -> str:
    return _NON_WORD.sub("", value.upper())


def _candidate_id(identity_id: UUID, organization_id: UUID) -> UUID:
    return uuid5(
        NAMESPACE_URL,
        f"identity-merge-candidate:{identity_id}:{organization_id}",
    )
