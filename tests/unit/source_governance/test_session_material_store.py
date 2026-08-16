from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest

from cip.modules.provider_onboarding.domain.models import SecretReference
from cip.modules.source_governance.application.session_material import (
    SessionMaterialStoreError,
)
from cip.modules.source_governance.infrastructure.local_session_material import (
    LocalFileSessionMaterialStore,
)


def test_file_session_store_round_trip_and_delete(tmp_path: Path) -> None:
    store = LocalFileSessionMaterialStore(tmp_path)
    reference = store.reference_for(uuid4())

    assert not store.is_available(reference)
    store.write(reference, '{"cookies":[],"origins":[]}')

    assert store.is_available(reference)
    assert store.resolve(reference) == '{"cookies":[],"origins":[]}'
    stored = next(tmp_path.iterdir())
    assert stored.stat().st_mode & 0o777 == 0o600

    store.delete(reference)
    assert not store.is_available(reference)


def test_file_session_store_rejects_non_file_reference(tmp_path: Path) -> None:
    store = LocalFileSessionMaterialStore(tmp_path)
    reference = SecretReference("env://CIP_SESSION_TEST")

    with pytest.raises(SessionMaterialStoreError, match="file-secret"):
        store.write(reference, "secret-session")


def test_file_session_store_rejects_empty_and_oversized_material(tmp_path: Path) -> None:
    store = LocalFileSessionMaterialStore(tmp_path)
    reference = store.reference_for(uuid4())

    with pytest.raises(SessionMaterialStoreError, match="size"):
        store.write(reference, "")
    with pytest.raises(SessionMaterialStoreError, match="size"):
        store.write(reference, "x" * 262_145)


def test_file_session_store_maps_logical_reference_under_configured_root(
    tmp_path: Path,
) -> None:
    store = LocalFileSessionMaterialStore(tmp_path)
    reference = SecretReference("file-secret:///run/secrets/nested/session.json")

    store.write(reference, "session")

    assert (tmp_path / "nested" / "session.json").read_text(encoding="utf-8") == "session"
