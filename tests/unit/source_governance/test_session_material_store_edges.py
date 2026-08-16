from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest

from cip.modules.provider_onboarding.domain.models import SecretReference
from cip.modules.source_governance.application.session_material import SessionMaterialStoreError
from cip.modules.source_governance.infrastructure.local_session_material import (
    LocalFileSessionMaterialStore,
)


def test_missing_and_non_file_references_are_unavailable(tmp_path: Path) -> None:
    store = LocalFileSessionMaterialStore(tmp_path)
    reference = store.reference_for(uuid4())
    assert not store.is_available(reference)
    assert not store.is_available(SecretReference("env://CIP_SESSION"))
    with pytest.raises(SessionMaterialStoreError, match="unavailable"):
        store.resolve(reference)


def test_store_rejects_reference_outside_logical_root(tmp_path: Path) -> None:
    store = LocalFileSessionMaterialStore(tmp_path)
    reference = SecretReference("file-secret:///tmp/session.json")

    assert not store.is_available(reference)
    with pytest.raises(SessionMaterialStoreError, match="logical root"):
        store.resolve(reference)
    with pytest.raises(SessionMaterialStoreError, match="logical root"):
        store.delete(reference)


def test_resolve_rejects_oversized_existing_file(tmp_path: Path) -> None:
    store = LocalFileSessionMaterialStore(tmp_path)
    reference = store.reference_for(uuid4())
    path = tmp_path / Path(reference.target).name
    path.write_bytes(b"x" * 262_145)

    assert not store.is_available(reference)
    with pytest.raises(SessionMaterialStoreError, match="unavailable"):
        store.resolve(reference)


def test_write_creates_nested_parent_and_overwrites_atomically(tmp_path: Path) -> None:
    store = LocalFileSessionMaterialStore(tmp_path)
    reference = SecretReference("file-secret:///run/secrets/nested/deeper/session.json")

    store.write(reference, "first")
    store.write(reference, "second")

    path = tmp_path / "nested" / "deeper" / "session.json"
    assert path.read_text(encoding="utf-8") == "second"
    assert path.stat().st_mode & 0o777 == 0o600


def test_delete_missing_material_is_idempotent(tmp_path: Path) -> None:
    store = LocalFileSessionMaterialStore(tmp_path)
    reference = store.reference_for(uuid4())

    store.delete(reference)

    assert not store.is_available(reference)
