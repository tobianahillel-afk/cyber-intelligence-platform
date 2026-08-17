from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import StrEnum
from uuid import UUID

from cip.adapters.sources.public_web.federated_token_runtime import FederatedTokenMaterial
from cip.modules.provider_onboarding.application.federated_authorization import (
    FederatedAuthorizationMaterial,
)

_MAX_CONTINUATION_JSON_BYTES = 65_536


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

    @classmethod
    def from_secret_json(cls, payload: str) -> FederatedContinuationBundle:
        if len(payload.encode("utf-8")) > _MAX_CONTINUATION_JSON_BYTES:
            raise ValueError("federated continuation material is too large")
        try:
            value = json.loads(payload)
        except json.JSONDecodeError as exc:
            raise ValueError("invalid federated continuation material") from exc
        required = {
            "version",
            "checkpoint_id",
            "job_id",
            "delegated_identity_id",
            "source_id",
            "profile_id",
            "state",
            "authorization_url",
            "authorization",
            "token",
        }
        if not isinstance(value, dict) or set(value) != required or value.get("version") != 1:
            raise ValueError("invalid federated continuation material shape")
        try:
            checkpoint_id = UUID(str(value["checkpoint_id"]))
            job_id = UUID(str(value["job_id"]))
            delegated_identity_id = UUID(str(value["delegated_identity_id"]))
            state = FederatedContinuationState(str(value["state"]))
        except (ValueError, TypeError) as exc:
            raise ValueError("invalid federated continuation identity fields") from exc
        source_id = value["source_id"]
        profile_id = value["profile_id"]
        authorization_url = value["authorization_url"]
        authorization = value["authorization"]
        token = value["token"]
        if not all(isinstance(item, str) for item in (source_id, profile_id, authorization_url)):
            raise ValueError("invalid federated continuation string fields")
        authorization_material = FederatedAuthorizationMaterial.from_secret_json(
            json.dumps(authorization, separators=(",", ":"), sort_keys=True)
        )
        token_material = _token_from_payload(token) if token is not None else None
        return cls(
            checkpoint_id=checkpoint_id,
            job_id=job_id,
            delegated_identity_id=delegated_identity_id,
            source_id=source_id,
            profile_id=profile_id,
            state=state,
            authorization_url=authorization_url,
            authorization=authorization_material,
            token=token_material,
        )


def _token_from_payload(value: object) -> FederatedTokenMaterial:
    if not isinstance(value, dict):
        raise ValueError("invalid federated token continuation payload")
    required = {
        "version",
        "access_token",
        "token_type",
        "scopes",
        "expires_in",
        "refresh_token",
        "id_token",
    }
    if set(value) != required or value.get("version") != 1:
        raise ValueError("invalid federated token continuation shape")
    scopes = value["scopes"]
    if not isinstance(scopes, list) or any(not isinstance(item, str) for item in scopes):
        raise ValueError("invalid federated token continuation scopes")
    access_token = value["access_token"]
    token_type = value["token_type"]
    expires_in = value["expires_in"]
    refresh_token = value["refresh_token"]
    id_token = value["id_token"]
    if not isinstance(access_token, str) or not isinstance(token_type, str):
        raise ValueError("invalid federated token continuation fields")
    if expires_in is not None and (not isinstance(expires_in, int) or isinstance(expires_in, bool)):
        raise ValueError("invalid federated token continuation expiry")
    if refresh_token is not None and not isinstance(refresh_token, str):
        raise ValueError("invalid federated token continuation refresh token")
    if id_token is not None and not isinstance(id_token, str):
        raise ValueError("invalid federated token continuation id token")
    return FederatedTokenMaterial(
        access_token=access_token,
        token_type=token_type,
        scopes=tuple(scopes),
        expires_in=expires_in,
        refresh_token=refresh_token,
        id_token=id_token,
    )
