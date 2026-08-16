from __future__ import annotations

from datetime import datetime

from cip.adapters.sources.public_web.delegated_login_runtime import (
    execute_reviewed_provider_login,
    execute_reviewed_provider_logout,
    execute_reviewed_session_reuse,
)
from cip.modules.provider_onboarding.application.secrets import SecretValueResolver
from cip.modules.provider_onboarding.domain.browser_login import ProviderLoginProfile
from cip.modules.provider_onboarding.domain.models import SecretReference
from cip.modules.source_governance.application.provider_session_runtime import (
    AuthenticatedBrowserRuntimeResult,
)
from cip.modules.source_governance.infrastructure.registry import SourceRegistryEntry


class PublicWebDelegatedLoginExecutor:
    def __init__(
        self,
        entry: SourceRegistryEntry,
        profile: ProviderLoginProfile,
    ) -> None:
        if profile.source_id != entry.policy.id:
            raise ValueError("delegated login executor source/profile mismatch")
        self._entry = entry
        self._profile = profile

    @property
    def source_id(self) -> str:
        return self._profile.source_id

    @property
    def session_ttl_seconds(self) -> int:
        return self._profile.session_ttl_seconds

    @property
    def supports_remote_logout(self) -> bool:
        return self._profile.logout_url is not None

    def login(
        self,
        *,
        account_identifier: str,
        secret_reference: SecretReference,
        secret_resolver: SecretValueResolver,
        purpose: str,
        now: datetime,
    ) -> AuthenticatedBrowserRuntimeResult:
        result = execute_reviewed_provider_login(
            self._entry,
            self._profile,
            account_identifier=account_identifier,
            secret_reference=secret_reference,
            secret_resolver=secret_resolver,
            purpose=purpose,
            now=now,
        )
        return _result(result)

    def reuse(
        self,
        *,
        session_reference: SecretReference,
        session_resolver: SecretValueResolver,
        purpose: str,
        now: datetime,
    ) -> AuthenticatedBrowserRuntimeResult:
        result = execute_reviewed_session_reuse(
            self._entry,
            self._profile,
            session_reference=session_reference,
            session_resolver=session_resolver,
            purpose=purpose,
            now=now,
        )
        return _result(result)

    def logout(
        self,
        *,
        session_reference: SecretReference,
        session_resolver: SecretValueResolver,
        purpose: str,
        now: datetime,
    ) -> bool:
        return execute_reviewed_provider_logout(
            self._entry,
            self._profile,
            session_reference=session_reference,
            session_resolver=session_resolver,
            purpose=purpose,
            now=now,
        )


def _result(value) -> AuthenticatedBrowserRuntimeResult:
    return AuthenticatedBrowserRuntimeResult(
        final_url=value.final_url,
        html=value.html,
        session_state_json=value.session_state_json,
        requests_seen=value.requests_seen,
        redirects_seen=value.redirects_seen,
    )
