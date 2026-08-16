from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest

from cip.adapters.sources.public_web import delegated_login_orchestrator as orchestrator
from cip.adapters.sources.public_web.delegated_login_runtime import (
    ProviderAuthenticatedRuntimeResult,
    ProviderLoginChallengeError,
)
from cip.modules.provider_onboarding.domain.browser_login import (
    ProviderLoginChallenge,
    ProviderLoginHttpMethod,
    ProviderLoginProfile,
    ProviderLoginTransitionRule,
)
from cip.modules.provider_onboarding.domain.models import SecretReference
from cip.modules.source_governance.application.delegated_identity_contracts import (
    DelegatedIdentityAccessDeniedError,
    DelegatedOperatorContext,
)
from cip.modules.source_governance.application.delegated_identity_service import (
    attach_delegated_secret_reference,
    authorize_delegated_identity,
    get_delegated_identity,
    issue_delegated_execution_grant,
    register_delegated_identity,
)
from cip.modules.source_governance.domain.accounts import (
    SourceAccount,
    SourceAccountAuthMode,
    SourceAccountStatus,
)
from cip.modules.source_governance.domain.delegated_browser_identity import (
    DelegatedBrowserIdentity,
    DelegatedExecutionRequest,
    DelegatedOwnerKind,
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
from cip.modules.source_governance.infrastructure.local_session_material import (
    LocalFileSessionMaterialStore,
)
from cip.modules.source_governance.infrastructure.models import SourceRecord
from cip.modules.source_governance.infrastructure.registry import SourceRegistryEntry
from cip.shared.persistence.metadata import get_metadata
from cip.shared.persistence.session import create_database_engine, create_session_factory

NOW = datetime(2026, 8, 17, 1, 0, tzinfo=UTC)
SOURCE = "controlled-provider"
PURPOSE = "authenticated-provider-research"
SECRET_REFERENCE = "env://CIP_L16_TEST_SECRET"
TENANT = uuid4()


class _ReferenceResolver:
    def is_available(self, _reference: SecretReference) -> bool:
        return True


class _ValueResolver:
    def resolve(self, _reference: SecretReference) -> str:
        return "controlled-password-value"


def _profile() -> ProviderLoginProfile:
    return ProviderLoginProfile(
        id="controlled-login-v1",
        source_id=SOURCE,
        login_url="https://provider.example/login",
        username_selector="#username",
        secret_selector="#password",
        submit_selector="button[type=submit]",
        success_selector="#authenticated",
        authenticated_probe_url="https://provider.example/private",
        logout_url="https://provider.example/logout",
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
        session_ttl_seconds=3600,
    )


def _entry() -> SourceRegistryEntry:
    return SourceRegistryEntry(
        policy=SourcePolicy(
            id=SOURCE,
            name="Controlled provider",
            base_url="https://provider.example/",
            status=SourceStatus.ENABLED,
            source_type=SourceType.BROWSER,
            owner="CIP tests",
            licence="Controlled L16 fixture",
            allowed_data_categories=frozenset(
                {DataCategory.OFFICIAL_DOCUMENT_DISCOVERY}
            ),
            human_review_required=False,
        ),
        authorization=SourceAuthorization(
            status=AuthorizationStatus.APPROVED,
            document_reference="AUTH-L16-CONTROLLED",
            reviewed_at=NOW,
            approved_hosts=frozenset({"provider.example"}),
            approved_path_prefixes=("/",),
            approved_purposes=frozenset({PURPOSE}),
            approved_http_methods=frozenset({HttpMethod.GET, HttpMethod.POST}),
            automated_collection_allowed=True,
        ),
        economics={},
    )


def _source_record() -> SourceRecord:
    return SourceRecord(
        id=SOURCE,
        name="Controlled provider",
        base_url="https://provider.example/",
        status="enabled",
        source_type="browser",
        owner="CIP tests",
        terms_url=None,
        licence="Controlled L16 fixture",
        allowed_data_categories=[DataCategory.OFFICIAL_DOCUMENT_DISCOVERY.value],
        prohibited_data_categories=[],
        rate_limit_per_minute=None,
        retention_days=None,
        attribution_required=False,
        raw_content_storage=False,
        human_review_required=False,
        authorization_status="approved",
        authorization_document_reference="AUTH-L16-CONTROLLED",
        authorization_reviewed_at=NOW,
        authorization_expires_at=None,
        approved_hosts=["provider.example"],
        approved_path_prefixes=["/"],
        approved_purposes=[PURPOSE],
        approved_http_methods=["GET", "POST"],
        automated_collection_allowed=True,
        raw_storage_allowed=False,
    )


def _identity() -> DelegatedBrowserIdentity:
    account = SourceAccount(
        source_id=SOURCE,
        external_reference="controlled-user",
        auth_mode=SourceAccountAuthMode.INTERACTIVE_SESSION,
        status=SourceAccountStatus.PENDING_VERIFICATION,
        authorization_document_reference="AUTH-L16-CONTROLLED",
        approved_purposes=frozenset({PURPOSE}),
        created_at=NOW,
        expires_at=NOW + timedelta(days=30),
    )
    return DelegatedBrowserIdentity(
        account=account,
        tenant_id=TENANT,
        owner_kind=DelegatedOwnerKind.SERVICE_PRINCIPAL,
        owner_subject_id="l16-worker",
        purpose=PURPOSE,
        approved_scopes=frozenset({"authenticated-page.read"}),
        created_at=NOW,
    )


def _actor() -> DelegatedOperatorContext:
    return DelegatedOperatorContext(
        TENANT,
        DelegatedOwnerKind.SERVICE_PRINCIPAL,
        "l16-worker",
    )


def _request() -> DelegatedExecutionRequest:
    return DelegatedExecutionRequest(
        tenant_id=TENANT,
        owner_kind=DelegatedOwnerKind.SERVICE_PRINCIPAL,
        owner_subject_id="l16-worker",
        source_id=SOURCE,
        purpose=PURPOSE,
        required_scopes=frozenset({"authenticated-page.read"}),
    )


def _factory():
    engine = create_database_engine("sqlite+pysqlite:///:memory:")
    get_metadata().create_all(engine)
    return create_session_factory(engine)


def _prepare(session) -> DelegatedBrowserIdentity:
    identity = _identity()
    session.add(_source_record())
    session.flush()
    register_delegated_identity(session, identity, actor=_actor(), now=NOW)
    authorize_delegated_identity(
        session,
        identity.id,
        actor=_actor(),
        reviewed_at=NOW + timedelta(seconds=1),
    )
    attach_delegated_secret_reference(
        session,
        identity.id,
        SECRET_REFERENCE,
        actor=_actor(),
        resolver=_ReferenceResolver(),
        now=NOW + timedelta(seconds=2),
    )
    return identity


def _runtime_result(session_value: str) -> ProviderAuthenticatedRuntimeResult:
    return ProviderAuthenticatedRuntimeResult(
        final_url="https://provider.example/private",
        html=b"<div id='authenticated'>ok</div>",
        session_state_json=json.dumps(
            {
                "cookies": [
                    {"name": "sid", "value": session_value, "domain": "provider.example"}
                ],
                "origins": [],
            }
        ),
        requests_seen=3,
        redirects_seen=1,
    )


def test_login_reuse_and_revoke_session_lifecycle(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    factory = _factory()
    store = LocalFileSessionMaterialStore(tmp_path)
    with factory() as session:
        identity = _prepare(session)
        monkeypatch.setattr(
            orchestrator,
            "execute_reviewed_provider_login",
            lambda *args, **kwargs: _runtime_result("session-v1"),
        )
        established = orchestrator.establish_delegated_provider_session(
            session,
            identity.id,
            _request(),
            _entry(),
            _profile(),
            secret_reference_resolver=_ReferenceResolver(),
            secret_value_resolver=_ValueResolver(),
            session_store=store,
            now=NOW + timedelta(seconds=3),
        )
        assert established.session_established
        assert "controlled-password-value" not in repr(established)
        view = get_delegated_identity(session, identity.id, actor=_actor())
        assert view.has_session_reference
        reference = store.reference_for(identity.id)
        assert "session-v1" in store.resolve(reference)

        monkeypatch.setattr(
            orchestrator,
            "execute_reviewed_session_reuse",
            lambda *args, **kwargs: _runtime_result("session-v2"),
        )
        reused = orchestrator.reuse_delegated_provider_session(
            session,
            identity.id,
            _request(),
            _entry(),
            _profile(),
            session_store=store,
            now=NOW + timedelta(seconds=4),
        )
        assert reused.session_reused
        assert "session-v2" in store.resolve(reference)

        monkeypatch.setattr(
            orchestrator,
            "execute_reviewed_provider_logout",
            lambda *args, **kwargs: True,
        )
        revoked = orchestrator.revoke_delegated_provider_session(
            session,
            identity.id,
            _request(),
            _entry(),
            _profile(),
            session_store=store,
            now=NOW + timedelta(seconds=5),
        )
        assert revoked.local_revoked
        assert revoked.remote_logout_completed
        assert not store.is_available(reference)

        with pytest.raises(DelegatedIdentityAccessDeniedError):
            issue_delegated_execution_grant(
                session,
                identity.id,
                _request(),
                resolver=store,
                now=NOW + timedelta(seconds=6),
            )


def test_login_challenge_does_not_create_session_material(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    factory = _factory()
    store = LocalFileSessionMaterialStore(tmp_path)
    with factory() as session:
        identity = _prepare(session)

        def _challenge(*args, **kwargs):
            raise ProviderLoginChallengeError(ProviderLoginChallenge.MFA)

        monkeypatch.setattr(orchestrator, "execute_reviewed_provider_login", _challenge)
        with pytest.raises(ProviderLoginChallengeError):
            orchestrator.establish_delegated_provider_session(
                session,
                identity.id,
                _request(),
                _entry(),
                _profile(),
                secret_reference_resolver=_ReferenceResolver(),
                secret_value_resolver=_ValueResolver(),
                session_store=store,
                now=NOW + timedelta(seconds=3),
            )
        assert not store.is_available(store.reference_for(identity.id))
