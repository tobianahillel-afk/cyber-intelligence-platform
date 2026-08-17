from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import StrEnum
from uuid import UUID

from cip.adapters.sources.public_web.federated_token_runtime import FederatedTokenMaterial
from cip.modules.provider_onboarding.application.federated_authorization import (
    FederatedAuthorizationMaterial,
)


class FederatedContinuationState(StrEnum):
    AUTHORIZATION_PENDING = "authorization_pending"
    TOKEN_READY = "token_ready"


@dataclass(frozen=True, slots=True)
class FederatedContinuationBundle:
    checkpoint_id: UUID
    job_id: UUID
    delegated_identity_id: UUID
    source_id: str
    profile_id: str
    state: FederatedContinuationState
    authorization_url: str = field(repr=False)
    authorization: FederatedAuthorizationMaterial = field(repr=False)
    token: FederatedTokenMaterial | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        for value, label, maximum in (
            (self.source_id, "source_id", 64),
            (self.profile_id, "profile_id", 100),
            (self.authorization_url, "authorization_url", 4000),
        ):
            if not value.strip() or len(value) > maximum or "\x00" in value:
                raise ValueError(f"{label} is invalid")
        if self.state is FederatedContinuationState.TOKEN_READY and self.token is None:
            raise ValueError("token_ready continuation requires token material")
        if self.state is FederatedContinuationState.AUTHORIZATION_PENDING and self.token is not None:
            raise ValueError("authorization_pending continuation cannot contain token material")

    def with_token(self, token: FederatedTokenMaterial) -> FederatedContinuationBundle:
        return FederatedContinuationBundle(
            checkpoint_id=self.checkpoint_id,
            job_id=self.job_id,
            delegated_identity_id=self.delegated_identity_id,
            source_id=self.source_id,
            profile_id=self.profile_id,
            state=FederatedContinuationState.TOKEN_READY,
            authorization_url=self.authorization_url,
            authorization=self.authorization,
            token=token,
        )

    def to_secret_json(self) -> str:
        token_payload = None
        if self.token is not None:
            token_payload = json.loads(self.token.to_secret_json())
        return json.dumps(
            {
                "version": 1,
                "checkpoint_id": str(self.checkpoint_id),
                "job_id": str(self.job_id),
                "delegated_identity_id": str(self.delegated_identity_id),
                "source_id": self.source_id,
                "profile_id": self.profile_id,
                "state": self.state.value,
                "authorization_url": self.authorization_url,
                "authorization": json.loads(self.authorization.to_secret_json()),
                "token": token_payload,
            },
            separators=(",", ":"),
            sort_keys=True,
        )
