from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol

from cip.modules.provider_onboarding.application.secrets import (
    SecretValueResolver,
)
from cip.modules.provider_onboarding.domain.models import SecretReference


@dataclass(frozen=True, slots=True)
class AuthenticatedBrowserRuntimeResult:
    final_url: str
    html: bytes = field(repr=False)
    session_state_json: str = field(repr=False)
    requests_seen: int = 0
    redirects_seen: int = 0


class DelegatedBrowserSessionExecutor(Protocol):
    @property
    def source_id(self) -> str: ...

    @property
    def session_ttl_seconds(self) -> int: ...

    @property
    def supports_remote_logout(self) -> bool: ...

    def login(
        self,
        *,
        account_identifier: str,
        secret_reference: SecretReference,
        secret_resolver: SecretValueResolver,
        purpose: str,
        now: datetime,
    ) -> AuthenticatedBrowserRuntimeResult: ...

    def reuse(
        self,
        *,
        session_reference: SecretReference,
        session_resolver: SecretValueResolver,
        purpose: str,
        now: datetime,
    ) -> AuthenticatedBrowserRuntimeResult: ...

    def logout(
        self,
        *,
        session_reference: SecretReference,
        session_resolver: SecretValueResolver,
        purpose: str,
        now: datetime,
    ) -> bool: ...
