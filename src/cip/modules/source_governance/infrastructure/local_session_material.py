from __future__ import annotations

import os
import tempfile
from contextlib import suppress
from pathlib import Path
from uuid import UUID

from cip.modules.provider_onboarding.domain.models import (
    SecretReference,
    SecretReferenceScheme,
)
from cip.modules.source_governance.application.session_material import (
    MAX_SESSION_MATERIAL_BYTES,
    SessionMaterialStoreError,
)

_LOGICAL_ROOT = Path("/run/secrets")


class LocalFileSessionMaterialStore:
    """Store browser session material behind deterministic file-secret references."""

    def __init__(self, root: Path = _LOGICAL_ROOT) -> None:
        self._root = root

    def reference_for(self, identity_id: UUID) -> SecretReference:
        return SecretReference(
            f"file-secret:///run/secrets/cip-browser-session-{identity_id}.json"
        )

    def is_available(self, reference: SecretReference) -> bool:
        try:
            path = self._path(reference)
            return (
                path.is_file()
                and 0 < path.stat().st_size <= MAX_SESSION_MATERIAL_BYTES
            )
        except (OSError, SessionMaterialStoreError):
            return False

    def resolve(self, reference: SecretReference) -> str:
        path = self._path(reference)
        try:
            if not path.is_file() or path.stat().st_size > MAX_SESSION_MATERIAL_BYTES:
                raise SessionMaterialStoreError("session material is unavailable")
            value = path.read_text(encoding="utf-8")
        except OSError as exc:
            raise SessionMaterialStoreError("session material is unavailable") from exc
        if not value or len(value.encode("utf-8")) > MAX_SESSION_MATERIAL_BYTES:
            raise SessionMaterialStoreError("session material is unavailable")
        return value

    def write(self, reference: SecretReference, value: str) -> None:
        payload = value.encode("utf-8")
        if not payload or len(payload) > MAX_SESSION_MATERIAL_BYTES:
            raise SessionMaterialStoreError("session material size is invalid")
        path = self._path(reference)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            fd, temporary = tempfile.mkstemp(prefix=".cip-session-", dir=path.parent)
            try:
                os.fchmod(fd, 0o600)
                with os.fdopen(fd, "wb", closefd=True) as handle:
                    handle.write(payload)
                    handle.flush()
                    os.fsync(handle.fileno())
                os.replace(temporary, path)
                os.chmod(path, 0o600)
            except Exception:
                with suppress(OSError):
                    os.close(fd)
                Path(temporary).unlink(missing_ok=True)
                raise
        except OSError as exc:
            raise SessionMaterialStoreError("session material write failed") from exc

    def delete(self, reference: SecretReference) -> None:
        path = self._path(reference)
        try:
            path.unlink(missing_ok=True)
        except OSError as exc:
            raise SessionMaterialStoreError("session material deletion failed") from exc

    def _path(self, reference: SecretReference) -> Path:
        if reference.scheme is not SecretReferenceScheme.FILE_SECRET:
            raise SessionMaterialStoreError("session store requires file-secret reference")
        logical = Path(reference.target)
        try:
            relative = logical.relative_to(_LOGICAL_ROOT)
        except ValueError as exc:
            raise SessionMaterialStoreError("session reference is outside logical root") from exc
        path = (self._root / relative).resolve()
        root = self._root.resolve()
        if path != root and root not in path.parents:
            raise SessionMaterialStoreError("session reference escaped configured root")
        return path
