from __future__ import annotations

from uuid import uuid4

import pytest

from cip.modules.public_footprint.domain import (
    PublicStructuredState,
    PublicStructuredStateKind,
)


def test_network_structured_state_canonicalizes_payload_and_identity() -> None:
    organization_id = uuid4()
    version_id = uuid4()
    state = PublicStructuredState(
        organization_id=organization_id,
        resource_version_id=version_id,
        kind=PublicStructuredStateKind.NETWORK_JSON,
        page_url="https://example.com/app#fragment",
        source_locator="https://example.com/api/state",
        source_url="https://example.com/api/state#x",
        http_status=200,
        media_type="Application/JSON; charset=utf-8",
        payload_json=' { "b": 2, "a": 1 } ',
    )

    assert state.page_url == "https://example.com/app"
    assert state.source_url == "https://example.com/api/state"
    assert state.media_type == "application/json"
    assert state.payload_json == '{"a":1,"b":2}'
    assert len(state.payload_hash_sha256) == 64
    assert state.identity_key == state.identity_key_for_version(version_id)
    assert state.identity_key_for_version(uuid4()) != state.identity_key


def test_script_state_requires_extractor_and_forbids_http_metadata() -> None:
    common = dict(
        organization_id=uuid4(),
        resource_version_id=uuid4(),
        kind=PublicStructuredStateKind.SCRIPT_STATE,
        page_url="https://example.com/app",
        source_locator="window.__INITIAL_STATE__",
        payload_json='{"name":"Example"}',
    )

    with pytest.raises(ValueError, match="requires extractor_id"):
        PublicStructuredState(**common)
    with pytest.raises(ValueError, match="cannot carry HTTP"):
        PublicStructuredState(
            **common,
            extractor_id="public-known-globals-v1",
            source_url="https://example.com/api/state",
        )


def test_network_state_requires_complete_2xx_response_metadata() -> None:
    common = dict(
        organization_id=uuid4(),
        resource_version_id=uuid4(),
        kind=PublicStructuredStateKind.NETWORK_JSON,
        page_url="https://example.com/app",
        source_locator="https://example.com/api/state",
        source_url="https://example.com/api/state",
        media_type="application/json",
        payload_json='{"ok":true}',
    )

    with pytest.raises(ValueError, match="requires source_url"):
        PublicStructuredState(**{**common, "source_url": None}, http_status=200)
    with pytest.raises(ValueError, match="status must be 2xx"):
        PublicStructuredState(**common, http_status=404)
    with pytest.raises(ValueError, match="cannot have an extractor_id"):
        PublicStructuredState(
            **common,
            http_status=200,
            extractor_id="not-allowed",
        )


@pytest.mark.parametrize("payload", ["not-json", "1", "null", '"text"'])
def test_structured_state_requires_object_or_array_json(payload: str) -> None:
    with pytest.raises(ValueError, match="payload_json"):
        PublicStructuredState(
            organization_id=uuid4(),
            resource_version_id=uuid4(),
            kind=PublicStructuredStateKind.SCRIPT_STATE,
            page_url="https://example.com/app",
            source_locator="window.__INITIAL_STATE__",
            extractor_id="public-known-globals-v1",
            payload_json=payload,
        )
