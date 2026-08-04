from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

import pytest

from cip.adapters.sources.organization_identity.registry import OrganizationIdentityTarget
from cip.modules.collection_orchestration.application.bodacc_identity_adapter import (
    BodaccIdentityAdapter,
    _checkpoint_from_payload as bodacc_checkpoint,
)
from cip.modules.collection_orchestration.application.gleif_adapter import (
    GleifAdapter,
    _checkpoint_from_payload as gleif_checkpoint,
)
from cip.modules.collection_orchestration.application.identity_adapters import (
    register_identity_adapters,
)
from cip.modules.collection_orchestration.application.ports import (
    AdapterExecutionError,
    CollectionAdapter,
)
from cip.modules.collection_orchestration.application.recherche_entreprises_adapter import (
    RechercheEntreprisesAdapter,
    _checkpoint_from_payload as recherche_checkpoint,
)
from cip.modules.source_governance.infrastructure.registry import (
    SourceRegistryEntry,
    load_source_registry,
)

NOW = datetime(2026, 8, 4, 16, 0, tzinfo=UTC)
ORGANIZATION_ID = UUID("86fe6126-5731-5c4d-a206-69a6a736cae5")


def test_identity_adapters_are_not_registered_without_enabled_targets() -> None:
    adapters: dict[tuple[str, str], CollectionAdapter] = {}

    register_identity_adapters(
        adapters,
        _entries(),
        (_target(enabled=False),),
        timeout_seconds=30,
    )

    assert adapters == {}


def test_compatible_enabled_targets_register_three_identity_adapters() -> None:
    adapters: dict[tuple[str, str], CollectionAdapter] = {}

    register_identity_adapters(
        adapters,
        _entries(),
        (_target(),),
        timeout_seconds=30,
    )

    assert set(adapters) == {
        ("recherche-entreprises", "recherche-entreprises-search"),
        ("gleif", "gleif-lei-api"),
        ("bodacc-identity", "bodacc-commercial-announcements"),
    }
    assert isinstance(
        adapters[("recherche-entreprises", "recherche-entreprises-search")],
        RechercheEntreprisesAdapter,
    )
    assert isinstance(adapters[("gleif", "gleif-lei-api")], GleifAdapter)
    assert isinstance(
        adapters[("bodacc-identity", "bodacc-commercial-announcements")],
        BodaccIdentityAdapter,
    )


def test_registration_is_provider_specific() -> None:
    entries = _entries()

    french_only: dict[tuple[str, str], CollectionAdapter] = {}
    register_identity_adapters(
        french_only,
        entries,
        (replace(_target(), lei=None),),
        timeout_seconds=30,
    )
    assert set(french_only) == {
        ("recherche-entreprises", "recherche-entreprises-search"),
        ("bodacc-identity", "bodacc-commercial-announcements"),
    }

    lei_only: dict[tuple[str, str], CollectionAdapter] = {}
    register_identity_adapters(
        lei_only,
        entries,
        (
            OrganizationIdentityTarget(
                id="foreign",
                organization_id=ORGANIZATION_ID,
                canonical_name="Synthetic Foreign Company",
                country_code="DE",
                query="Synthetic Foreign Company",
                lei="5493001KJTIIGC8Y1R12",
                enabled=True,
            ),
        ),
        timeout_seconds=30,
    )
    assert set(lei_only) == {("gleif", "gleif-lei-api")}


def test_missing_source_entries_are_skipped() -> None:
    adapters: dict[tuple[str, str], CollectionAdapter] = {}

    register_identity_adapters(
        adapters,
        {},
        (_target(),),
        timeout_seconds=30,
    )

    assert adapters == {}


@pytest.mark.parametrize(
    ("factory", "payload"),
    (
        (recherche_checkpoint, None),
        (gleif_checkpoint, None),
        (bodacc_checkpoint, None),
    ),
)
def test_empty_checkpoint_is_supported(factory, payload) -> None:  # type: ignore[no-untyped-def]
    assert factory(payload) is None


def test_recherche_and_gleif_checkpoint_round_trip() -> None:
    payload = {
        "fingerprints": {
            "target": {
                "record": "hash",
            }
        }
    }

    recherche = recherche_checkpoint(payload)
    gleif = gleif_checkpoint(payload)

    assert recherche is not None
    assert recherche.fingerprints["target"]["record"] == "hash"
    assert gleif is not None
    assert gleif.fingerprints["target"]["record"] == "hash"


def test_bodacc_checkpoint_round_trip() -> None:
    checkpoint = bodacc_checkpoint({"fingerprints": {"target": "hash"}})

    assert checkpoint is not None
    assert checkpoint.fingerprints == {"target": "hash"}


@pytest.mark.parametrize(
    ("factory", "payload"),
    (
        (recherche_checkpoint, {}),
        (recherche_checkpoint, {"fingerprints": []}),
        (recherche_checkpoint, {"fingerprints": {1: {"record": "hash"}}}),
        (recherche_checkpoint, {"fingerprints": {"target": []}}),
        (recherche_checkpoint, {"fingerprints": {"target": {1: "hash"}}}),
        (gleif_checkpoint, {}),
        (gleif_checkpoint, {"fingerprints": {"target": {"record": 1}}}),
        (bodacc_checkpoint, {}),
        (bodacc_checkpoint, {"fingerprints": []}),
        (bodacc_checkpoint, {"fingerprints": {1: "hash"}}),
        (bodacc_checkpoint, {"fingerprints": {"target": 1}}),
    ),
)
def test_invalid_checkpoints_are_non_retryable(factory, payload) -> None:  # type: ignore[no-untyped-def]
    with pytest.raises(AdapterExecutionError) as captured:
        factory(payload)

    assert captured.value.error_code == "invalid_checkpoint"
    assert captured.value.retryable is False


@pytest.mark.parametrize(
    ("adapter_type", "source_id"),
    (
        (RechercheEntreprisesAdapter, "recherche-entreprises"),
        (GleifAdapter, "gleif"),
        (BodaccIdentityAdapter, "bodacc-identity"),
    ),
)
def test_adapter_constructors_validate_source_timeout_and_targets(
    adapter_type,
    source_id: str,
) -> None:  # type: ignore[no-untyped-def]
    entry = _entries()[source_id]
    target = _target()

    with pytest.raises(ValueError, match="source policy"):
        adapter_type(_entries()["gleif" if source_id != "gleif" else "bodacc-identity"], (target,))
    with pytest.raises(ValueError, match="timeout_seconds"):
        adapter_type(entry, (target,), timeout_seconds=0)

    incompatible = (
        replace(target, enabled=False)
        if source_id == "recherche-entreprises"
        else replace(target, lei=None)
        if source_id == "gleif"
        else replace(target, siren=None)
    )
    with pytest.raises(ValueError):
        adapter_type(entry, (incompatible,))


def _entries() -> dict[str, SourceRegistryEntry]:
    return {
        entry.policy.id: entry
        for entry in load_source_registry(Path("policies/identity_sources.yml"))
    }


def _target(*, enabled: bool = True) -> OrganizationIdentityTarget:
    return OrganizationIdentityTarget(
        id="synthetic-fr",
        organization_id=ORGANIZATION_ID,
        canonical_name="Synthetic Company SAS",
        country_code="FR",
        query="Synthetic Company",
        postal_code="75001",
        siren="732829320",
        siret="73282932000074",
        lei="5493001KJTIIGC8Y1R12",
        enabled=enabled,
    )
