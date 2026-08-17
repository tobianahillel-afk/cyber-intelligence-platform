from __future__ import annotations

import os
from pathlib import Path
from uuid import uuid4

import pytest

from cip.modules.provider_onboarding.domain.models import SecretReference
from cip.modules.source_governance.application.session_material import SessionMaterialStoreError
from cip.modules.source_governance.infrastructure import local_session_material
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


def test_file_secret_domain_rejects_reference_outside_logical_root() -> None:
    with pytest.raises(ValueError, match="under /run/secrets"):
        SecretReference("file-secret:///tmp/session.json")


def test_resolve_rejects_oversized_and_empty_existing_files(tmp_path: Path) -> None:
    store = LocalFileSessionMaterialStore(tmp_path)
    oversized = store.reference_for(uuid4())
    oversized_path = tmp_path / Path(oversized.target).name
    oversized_path.write_bytes(b"x" * 262_145)

    assert not store.is_available(oversized)
    with pytest.raises(SessionMaterialStoreError, match="unavailable"):
        store.resolve(oversized)

    empty = store.reference_for(uuid4())
    empty_path = tmp_path / Path(empty.target).name
    empty_path.write_bytes(b"")
    with pytest.raises(SessionMaterialStoreError, match="unavailable"):
        store.resolve(empty)


def test_resolve_wraps_read_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    store = LocalFileSessionMaterialStore(tmp_path)
    reference = store.reference_for(uuid4())
    path = tmp_path / Path(reference.target).name
    path.write_text("session", encoding="utf-8")

    def _read_error(self: Path, *, encoding: str) -> str:
        del self, encoding
        raise OSError("read denied")

    monkeypatch.setattr(Path, "read_text", _read_error)
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


def test_write_cleans_temporary_file_after_runtime_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = LocalFileSessionMaterialStore(tmp_path)
    reference = store.reference_for(uuid4())

    def _replace_error(_source: str, _target: Path) -> None:
        raise RuntimeError("replace failed")

    monkeypatch.setattr(os, "replace", _replace_error)
    with pytest.raises(RuntimeError, match="replace failed"):
        store.write(reference, "session")

    assert not list(tmp_path.glob(".cip-session-*"))


def test_write_wraps_filesystem_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    store = LocalFileSessionMaterialStore(tmp_path)
    reference = store.reference_for(uuid4())

    def _mkstemp_error(*args, **kwargs):
        del args, kwargs
        raise OSError("filesystem unavailable")

    monkeypatch.setattr(local_session_material.tempfile, "mkstemp", _mkstemp_error)
    with pytest.raises(SessionMaterialStoreError, match="write failed"):
        store.write(reference, "session")


def test_delete_missing_material_is_idempotent(tmp_path: Path) -> None:
    store = LocalFileSessionMaterialStore(tmp_path)
    reference = store.reference_for(uuid4())

    store.delete(reference)

    assert not store.is_available(reference)


def test_delete_wraps_filesystem_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    store = LocalFileSessionMaterialStore(tmp_path)
    reference = store.reference_for(uuid4())

    def _unlink_error(self: Path, *, missing_ok: bool = False) -> None:
        del self, missing_ok
        raise OSError("delete denied")

    monkeypatch.setattr(Path, "unlink", _unlink_error)
    with pytest.raises(SessionMaterialStoreError, match="deletion failed"):
        store.delete(reference)


def test_store_rejects_symlink_escape_from_configured_root(tmp_path: Path) -> None:
    outside = tmp_path.parent / f"outside-{uuid4()}"
    outside.mkdir()
    link = tmp_path / "link"
    link.symlink_to(outside, target_is_directory=True)
    store = LocalFileSessionMaterialStore(tmp_path)
    reference = SecretReference("file-secret:///run/secrets/link/session.json")

    with pytest.raises(SessionMaterialStoreError, match="escaped configured root"):
        store.write(reference, "session")
