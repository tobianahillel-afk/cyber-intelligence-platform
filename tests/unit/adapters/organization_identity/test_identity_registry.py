from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from textwrap import dedent
from uuid import UUID

import pytest

from cip.adapters.sources.organization_identity.registry import (
    OrganizationIdentityTarget,
    load_organization_identity_targets,
)
from cip.modules.organizations.domain.identifiers import IdentifierScheme
from cip.modules.source_governance.infrastructure.registry_bundle import (
    load_source_registry_bundle,
)

NOW = datetime(2026, 8, 4, 16, 0, tzinfo=UTC)
ORGANIZATION_ID = UUID("86fe6126-5731-5c4d-a206-69a6a736cae5")


def test_repository_identity_target_registry_is_safe_by_default() -> None:
    targets = load_organization_identity_targets(
        Path("policies/organization_identity_targets.yml")
    )

    assert len(targets) == 1
    assert targets[0].organization_id == ORGANIZATION_ID
    assert targets[0].enabled is False
    assert targets[0].known_identifiers(source_id="test", verified_at=NOW) == ()


def test_target_normalizes_official_identifiers() -> None:
    target = OrganizationIdentityTarget(
        id="example",
        organization_id=ORGANIZATION_ID,
        canonical_name="Example SA",
        country_code="fr",
        query="Example",
        postal_code=" 75001 ",
        siren="732 829 320",
        siret="73282932000074",
        lei="5493001kjtiigc8y1r12",
    )

    identifiers = target.known_identifiers(
        source_id="target-registry",
        verified_at=NOW,
    )
    assert target.country_code == "FR"
    assert target.postal_code == "75001"
    assert [identifier.scheme for identifier in identifiers] == [
        IdentifierScheme.SIREN,
        IdentifierScheme.SIRET,
        IdentifierScheme.LEI,
    ]
    assert identifiers[0].value == "732829320"


def test_target_registry_rejects_invalid_shapes_and_duplicates(tmp_path: Path) -> None:
    cases = (
        ("- bad\n", "root must be a mapping"),
        ("version: 2\ntargets: []\n", "unsupported"),
        ("version: 1\ntargets: {}\n", "targets must be a list"),
        ("version: 1\ntargets: [bad]\n", "must be a mapping"),
    )
    for index, (content, message) in enumerate(cases):
        path = tmp_path / f"bad-{index}.yml"
        path.write_text(content, encoding="utf-8")
        with pytest.raises(ValueError, match=message):
            load_organization_identity_targets(path)

    duplicate = tmp_path / "duplicate.yml"
    duplicate.write_text(
        "version: 1\ntargets:\n"
        + _target_yaml("one", str(ORGANIZATION_ID))
        + _target_yaml("one", "f57f6b5c-89f7-50b8-b0ae-373da3f0da31"),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="duplicate organization identity target id"):
        load_organization_identity_targets(duplicate)

    duplicate_organization = tmp_path / "duplicate-org.yml"
    duplicate_organization.write_text(
        "version: 1\ntargets:\n"
        + _target_yaml("one", str(ORGANIZATION_ID))
        + _target_yaml("two", str(ORGANIZATION_ID)),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="duplicate.*organization_id"):
        load_organization_identity_targets(duplicate_organization)


def test_target_registry_rejects_invalid_values(tmp_path: Path) -> None:
    invalid = (
        ("organization_id: invalid", "UUID"),
        ("country_code: FRA", "ISO alpha-2"),
        ('enabled: "yes"', "enabled must be a boolean"),
        ("siren: '732829321'", "checksum"),
    )
    for index, (replacement, message) in enumerate(invalid):
        content = dedent(
            f"""
            version: 1
            targets:
              - id: example
                organization_id: {ORGANIZATION_ID}
                canonical_name: Example
                country_code: FR
                query: Example
                postal_code: null
                siren: null
                siret: null
                lei: null
                enabled: true
            """
        )
        if replacement.startswith("organization_id"):
            content = content.replace(f"organization_id: {ORGANIZATION_ID}", replacement)
        elif replacement.startswith("country_code"):
            content = content.replace("country_code: FR", replacement)
        elif replacement.startswith("enabled"):
            content = content.replace("enabled: true", replacement)
        else:
            content = content.replace("siren: null", replacement)
        path = tmp_path / f"invalid-value-{index}.yml"
        path.write_text(content, encoding="utf-8")
        with pytest.raises(ValueError, match=message):
            load_organization_identity_targets(path)


def test_source_registry_bundle_loads_identity_sources_and_rejects_duplicates(
    tmp_path: Path,
) -> None:
    entries = load_source_registry_bundle(
        Path("policies/sources.example.yml"),
        Path("policies/identity_sources.yml"),
    )
    ids = {entry.policy.id for entry in entries}

    assert {"recherche-entreprises", "gleif", "bodacc-identity"} <= ids
    sirene = next(entry for entry in entries if entry.policy.id == "sirene-api")
    inpi = next(entry for entry in entries if entry.policy.id == "inpi-rne")
    assert sirene.policy.status.value == "conditional"
    assert inpi.authorization.status.value == "pending_review"

    duplicate = tmp_path / "duplicate.yml"
    duplicate.write_text(
        Path("policies/identity_sources.yml").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="duplicate source id across registries"):
        load_source_registry_bundle(duplicate, duplicate)


def _target_yaml(identifier: str, organization_id: str) -> str:
    return dedent(
        f"""
          - id: {identifier}
            organization_id: {organization_id}
            canonical_name: Example
            country_code: FR
            query: Example
            postal_code: null
            siren: null
            siret: null
            lei: null
            enabled: true
        """
    )
