from __future__ import annotations

import json
from collections.abc import Callable
from uuid import UUID

import pytest

from cip.adapters.sources.public_web.federated_continuation import (
    FederatedContinuationBundle,
    FederatedContinuationState,
)
from cip.adapters.sources.public_web.federated_token_runtime import FederatedTokenMaterial
from cip.modules.provider_onboarding.application.federated_authorization import (
    FederatedAuthorizationMaterial,
)

CHECKPOINT_ID = UUID("10000000-0000-4000-8000-000000000001")
JOB_ID = UUID("20000000-0000-4000-8000-000000000002")
IDENTITY_ID = UUID("30000000-0000-4000-8000-000000000003")


def _bundle() -> FederatedContinuationBundle:
    return FederatedContinuationBundle(
        checkpoint_id=CHECKPOINT_ID,
        job_id=JOB_ID,
        delegated_identity_id=IDENTITY_ID,
        source_id="provider",
        profile_id="profile",
        state=FederatedContinuationState.AUTHORIZATION_PENDING,
        authorization_url="https://provider.example/oauth/authorize",
        authorization=FederatedAuthorizationMaterial(
            profile_id="profile",
            state="s" * 48,
            code_verifier="v" * 64,
        ),
    )


def _ready_payload() -> dict[str, object]:
    bundle = _bundle().with_token(
        FederatedTokenMaterial(
            access_token="opaque-access",
            scopes=("read",),
            expires_in=3600,
            refresh_token="opaque-refresh",
            id_token="opaque-id",
        )
    )
    value = json.loads(bundle.to_secret_json())
    assert isinstance(value, dict)
    return value


@pytest.mark.parametrize(
    ("field", "value", "match"),
    [
        ("source_id", " ", "source_id"),
        ("profile_id", "x" * 101, "profile_id"),
        ("authorization_url", "bad\x00url", "authorization_url"),
    ],
)
def test_bundle_rejects_invalid_bounded_strings(
    field: str,
    value: str,
    match: str,
) -> None:
    values: dict[str, object] = {
        "checkpoint_id": CHECKPOINT_ID,
        "job_id": JOB_ID,
        "delegated_identity_id": IDENTITY_ID,
        "source_id": "provider",
        "profile_id": "profile",
        "state": FederatedContinuationState.AUTHORIZATION_PENDING,
        "authorization_url": "https://provider.example/oauth/authorize",
        "authorization": _bundle().authorization,
    }
    values[field] = value
    with pytest.raises(ValueError, match=match):
        FederatedContinuationBundle(**values)  # type: ignore[arg-type]


def test_parser_rejects_invalid_json_identity_and_string_fields() -> None:
    with pytest.raises(ValueError, match="invalid federated continuation material"):
        FederatedContinuationBundle.from_secret_json("{")

    payload = json.loads(_bundle().to_secret_json())
    payload["checkpoint_id"] = "not-a-uuid"
    with pytest.raises(ValueError, match="identity fields"):
        FederatedContinuationBundle.from_secret_json(json.dumps(payload))

    payload = json.loads(_bundle().to_secret_json())
    payload["source_id"] = 42
    with pytest.raises(ValueError, match="string fields"):
        FederatedContinuationBundle.from_secret_json(json.dumps(payload))


def test_parser_rejects_invalid_state_and_authorization_material() -> None:
    payload = json.loads(_bundle().to_secret_json())
    payload["state"] = "impossible"
    with pytest.raises(ValueError, match="identity fields"):
        FederatedContinuationBundle.from_secret_json(json.dumps(payload))

    payload = json.loads(_bundle().to_secret_json())
    payload["authorization"] = {"version": 1}
    with pytest.raises(ValueError, match="authorization material shape"):
        FederatedContinuationBundle.from_secret_json(json.dumps(payload))


@pytest.mark.parametrize(
    ("mutate", "match"),
    [
        (lambda token: "not-a-dict", "token continuation payload"),
        (lambda token: {"version": 1}, "token continuation shape"),
        (
            lambda token: {**token, "scopes": "read"},
            "token continuation scopes",
        ),
        (
            lambda token: {**token, "scopes": ["read", 1]},
            "token continuation scopes",
        ),
        (
            lambda token: {**token, "access_token": 1},
            "token continuation fields",
        ),
        (
            lambda token: {**token, "token_type": 1},
            "token continuation fields",
        ),
        (
            lambda token: {**token, "expires_in": True},
            "token continuation expiry",
        ),
        (
            lambda token: {**token, "refresh_token": 1},
            "continuation refresh token",
        ),
        (
            lambda token: {**token, "id_token": 1},
            "continuation id token",
        ),
    ],
)
def test_parser_rejects_malformed_token_material(
    mutate: Callable[[dict[str, object]], object],
    match: str,
) -> None:
    payload = _ready_payload()
    token = payload["token"]
    assert isinstance(token, dict)
    payload["token"] = mutate(token)
    with pytest.raises(ValueError, match=match):
        FederatedContinuationBundle.from_secret_json(json.dumps(payload))
