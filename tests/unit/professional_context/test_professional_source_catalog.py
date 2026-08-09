from __future__ import annotations

import pytest

from cip.adapters.sources.professional_context_catalogs import (
    PROFESSIONAL_CONTEXT_SOURCE_CANDIDATES,
    ProfessionalSourceCandidate,
)
from cip.modules.professional_context.domain import CommunityAcquisitionMode


def test_professional_source_candidates_are_non_executable_and_unscoped() -> None:
    assert len(PROFESSIONAL_CONTEXT_SOURCE_CANDIDATES) == 3
    assert all(item.authorization_required for item in PROFESSIONAL_CONTEXT_SOURCE_CANDIDATES)
    assert all(item.executable is False for item in PROFESSIONAL_CONTEXT_SOURCE_CANDIDATES)
    assert all(item.approved_hosts == () for item in PROFESSIONAL_CONTEXT_SOURCE_CANDIDATES)
    assert all(item.approved_paths == () for item in PROFESSIONAL_CONTEXT_SOURCE_CANDIDATES)
    assert all(item.runtime_adapter is None for item in PROFESSIONAL_CONTEXT_SOURCE_CANDIDATES)


def test_professional_source_catalog_has_no_private_or_outreach_fields() -> None:
    forbidden_fragments = (
        "personal_phone",
        "personal_address",
        "private_message",
        "friend_graph",
        "password",
        "credential",
        "outreach",
    )
    fields = {
        field.casefold()
        for candidate in PROFESSIONAL_CONTEXT_SOURCE_CANDIDATES
        for field in candidate.allowed_fields
    }

    assert not any(fragment in field for fragment in forbidden_fragments for field in fields)


def test_professional_source_candidate_cannot_enable_runtime_scope() -> None:
    with pytest.raises(ValueError, match="cannot be executable"):
        ProfessionalSourceCandidate(
            source_id="unsafe",
            source_kind="unsafe",
            acquisition_mode=CommunityAcquisitionMode.APPROVED_API,
            purpose="unsafe test candidate",
            allowed_fields=("role_title",),
            executable=True,
        )

    with pytest.raises(ValueError, match="runtime execution scope"):
        ProfessionalSourceCandidate(
            source_id="unsafe-host",
            source_kind="unsafe",
            acquisition_mode=CommunityAcquisitionMode.APPROVED_API,
            purpose="unsafe host test candidate",
            allowed_fields=("role_title",),
            approved_hosts=("example.invalid",),
        )
