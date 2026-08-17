from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest

from cip.adapters.sources.public_web import delegated_session_state as state
from cip.modules.provider_onboarding.domain.browser_login import (
    ProviderLoginHttpMethod,
    ProviderLoginProfile,
    ProviderLoginTransitionRule,
)

NOW = datetime(2026, 8, 17, tzinfo=UTC)


def _profile() -> ProviderLoginProfile:
    return ProviderLoginProfile(
        id="session-state-v1",
        source_id="provider",
        login_url="https://provider.example/login",
        username_selector="#username",
        secret_selector="#password",
        submit_selector="#submit",
        success_selector="#ok",
        authenticated_probe_url="https://provider.example/private",
        allowed_transitions=(
            ProviderLoginTransitionRule(
                host="provider.example",
                path_prefix="/",
                methods=frozenset(
                    {ProviderLoginHttpMethod.GET, ProviderLoginHttpMethod.POST}
                ),
            ),
        ),
        review_reference="AUTH-L16-STATE",
        reviewed_at=NOW,
    )


def test_parse_rejects_empty_oversized_non_mapping_and_missing_lists() -> None:
    profile = _profile()
    for raw, match in (
        ("", "size_invalid"),
        ("x" * 262_145, "size_invalid"),
        ("[]", "shape_invalid"),
        ('{"cookies":[]}', "shape_invalid"),
    ):
        with pytest.raises(state.ProviderSessionInvalidError, match=match):
            state.parse_storage_state(raw, profile)


def test_entry_budgets_are_enforced() -> None:
    profile = _profile()
    with pytest.raises(state.ProviderSessionInvalidError, match="entry_budget"):
        state.validate_storage_state(
            {"cookies": [{}] * 65, "origins": []},
            profile,
        )
    with pytest.raises(state.ProviderSessionInvalidError, match="entry_budget"):
        state.validate_storage_state(
            {"cookies": [], "origins": [{}] * 17},
            profile,
        )


def test_cookie_shape_type_origin_and_field_budgets_are_enforced() -> None:
    profile = _profile()
    invalid_values = (
        ["cookie"],
        [{"name": "sid", "value": 7, "domain": "provider.example"}],
        [{"name": "sid", "value": "x", "domain": "evil.example"}],
        [{"name": "n" * 16_385, "value": "x", "domain": "provider.example"}],
    )
    matches = ("cookie_invalid", "cookie_invalid", "cookie_origin_denied", "field_budget")
    for cookies, match in zip(invalid_values, matches, strict=True):
        with pytest.raises(state.ProviderSessionInvalidError, match=match):
            state.validate_storage_state(
                {"cookies": cookies, "origins": []},
                profile,
            )


def test_origin_and_local_storage_guards_cover_all_shapes() -> None:
    profile = _profile()
    invalid_origins = (
        ["origin"],
        [{"origin": 7, "localStorage": []}],
        [{"origin": "https://evil.example", "localStorage": []}],
        [
            {
                "origin": "https://provider.example",
                "localStorage": [{}] * 129,
            }
        ],
        [{"origin": "https://provider.example", "localStorage": ["item"]}],
        [
            {
                "origin": "https://provider.example",
                "localStorage": [{"name": "key", "value": 7}],
            }
        ],
        [
            {
                "origin": "https://provider.example",
                "localStorage": [{"name": "k" * 16_385, "value": "x"}],
            }
        ],
    )
    matches = (
        "origin_invalid",
        "origin_invalid",
        "origin_denied",
        "storage_budget",
        "storage_invalid",
        "storage_invalid",
        "field_budget",
    )
    for origins, match in zip(invalid_origins, matches, strict=True):
        with pytest.raises(state.ProviderSessionInvalidError, match=match):
            state.validate_storage_state(
                {"cookies": [], "origins": origins},
                profile,
            )


def test_subdomains_are_allowed_and_serialized_total_size_is_bounded() -> None:
    profile = _profile()
    state.validate_storage_state(
        {
            "cookies": [
                {"name": "sid", "value": "x", "domain": ".api.provider.example"}
            ],
            "origins": [
                {"origin": "https://api.provider.example", "localStorage": []}
            ],
        },
        profile,
    )
    oversized = {
        "cookies": [],
        "origins": [
            {
                "origin": "https://provider.example",
                "localStorage": [
                    {"name": f"key-{index}", "value": "x" * 16_000}
                    for index in range(20)
                ],
            }
        ],
    }
    with pytest.raises(state.ProviderSessionInvalidError, match="state_exceeds_budget"):
        state.serialize_storage_state(oversized, profile)  # type: ignore[arg-type]


def test_valid_round_trip_is_canonical_json() -> None:
    profile = _profile()
    payload = {
        "cookies": [
            {"name": "sid", "value": "opaque", "domain": "provider.example"}
        ],
        "origins": [],
    }

    serialized = state.serialize_storage_state(payload, profile)  # type: ignore[arg-type]

    assert json.loads(serialized) == payload
    assert state.parse_storage_state(serialized, profile)["cookies"][0]["name"] == "sid"
