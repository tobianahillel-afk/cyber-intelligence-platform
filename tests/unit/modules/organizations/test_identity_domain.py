from __future__ import annotations

from datetime import UTC, date, datetime
from uuid import uuid4

import pytest

from cip.modules.organizations.domain.entities import Organization
from cip.modules.organizations.domain.identifiers import (
    IdentifierScheme,
    OfficialIdentifier,
    identifier_from_registration_id,
    normalize_identifier,
)
from cip.modules.organizations.domain.identity import (
    IdentityKind,
    IdentityMergeCandidate,
    IdentityRelationship,
    IdentityStatus,
    MatchMethod,
    MatchState,
    OrganizationIdentity,
    RelationshipType,
)
from cip.modules.organizations.domain.matching import (
    build_merge_candidate,
    normalized_organization_name,
    review_candidate,
)

NOW = datetime(2026, 8, 4, 16, 0, tzinfo=UTC)


def test_official_identifiers_validate_and_normalize() -> None:
    siren = OfficialIdentifier(
        IdentifierScheme.SIREN,
        "732 829 320",
        "sirene-api",
        NOW,
        "fr",
    )
    siret = OfficialIdentifier(
        IdentifierScheme.SIRET,
        "732-829-320-00074",
        "sirene-api",
        NOW,
        "FR",
    )
    lei = OfficialIdentifier(
        IdentifierScheme.LEI,
        "5493001kjtiigc8y1r12",
        "gleif",
        NOW,
    )
    foreign = OfficialIdentifier(
        IdentifierScheme.FOREIGN_REGISTRATION,
        " HRB-12345 ",
        "gleif",
        NOW,
        "DE",
    )

    assert siren.value == "732829320"
    assert siren.exact_key == "siren:FR:732829320"
    assert siret.value == "73282932000074"
    assert lei.value == "5493001KJTIIGC8Y1R12"
    assert foreign.value == "HRB-12345"


@pytest.mark.parametrize(
    ("scheme", "value", "country"),
    (
        (IdentifierScheme.SIREN, "732829321", "FR"),
        (IdentifierScheme.SIRET, "73282932000075", "FR"),
        (IdentifierScheme.LEI, "5493001KJTIIGC8Y1R13", None),
        (IdentifierScheme.FOREIGN_REGISTRATION, "bad value!", "DE"),
        (IdentifierScheme.FOREIGN_REGISTRATION, "HRB123", None),
    ),
)
def test_invalid_official_identifiers_are_rejected(
    scheme: IdentifierScheme,
    value: str,
    country: str | None,
) -> None:
    with pytest.raises(ValueError):
        normalize_identifier(scheme, value, country)


def test_registration_identifier_parser_supports_typed_and_legacy_values() -> None:
    typed = identifier_from_registration_id(
        "SIREN:732829320",
        source_id="legacy",
        verified_at=NOW,
    )
    raw = identifier_from_registration_id(
        "73282932000074",
        source_id="legacy",
        verified_at=NOW,
    )

    assert typed is not None and typed.scheme is IdentifierScheme.SIREN
    assert raw is not None and raw.scheme is IdentifierScheme.SIRET
    assert (
        identifier_from_registration_id(
            "UNKNOWN:123",
            source_id="legacy",
            verified_at=NOW,
        )
        is None
    )
    assert (
        identifier_from_registration_id(
            "not-an-identifier",
            source_id="legacy",
            verified_at=NOW,
        )
        is None
    )


def test_identity_normalizes_aliases_and_has_deterministic_key() -> None:
    identifier = _identifier("732829320")
    identity = OrganizationIdentity(
        kind=IdentityKind.LEGAL_UNIT,
        official_name="Example Société",
        country_code="fr",
        source_id="recherche-entreprises",
        source_record_key="legal-unit:732829320",
        source_url="https://recherche-entreprises.api.gouv.fr/search?q=example",
        confidence=0.98,
        observed_at=NOW,
        status=IdentityStatus.ACTIVE,
        identifiers=(identifier,),
        aliases=(" Example Société ", "EXAMPLE", "EXAMPLE"),
        legal_form=" SAS ",
        valid_from=date(2020, 1, 1),
    )

    assert identity.country_code == "FR"
    assert identity.aliases == ("EXAMPLE",)
    assert identity.legal_form == "SAS"
    assert identity.deterministic_key == identifier.exact_key
    assert OrganizationIdentity.deterministic_id(identifier.exact_key) == (
        OrganizationIdentity.deterministic_id(identifier.exact_key)
    )


