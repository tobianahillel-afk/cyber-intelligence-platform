from __future__ import annotations

import os
from pathlib import Path
from uuid import uuid4

import pytest

from cip.modules.provider_onboarding.application.federated_material import (
    MAX_FEDERATED_CONTINUATION_BYTES,
    FederatedContinuationMaterialStoreError,
)
from cip.modules.provider_onboarding.domain.models import SecretReference
from cip.modules.provider_onboarding.infrastructure.local_federated_material import (
    LocalFederatedContinuationMaterialStore,
)


def test_resolve_rejects_empty_and_oversize_existing_files(tmp_path: Path) -> None:
    store = LocalFederatedContinuationMaterialStore(tmp_path)
    reference = store.reference_for(uuid4(), uuid4())
    path = tmp_path / Path(reference.target).name
    path.write_bytes(b"")
    with pytest.raises(FederatedContinuationMaterialStoreError, match="unavailable"):
        store.resolve(reference)

    path.write_bytes(b"x" * (MAX_FEDERATED_CONTINUATION_BYTES + 1))
    with pytest.raises(FederatedContinuationMaterialStoreError, match="unavailable"):
        store.resolve(reference)


def test_is_available_and_resolve_hide_filesystem_errors(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = LocalFederatedContinuationMaterialStore(tmp_path)
    reference = store.reference_for(uuid4(), uuid4())

    def fail_is_file(self: Path) -> bool:
        del self
        raise OSError("filesystem unavailable")

    monkeypatch.setattr(Path, "is_file", fail_is_file)
    assert not store.is_available(reference)
    with pytest.raises(FederatedContinuationMaterialStoreError, match="unavailable"):
        store.resolve(reference)


def test_write_cleans_temporary_file_when_atomic_replace_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = LocalFederatedContinuationMaterialStore(tmp_path)
    reference = store.reference_for(uuid4(), uuid4())

    def fail_replace(source: str | os.PathLike[str], target: str | os.PathLike[str]) -> None:
        del source, target
        raise RuntimeError("replace interrupted")

    monkeypatch.setattr(os, "replace", fail_replace)
    with pytest.raises(RuntimeError, match="replace interrupted"):
        store.write(reference, "material")
    assert not list(tmp_path.glob(".cip-federated-*"))


def test_write_wraps_directory_oserror(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = LocalFederatedContinuationMaterialStore(tmp_path)
    reference = store.reference_for(uuid4(), uuid4())

    def fail_mkdir(self: Path, *args: object, **kwargs: object) -> None:
        del self, args, kwargs
        raise OSError("read only")

    monkeypatch.setattr(Path, "mkdir", fail_mkdir)
    with pytest.raises(FederatedContinuationMaterialStoreError, match="write failed"):
        store.write(reference, "material")


def test_delete_wraps_filesystem_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = LocalFederatedContinuationMaterialStore(tmp_path)
    reference = store.reference_for(uuid4(), uuid4())
    store.write(reference, "material")

    def fail_unlink(self: Path, *args: object, **kwargs: object) -> None:
        del self, args, kwargs
        raise OSError("busy")

    monkeypatch.setattr(Path, "unlink", fail_unlink)
    with pytest.raises(FederatedContinuationMaterialStoreError, match="deletion failed"):
        store.delete(reference)


def test_reference_domain_rejects_outside_logical_root() -> None:
    with pytest.raises(ValueError, match="must stay under /run/secrets"):
        SecretReference("file-secret:///var/tmp/material.json")
