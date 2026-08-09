from __future__ import annotations

import os
from pathlib import Path
from typing import Protocol

from cip.modules.provider_onboarding.domain.models import (
    SecretReference,
    SecretReferenceScheme,
)

_MAX_RUNTIME_SECRET_BYTES = 16_384


class SecretReferenceResolver(Protocol):
    def is_available(self, reference: SecretReference) -> bool: ...


class SecretValueResolver(Protocol):
    def resolve(self, reference: SecretReference) -> str: ...


class LocalSecretReferenceResolver:
    """Check configured secret backends without returning or logging secret values."""

    def is_available(self, reference: SecretReference) -> bool:
        if reference.scheme is SecretReferenceScheme.ENV:
            return bool(os.environ.get(reference.target))
        if reference.scheme is SecretReferenceScheme.FILE_SECRET:
            path = Path(reference.target)
            try:
                return path.is_file() and 0 < path.stat().st_size <= _MAX_RUNTIME_SECRET_BYTES
            except OSError:
                return False
        return False


class LocalSecretValueResolver:
    """Resolve approved local secret references transiently for provider requests."""

    def resolve(self, reference: SecretReference) -> str:
        if reference.scheme is SecretReferenceScheme.ENV:
            value = os.environ.get(reference.target)
            return _validated_secret(value)
        if reference.scheme is SecretReferenceScheme.FILE_SECRET:
            path = Path(reference.target)
            try:
                if not path.is_file() or path.stat().st_size > _MAX_RUNTIME_SECRET_BYTES:
                    raise RuntimeError("runtime secret reference is unavailable")
                value = path.read_text(encoding="utf-8")
            except OSError as exc:
                raise RuntimeError("runtime secret reference is unavailable") from exc
            return _validated_secret(value)
        raise RuntimeError("runtime secret backend is not supported by this deployment")


def _validated_secret(value: str | None) -> str:
    if value is None:
        raise RuntimeError("runtime secret reference is unavailable")
    normalized = value.strip()
    if not normalized or len(normalized.encode("utf-8")) > _MAX_RUNTIME_SECRET_BYTES:
        raise RuntimeError("runtime secret reference is unavailable")
    return normalized
