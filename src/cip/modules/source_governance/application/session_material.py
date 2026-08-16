from __future__ import annotations

from typing import Protocol
from uuid import UUID

from cip.modules.provider_onboarding.domain.models import SecretReference


class SessionMaterialStore(Protocol):
    def reference_for(self, identity_id: UUID) -> SecretReference: ...

    def is_available(self, reference: SecretReference) -> bool: ...

    def resolve(self, reference: SecretReference) -> str: ...

    def write(self, reference: SecretReference, value: str) -> None: ...

    def delete(self, reference: SecretReference) -> None: ...


class SessionMaterialStoreError(RuntimeError):
    pass
