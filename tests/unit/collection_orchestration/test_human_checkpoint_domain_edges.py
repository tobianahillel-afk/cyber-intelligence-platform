from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest

from cip.modules.collection_orchestration.domain.human_checkpoints import (
    HumanCheckpointBinding,
    HumanCheckpointKind,
    HumanCheckpointRequest,
    HumanCheckpointResumeRequest,
    correlation_digest,
    correlation_matches,
    validate_actor_reference,
)

NOW = datetime(2026, 8, 17, tzinfo=UTC)
JOB_ID = UUID("10000000-0000-4000-8000-000000000001")
IDENTITY_ID = UUID("20000000-0000-4000-8000-000000000002")
TOKEN = "controlled-correlation-token"


def _binding(**changes: object) -> HumanCheckpointBinding:
    values: dict[str, object] = {
        "job_id": JOB_ID,
        "source_id": "provider",
        "adapter_id": "adapter",
        "delegated_identity_id": IDENTITY_ID,
        "purpose": "authorized-research",
    }
    values.update(changes)
    return HumanCheckpointBinding(**values)  # type: ignore[arg-type]


def _request(**changes: object) -> HumanCheckpointRequest:
    values: dict[str, object] = {
        "binding": _binding(),
        "kind": HumanCheckpointKind.OAUTH_CONSENT,
        "correlation_digest": correlation_digest(TOKEN),
        "session_reference": "file-secret:///run/secrets/material.json",
        "created_at": NOW,
        "expires_at": NOW + timedelta(minutes=10),
    }
    values.update(changes)
    return HumanCheckpointRequest(**values)  # type: ignore[arg-type]


@pytest.mark.parametrize("field", ["source_id", "adapter_id", "purpose"])
def test_binding_rejects_empty_and_oversize_fields(field: str) -> None:
    with pytest.raises(ValueError, match=field):
        _binding(**{field: " "})
    with pytest.raises(ValueError, match=field):
        _binding(**{field: "x" * 201})


def test_request_rejects_expiry_digest_and_reference_edges() -> None:
    with pytest.raises(ValueError, match="expires_at"):
        _request(expires_at=NOW)
    with pytest.raises(ValueError, match="SHA-256"):
        _request(correlation_digest="x" * 63)
    with pytest.raises(ValueError, match="SHA-256"):
        _request(correlation_digest="g" * 64)
    with pytest.raises(ValueError, match="session_reference"):
        _request(session_reference="not-a-reference")
    with pytest.raises(ValueError, match="session_reference"):
        _request(session_reference="file-secret://" + "x" * 500)


def test_request_allows_no_session_reference_and_from_token_hashes_value() -> None:
    without_reference = _request(session_reference=None)
    assert without_reference.session_reference is None

    request = HumanCheckpointRequest.from_correlation_token(
        binding=_binding(),
        kind=HumanCheckpointKind.MFA,
        correlation_token=TOKEN,
        session_reference="file-secret:///run/secrets/material.json",
        created_at=NOW,
        expires_at=NOW + timedelta(minutes=5),
    )
    assert request.correlation_digest == correlation_digest(TOKEN)
    assert TOKEN not in repr(request)


@pytest.mark.parametrize(
    "token",
    ["short", " padded-correlation-token ", "x" * 513],
)
def test_correlation_token_bounds_fail_closed(token: str) -> None:
    with pytest.raises(ValueError, match="correlation token"):
        correlation_digest(token)


def test_correlation_match_true_and_false_are_constant_time_interface() -> None:
    digest = correlation_digest(TOKEN)
    assert correlation_matches(TOKEN, digest)
    assert not correlation_matches("different-valid-token", digest)


@pytest.mark.parametrize("actor", [" ", "x" * 201])
def test_actor_reference_bounds_are_shared_by_resume_and_validator(actor: str) -> None:
    with pytest.raises(ValueError, match="actor_reference"):
        validate_actor_reference(actor)
    with pytest.raises(ValueError, match="actor_reference"):
        HumanCheckpointResumeRequest(
            checkpoint_id=UUID("30000000-0000-4000-8000-000000000003"),
            binding=_binding(),
            correlation_token=TOKEN,
            actor_reference=actor,
            resumed_at=NOW,
        )


def test_resume_request_rejects_bad_token_and_naive_time() -> None:
    with pytest.raises(ValueError, match="correlation token"):
        HumanCheckpointResumeRequest(
            checkpoint_id=UUID("30000000-0000-4000-8000-000000000003"),
            binding=_binding(),
            correlation_token="short",
            actor_reference="user:approver",
            resumed_at=NOW,
        )
    with pytest.raises(ValueError, match="timezone-aware"):
        HumanCheckpointResumeRequest(
            checkpoint_id=UUID("30000000-0000-4000-8000-000000000003"),
            binding=_binding(),
            correlation_token=TOKEN,
            actor_reference="user:approver",
            resumed_at=datetime(2026, 8, 17),
        )
