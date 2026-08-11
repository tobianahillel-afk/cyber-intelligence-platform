from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest

from cip.modules.provider_onboarding.domain.models import AuthMode, OnboardingState
from cip.modules.provider_onboarding.infrastructure.registry import load_provider_profiles


def test_repository_provider_catalog_has_safe_defaults() -> None:
    profiles = load_provider_profiles(Path("policies/provider_onboarding.yml"))
    by_source = {profile.source_id: profile for profile in profiles}

    assert len(profiles) == 26
    assert by_source["cisa-kev"].initial_state is OnboardingState.CONNECTED
    assert by_source["ashby-job-board"].auth_mode is AuthMode.NONE
    assert by_source["ashby-job-board"].initial_state is OnboardingState.CONNECTED
    assert by_source["recruitee-careers-site"].auth_mode is AuthMode.NONE
    assert by_source["recruitee-careers-site"].initial_state is OnboardingState.CONNECTED
    assert by_source["teamtailor-public-jobs"].auth_mode is AuthMode.API_KEY
    assert by_source["teamtailor-public-jobs"].required_secret_names == ("api_token",)
    assert by_source["teamtailor-public-jobs"].initial_state is OnboardingState.NOT_CONFIGURED
    assert by_source["sirene-api"].auth_mode is AuthMode.NONE
    assert by_source["inpi-rne"].required_secret_names == ("username", "password")
    assert by_source["brave-search-api"].auth_mode is AuthMode.API_KEY
    assert by_source["brave-search-api"].required_secret_names == ("api_token",)
    assert by_source["brave-search-api"].initial_state is OnboardingState.NOT_CONFIGURED
    assert by_source["github-code-search-metadata"].auth_mode is AuthMode.API_KEY
    assert by_source["github-code-search-metadata"].required_secret_names == (
        "api_token",
    )
    assert (
        by_source["github-code-search-metadata"].initial_state
        is OnboardingState.NOT_CONFIGURED
    )
    assert by_source["patentsview-patent-metadata"].auth_mode is AuthMode.API_KEY
    assert by_source["patentsview-patent-metadata"].required_secret_names == (
        "api_key",
    )
    assert (
        by_source["patentsview-patent-metadata"].initial_state
        is OnboardingState.NOT_CONFIGURED
    )
    assert by_source["mojeek-web-search-metadata"].auth_mode is AuthMode.API_KEY
    assert by_source["mojeek-web-search-metadata"].required_secret_names == ("api_key",)
    assert by_source["mojeek-web-search-metadata"].automatic_onboarding is False
    assert (
        by_source["mojeek-web-search-metadata"].initial_state
        is OnboardingState.NOT_CONFIGURED
    )
    assert by_source["internet-archive-cdx"].initial_state is OnboardingState.CONNECTED
    assert by_source["cloudflare-doh"].auth_mode is AuthMode.NONE
    assert by_source["cloudflare-doh"].initial_state is OnboardingState.CONNECTED
    assert by_source["certspotter-ct"].auth_mode is AuthMode.API_KEY
    assert by_source["certspotter-ct"].required_secret_names == ("api_token",)
    assert by_source["certspotter-ct"].initial_state is OnboardingState.NOT_CONFIGURED
    assert by_source["sec-cyber-disclosures"].auth_mode is AuthMode.NONE
    assert by_source["sec-cyber-disclosures"].initial_state is OnboardingState.CONNECTED
    assert by_source["phishtank-verified-online"].auth_mode is AuthMode.API_KEY
    assert by_source["phishtank-verified-online"].required_secret_names == ("api_token",)
    assert by_source["phishtank-verified-online"].initial_state is OnboardingState.NOT_CONFIGURED
    assert by_source["linkedin-official-api"].initial_state is OnboardingState.NOT_CONFIGURED
    assert by_source["linkedin-authorized-browser"].initial_state is OnboardingState.BLOCKED
    assert by_source["brixhub"].initial_state is OnboardingState.BLOCKED


def test_provider_catalog_rejects_invalid_shapes_and_duplicates(tmp_path: Path) -> None:
    cases = (
        ("- invalid\n", "root must be a mapping"),
        ("version: 2\nproviders: []\n", "unsupported"),
        ("version: 1\nproviders: {}\n", "providers must be a list"),
        ("version: 1\nproviders: [invalid]\n", "must be a mapping"),
    )
    for index, (content, message) in enumerate(cases):
        path = tmp_path / f"invalid-{index}.yml"
        path.write_text(content, encoding="utf-8")
        with pytest.raises(ValueError, match=message):
            load_provider_profiles(path)

    duplicate = tmp_path / "duplicate.yml"
    duplicate.write_text(
        "version: 1\nproviders:\n" + _profile_yaml("same") + _profile_yaml("same"),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="duplicate provider"):
        load_provider_profiles(duplicate)


def test_provider_catalog_rejects_invalid_values(tmp_path: Path) -> None:
    invalid_values = (
        ("auth_mode: invalid", "invalid"),
        ('automatic_onboarding: "yes"', "boolean"),
        ("documentation_url: http://provider.example/docs", "HTTPS"),
        ("human_actions: [invalid]", "invalid"),
    )
    for index, (replacement, message) in enumerate(invalid_values):
        content = dedent(
            """
            version: 1
            providers:
              - source_id: provider
                display_name: Provider
                auth_mode: none
                documentation_url: https://provider.example/docs
                signup_url: null
                console_url: null
                required_secret_names: []
                human_actions: []
                automatic_onboarding: true
                blocked_reason: null
            """
        )
        if replacement.startswith("auth_mode"):
            content = content.replace("auth_mode: none", replacement)
        elif replacement.startswith("automatic"):
            content = content.replace("automatic_onboarding: true", replacement)
        elif replacement.startswith("documentation"):
            content = content.replace(
                "documentation_url: https://provider.example/docs",
                replacement,
            )
        else:
            content = content.replace("human_actions: []", replacement)
        path = tmp_path / f"invalid-value-{index}.yml"
        path.write_text(content, encoding="utf-8")
        with pytest.raises(ValueError, match=message):
            load_provider_profiles(path)


def test_missing_provider_catalog_is_reported(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_provider_profiles(tmp_path / "missing.yml")


def _profile_yaml(source_id: str) -> str:
    return dedent(
        f"""
          - source_id: {source_id}
            display_name: Provider
            auth_mode: none
            documentation_url: https://provider.example/docs
            signup_url: null
            console_url: null
            required_secret_names: []
            human_actions: []
            automatic_onboarding: true
            blocked_reason: null
        """
    )
