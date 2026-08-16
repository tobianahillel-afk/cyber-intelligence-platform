from __future__ import annotations

from typing import Protocol


class ArtifactStorageError(RuntimeError):
    """An approved raw artifact could not be retained safely."""


class ArtifactStore(Protocol):
    """Deployment-owned object storage for policy-approved evidence artifacts."""

    def put(
        self,
        *,
        object_key: str,
        content: bytes,
        media_type: str,
    ) -> str: ...
