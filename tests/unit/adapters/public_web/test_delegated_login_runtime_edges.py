from __future__ import annotations

from datetime import UTC, datetime

import pytest

from cip.adapters.sources.public_web import delegated_login_runtime as runtime
from cip.adapters.sources.public_web.delegated_login_executor import (
    PublicWebDelegatedLoginExecutor,
)
from cip.modules.provider_onboarding.domain.browser_login import (
    ProviderLoginHttpMethod,
    ProviderLoginProfile,
    ProviderLoginTransitionRule,
)
from cip.modules.source_governance.domain.models import (
    AuthorizationStatus,
    DataCategory,
    HttpMethod,
    SourceAuthorization,
    SourcePolicy,
    SourceStatus,
    SourceType,
)
from cip.modules.source_governance.infrastructure.registry import SourceRegistryEntry

NOW = datetime(2026, 8, 17, tzinfo=UTC)
PURPOSE = "authenticated-provider-research"


def _entry() -> SourceRegistryEntry:
    return SourceRegistryEntry(
        SourcePolicy(
            id="controlled-provider",
            name="Controlled provider",
            base_url="https://provider.example/",
            status=SourceStatus.ENABLED,
            source_type=SourceType.BROWSER,
            owner="CIP tests",
            licence="controlled",
            allowed_data_categories=frozenset(
                {DataCategory.OFFICIAL_DOCUMENT_DISCOVERY}
            ),
            human_review_required=False,
        ),
        SourceAuthorization(
            status=AuthorizationStatus.APPROVED,
            document_reference="AUTH-L16-CONTROLLED",
            reviewed_at=NOW,
            approved_hosts=frozenset({"provider.example"}),
            approved_path_prefixes=("/",),
            approved_purposes=frozenset({PURPOSE}),
            approved_http_methods=frozenset({HttpMethod.GET, HttpMethod.POST}),
            automated_collection_allowed=True,
        ),
        {},
    )


def _profile(*, source_id: str = "controlled-provider") -> ProviderLoginProfile:
    return ProviderLoginProfile(
        id="controlled-login-v1",
        source_id=source_id,
        login_url="https://provider.example/login",
        username_selector="#username",
        secret_selector="#password",
        submit_selector="#submit",
        success_selector="#authenticated",
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
        review_reference="AUTH-L16-CONTROLLED",
        reviewed_at=NOW,
    )


class _NavigationErrorPage:
    def goto(self, *_args, **_kwargs) -> None:
        raise runtime.PlaywrightError("navigation failed")


class _SubmitPage:
    def __init__(self, error: Exception) -> None:
        self.error = error

    def wait_for_load_state(self, *_args, **_kwargs) -> None:
        raise self.error


def test_navigation_error_is_typed_and_policy_denial_wins() -> None:
    with pytest.raises(runtime.ProviderLoginRuntimeError, match="navigation_failed"):
        runtime._goto(
            _NavigationErrorPage(),  # type: ignore[arg-type]
            "https://provider.example/login",
            1000,
            runtime._NetworkState(),
        )

    state = runtime._NetworkState(denial="provider_login_source_policy_denied")
    with pytest.raises(runtime.ProviderLoginPolicyError, match="source_policy_denied"):
        runtime._goto(
            _NavigationErrorPage(),  # type: ignore[arg-type]
            "https://provider.example/login",
            1000,
            state,
        )


def test_submit_wait_handles_timeout_and_typed_browser_error() -> None:
    runtime._wait_after_submit(
        _SubmitPage(runtime.PlaywrightTimeoutError("timeout")),  # type: ignore[arg-type]
        1000,
        runtime._NetworkState(),
    )

    with pytest.raises(runtime.ProviderLoginRuntimeError, match="submit_failed"):
        runtime._wait_after_submit(
            _SubmitPage(runtime.PlaywrightError("submit failed")),  # type: ignore[arg-type]
            1000,
            runtime._NetworkState(),
        )


def test_network_denial_without_browser_exception_is_fail_closed() -> None:
    state = runtime._NetworkState(denial="provider_login_transition_denied")
    with pytest.raises(runtime.ProviderLoginPolicyError, match="transition_denied"):
        runtime._raise_network_denial(state)


def test_login_executor_rejects_source_profile_mismatch() -> None:
    with pytest.raises(ValueError, match="source/profile mismatch"):
        PublicWebDelegatedLoginExecutor(
            _entry(),
            _profile(source_id="different-provider"),
        )