def test_identity_relationship_and_candidate_invariants() -> None:
    identity_id = uuid4()
    organization_id = uuid4()

    with pytest.raises(ValueError, match="self-referential"):
        IdentityRelationship(
            subject_identity_id=identity_id,
            object_identity_id=identity_id,
            relationship_type=RelationshipType.DIRECT_PARENT,
            source_id="gleif",
            source_url="https://api.gleif.org/api/v1/lei-records/x",
            confidence=0.9,
            observed_at=NOW,
        )

    with pytest.raises(ValueError, match="exact identifier"):
        IdentityMergeCandidate(
            identity_id=identity_id,
            organization_id=organization_id,
            method=MatchMethod.EXACT_NORMALIZED_NAME,
            score=0.9,
            reasons=("same name",),
            state=MatchState.AUTO_CONFIRMED,
            created_at=NOW,
        )


def test_exact_identifier_is_the_only_automatic_match() -> None:
    organization = _organization(registration_ids=("SIREN:732829320",))
    identity = _identity("Example", identifiers=(_identifier("732829320"),))
    candidate = build_merge_candidate(
        identity,
        organization,
        known_identifiers=(_identifier("732829320", source="target-registry"),),
    )

    assert candidate is not None
    assert candidate.method is MatchMethod.EXACT_IDENTIFIER
    assert candidate.state is MatchState.AUTO_CONFIRMED
    assert candidate.score == 1.0


def test_name_and_postcode_match_requires_human_review() -> None:
    organization = _organization(name="Société Exemple SAS")
    identity = _identity("Societe Exemple", postal_code="75001")

    candidate = build_merge_candidate(
        identity,
        organization,
        target_postal_code="75 001",
    )

    assert candidate is not None
    assert candidate.method is MatchMethod.EXACT_NAME_AND_POSTCODE
    assert candidate.state is MatchState.NEEDS_REVIEW
    assert normalized_organization_name("Société Exemple SAS") == "SOCIETE EXEMPLE"


def test_conflicting_same_scheme_identifiers_are_exposed() -> None:
    organization = _organization(registration_ids=("SIREN:732829320",))
    identity = _identity("Example", identifiers=(_identifier("552100554"),))

    candidate = build_merge_candidate(
        identity,
        organization,
        known_identifiers=(_identifier("732829320", source="target-registry"),),
    )

    assert candidate is not None
    assert candidate.method is MatchMethod.CONFLICTING_IDENTIFIERS
    assert candidate.state is MatchState.NEEDS_REVIEW
    assert "Conflicting siren values" in candidate.reasons[0]


def test_unrelated_identity_produces_no_candidate() -> None:
    assert build_merge_candidate(_identity("Different"), _organization(name="Example")) is None


def test_candidate_review_requires_actor_and_is_final() -> None:
    candidate = IdentityMergeCandidate(
        identity_id=uuid4(),
        organization_id=uuid4(),
        method=MatchMethod.EXACT_NORMALIZED_NAME,
        score=0.75,
        reasons=("Normalized legal name or alias matches",),
        state=MatchState.NEEDS_REVIEW,
        created_at=NOW,
    )

    confirmed = review_candidate(
        candidate,
        confirm=True,
        actor=" analyst ",
        reviewed_at=NOW,
        note="Verified against registry",
    )
    assert confirmed.state is MatchState.CONFIRMED
    assert confirmed.reviewed_by == "analyst"

    with pytest.raises(ValueError, match="already been reviewed"):
        review_candidate(
            confirmed,
            confirm=False,
            actor="analyst",
            reviewed_at=NOW,
        )


def _identifier(value: str, *, source: str = "recherche-entreprises") -> OfficialIdentifier:
    return OfficialIdentifier(
        IdentifierScheme.SIREN,
        value,
        source,
        NOW,
        "FR",
    )


def _identity(
    name: str,
    *,
    identifiers: tuple[OfficialIdentifier, ...] = (),
    postal_code: str | None = None,
) -> OrganizationIdentity:
    return OrganizationIdentity(
        kind=IdentityKind.LEGAL_UNIT,
        official_name=name,
        country_code="FR",
        source_id="recherche-entreprises",
        source_record_key=f"record:{uuid4()}",
        source_url="https://recherche-entreprises.api.gouv.fr/search?q=example",
        confidence=0.9,
        observed_at=NOW,
        identifiers=identifiers,
        postal_code=postal_code,
    )


def _organization(
    *,
    name: str = "Example",
    registration_ids: tuple[str, ...] = (),
) -> Organization:
    return Organization(
        id=uuid4(),
        canonical_name=name,
        legal_name=name,
        country_code="FR",
        registration_ids=registration_ids,
        created_at=NOW,
        updated_at=NOW,
    )
