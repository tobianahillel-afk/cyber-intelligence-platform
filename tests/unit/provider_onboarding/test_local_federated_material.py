from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest

from cip.modules.provider_onboarding.application.federated_material import (
    FederatedContinuationMaterialStoreError,
)
from cip.modules.provider_onboarding.domain.models import SecretReference
from cip.modules.provider_onboarding.infrastructure.local_federated_material import (
    LocalFederatedContinuationMaterialStore,
)


def test_checkpoint_reference_is_distinct_per_identity_and_checkpoint(tmp_path: Path) -> None:
    store = LocalFederatedContinuationMaterialStore(tmp_path)
    identity = uuid4()
    first = store.reference_for(identity, uuid4())
    second = store.reference_for(identity, uuid4())

    assert first != second
    assert "cip-browser-session" not in first.value
    assert "cip-federated" in first.value


def test_write_resolve_and_delete_round_trip(tmp_path: Path) -> None:
    store = LocalFederatedContinuationMaterialStore(tmp_path)
    reference = store.reference_for(uuid4(), uuid4())

    store.write(reference, '{"state":"opaque"}')

    assert store.is_available(reference)
    assert store.resolve(reference) == '{"state":"opaque"}'
    path = tmp_path / Path(reference.target).name
    assert path.stat().st_mode & 0o777 == 0o600

    store.delete(reference)
    assert not store.is_available(reference)


def test_store_rejects_wrong_scheme_oversize_and_symlink_escape(tmp_path: Path) -> None:
    store = LocalFederatedContinuationMaterialStore(tmp_path)
    with pytest.raises(FederatedContinuationMaterialStoreError, match="file-secret"):
        store.write(SecretReference("env://CIP_L17"), "material")

    reference = store.reference_for(uuid4(), uuid4())
    with pytest.raises(FederatedContinuationMaterialStoreError, match="size"):
        store.write(reference, "x" * 65_537)

    outside = tmp_path.parent / f"outside-{uuid4()}"
    outside.mkdir()
    (tmp_path / "link").symlink_to(outside, target_is_directory=True)
    escaped = SecretReference("file-secret:///run/secrets/link/material.json")
    with pytest.raises(FederatedContinuationMaterialStoreError, match="escaped"):
        store.write(escaped, "material")


def test_missing_material_fails_closed(tmp_path: Path) -> None:
    store = LocalFederatedContinuationMaterialStore(tmp_path)
    reference = store.reference_for(uuid4(), uuid4())

    assert not store.is_available(reference)
    with pytest.raises(FederatedContinuationMaterialStoreError, match="unavailable"):
        store.resolve(reference)
