from __future__ import annotations

import os
from pathlib import Path
from typing import Protocol

from cip.modules.provider_onboarding.domain.models import (
    SecretReference,
    SecretReferenceScheme,
)


class SecretReferenceResolver(Protocol):
    def is_available(self, reference: SecretReference) -> bool: ...


class LocalSecretReferenceResolver:
    """Check configured secret backends without returning or logging secret values."""

    def is_available(self, reference: SecretReference) -> bool:
        if reference.scheme is SecretReferenceScheme.ENV:
            return bool(os.environ.get(reference.target))
        if reference.scheme is SecretReferenceScheme.FILE_SECRET:
            path = Path(reference.target)
            try:
                return path.is_file() and path.stat().st_size > 0
            except OSError:
                return False
        return False
