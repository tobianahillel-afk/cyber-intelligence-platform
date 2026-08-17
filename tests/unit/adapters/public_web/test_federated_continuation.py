from __future__ import annotations

from uuid import uuid4

import pytest

from cip.adapters.sources.public_web.federated_continuation import (
    FederatedContinuationBundle,
    FederatedContinuationState,
)
from cip.adapters.sources.public_web.federated_token_runtime import FederatedTokenMaterial
from cip.modules.provider_onboarding.application.federated_authorization import (
    FederatedAuthorizationMaterial,
)


def _bundle() -> FederatedContinuationBundle:
    return FederatedContinuationBundle(
        checkpoint_id=uuid4(),
        job_id=uuid4(),
        delegated_identity_id=uuid4(),
        source_id="provider",
        profile_id="profile",
        state=FederatedContinuationState.AUTHORIZATION_PENDING,
        authorization_url="https://provider.example/oauth/authorize?state=opaque",
        authorization=FederatedAuthorizationMaterial(
            profile_id="profile",
            state="s" * 48,
            code_verifier="v" * 64,
        ),
    )


def test_continuation_round_trip_keeps_secrets_out_of_repr() -> None:
    bundle = _bundle()
    raw = bundle.to_secret_json()
    restored = FederatedContinuationBundle.from_secret_json(raw)

    assert restored == bundle
    assert "v" * 64 not in repr(restored)
    assert "state=opaque" not in repr(restored)


def test_token_ready_round_trip_is_replay_safe() -> None:
    token = FederatedTokenMaterial(
        access_token="opaque-access",
        scopes=("read",),
        refresh_token="opaque-refresh",
        expires_in=3600,
    )
    bundle = _bundle().with_token(token)
    restored = FederatedContinuationBundle.from_secret_json(bundle.to_secret_json())

    assert restored.state is FederatedContinuationState.TOKEN_READY
    assert restored.token == token
    assert "opaque-access" not in repr(restored)
    assert "opaque-refresh" not in repr(restored)


def test_continuation_state_and_token_invariants_fail_closed() -> None:
    base = _bundle()
    token = FederatedTokenMaterial(access_token="opaque")
    with pytest.raises(ValueError, match="requires token"):
        FederatedContinuationBundle(
            checkpoint_id=base.checkpoint_id,
            job_id=base.job_id,
            delegated_identity_id=base.delegated_identity_id,
            source_id=base.source_id,
            profile_id=base.profile_id,
            state=FederatedContinuationState.TOKEN_READY,
            authorization_url=base.authorization_url,
            authorization=base.authorization,
        )
    with pytest.raises(ValueError, match="cannot contain token"):
        FederatedContinuationBundle(
            checkpoint_id=base.checkpoint_id,
            job_id=base.job_id,
            delegated_identity_id=base.delegated_identity_id,
            source_id=base.source_id,
            profile_id=base.profile_id,
            state=FederatedContinuationState.AUTHORIZATION_PENDING,
            authorization_url=base.authorization_url,
            authorization=base.authorization,
            token=token,
        )


def test_continuation_parser_rejects_unknown_shape_and_oversize() -> None:
    with pytest.raises(ValueError, match="shape"):
        FederatedContinuationBundle.from_secret_json('{"version":1}')
    with pytest.raises(ValueError, match="too large"):
        FederatedContinuationBundle.from_secret_json("x" * 70_000)
