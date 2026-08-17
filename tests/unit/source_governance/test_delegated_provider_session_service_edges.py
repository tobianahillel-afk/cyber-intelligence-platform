from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest

from cip.modules.provider_onboarding.domain.models import SecretReference
from cip.modules.source_governance.application import delegated_provider_session_service as service
from cip.modules.source_governance.application.delegated_identity_contracts import (
    DelegatedIdentityExecutionGrant,
    DelegatedReferenceUnavailableError,
)
from cip.modules.source_governance.application.provider_session_runtime import (
    AuthenticatedBrowserRuntimeResult,
)
from cip.modules.source_governance.domain.accounts import SourceAccountAuthMode
from cip.modules.source_governance.domain.delegated_browser_identity import (
    DelegatedExecutionRequest,
    DelegatedOwnerKind,
)

NOW = datetime(2026, 8, 17, 2, 0, tzinfo=UTC)
SOURCE = "controlled-provider"
PURPOSE = "authenticated-provider-research"
TENANT = uuid4()
IDENTITY = uuid4()


def _request() -> DelegatedExecutionRequest:
    return DelegatedExecutionRequest(
        tenant_id=TENANT,
        owner_kind=DelegatedOwnerKind.SERVICE_PRINCIPAL,
        owner_subject_id="l16-worker",
        source_id=SOURCE,
        purpose=PURPOSE,
        required_scopes=frozenset({"authenticated-page.read"}),
    )


def _grant(*, secret: str | None = None, session: str | None = None):
    return DelegatedIdentityExecutionGrant(
        identity_id=IDENTITY,
        source_id=SOURCE,
        tenant_id=TENANT,
        purpose=PURPOSE,
        approved_scopes=("authenticated-page.read",),
        secret_reference=secret,
        session_reference=session,
    )


class _ReferenceResolver:
    def is_available(self, _reference: SecretReference) -> bool:
        return True


class _ValueResolver:
    def resolve(self, _reference: SecretReference) -> str:
        return "secret"


class _Store:
    def __init__(self) -> None:
        self.writes: list[tuple[str, str]] = []
        self.deletes: list[str] = []

    def reference_for(self, identity_id: UUID) -> SecretReference:
        return SecretReference(
            f"file-secret:///run/secrets/cip-browser-session-{identity_id}.json"
        )

    def is_available(self, _reference: SecretReference) -> bool:
        return True

    def resolve(self, _reference: SecretReference) -> str:
        return '{"cookies":[],"origins":[]}'

    def write(self, reference: SecretReference, value: str) -> None:
        self.writes.append((reference.value, value))

    def delete(self, reference: SecretReference) -> None:
        self.deletes.append(reference.value)


class _Executor:
    source_id = SOURCE
    session_ttl_seconds = 3600
    supports_remote_logout = True

    def __init__(self, *, logout_error: bool = False) -> None:
        self.logout_error = logout_error

    def login(self, **_kwargs) -> AuthenticatedBrowserRuntimeResult:
        return AuthenticatedBrowserRuntimeResult(
            final_url="https://provider.example/private",
            html=b"ok",
            session_state_json='{"cookies":[],"origins":[]}',
        )

    def reuse(self, **_kwargs) -> AuthenticatedBrowserRuntimeResult:
        return self.login()

    def logout(self, **_kwargs) -> bool:
        if self.logout_error:
            raise RuntimeError("remote unavailable")
        return True


def _view(*, auth_mode: SourceAccountAuthMode = SourceAccountAuthMode.INTERACTIVE_SESSION):
    return SimpleNamespace(
        source_id=SOURCE,
        auth_mode=auth_mode,
        provider_account_identifier="controlled-user",
    )


def test_establish_deletes_material_if_reference_attach_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = _Store()
    monkeypatch.setattr(service, "get_delegated_identity", lambda *args, **kwargs: _view())
    monkeypatch.setattr(
        service,
        "issue_delegated_execution_grant",
        lambda *args, **kwargs: _grant(secret="env://CIP_L16_SECRET"),
    )

    def _attach_failure(*args, **kwargs) -> None:
        raise RuntimeError("persistence failed")

    monkeypatch.setattr(service, "attach_delegated_session_reference", _attach_failure)

    with pytest.raises(RuntimeError, match="persistence failed"):
        service.establish_delegated_provider_session(
            object(),  # type: ignore[arg-type]
            IDENTITY,
            _request(),
            _Executor(),
            secret_reference_resolver=_ReferenceResolver(),
            secret_value_resolver=_ValueResolver(),
            session_store=store,
            now=NOW,
        )

    reference = store.reference_for(IDENTITY).value
    assert store.writes and store.writes[0][0] == reference
    assert store.deletes == [reference]


def test_revoke_is_locally_successful_when_remote_logout_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = _Store()
    monkeypatch.setattr(service, "get_delegated_identity", lambda *args, **kwargs: _view())
    monkeypatch.setattr(
        service,
        "issue_delegated_execution_grant",
        lambda *args, **kwargs: _grant(
            session="file-secret:///run/secrets/session.json"
        ),
    )
    monkeypatch.setattr(service, "revoke_delegated_identity", lambda *args, **kwargs: None)

    result = service.revoke_delegated_provider_session(
        object(),  # type: ignore[arg-type]
        IDENTITY,
        _request(),
        _Executor(logout_error=True),
        session_store=store,
        now=NOW,
    )

    assert result.local_revoked
    assert result.remote_logout_attempted
    assert not result.remote_logout_completed
    assert store.deletes == [store.reference_for(IDENTITY).value]


def test_session_reference_lookup_returns_none_when_material_is_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _unavailable(*args, **kwargs):
        raise DelegatedReferenceUnavailableError("missing")

    monkeypatch.setattr(service, "issue_delegated_execution_grant", _unavailable)

    assert (
        service._session_reference_if_usable(
            object(),  # type: ignore[arg-type]
            IDENTITY,
            _request(),
            _Store(),
            NOW,
        )
        is None
    )


def test_context_and_required_reference_guards_are_fail_closed() -> None:
    with pytest.raises(service.DelegatedProviderSessionError, match="interactive-session"):
        service._validate_context(
            SOURCE,
            SourceAccountAuthMode.API_KEY,
            _Executor(),
        )

    wrong_source = _Executor()
    wrong_source.source_id = "other-provider"
    with pytest.raises(service.DelegatedProviderSessionError, match="source mismatch"):
        service._validate_context(
            SOURCE,
            SourceAccountAuthMode.INTERACTIVE_SESSION,
            wrong_source,
        )

    with pytest.raises(service.DelegatedProviderSessionError, match="reference is missing"):
        service._required_reference(None, "browser session")
