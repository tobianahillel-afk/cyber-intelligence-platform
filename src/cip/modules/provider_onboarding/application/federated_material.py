from __future__ import annotations

from typing import Protocol
from uuid import UUID

from cip.modules.provider_onboarding.domain.models import SecretReference

MAX_FEDERATED_CONTINUATION_BYTES = 65_536


class FederatedContinuationMaterialStore(Protocol):
    def reference_for(
        self,
        delegated_identity_id: UUID,
        checkpoint_id: UUID,
    ) -> SecretReference: ...

    def is_available(self, reference: SecretReference) -> bool: ...

    def resolve(self, reference: SecretReference) -> str: ...

    def write(self, reference: SecretReference, value: str) -> None: ...

    def delete(self, reference: SecretReference) -> None: ...


class FederatedContinuationMaterialStoreError(RuntimeError):
    pass
