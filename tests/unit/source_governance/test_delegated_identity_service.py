from __future__ import annotations

from dataclasses import asdict
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from cip.modules.provider_onboarding.domain.models import SecretReference
from cip.modules.source_governance.application.delegated_identity_service import (
    DelegatedIdentityAccessDeniedError,
    DelegatedIdentityAuditEvent,
    DelegatedIdentityNotFoundError,
    DelegatedOperatorContext,
    DelegatedReferenceUnavailableError,
    attach_delegated_secret_reference,
    attach_delegated_session_reference,
    authorize_delegated_identity,
    delete_delegated_identity,
    get_delegated_identity,
    issue_delegated_execution_grant,
    list_delegated_identities,
    list_delegated_identity_audit,
    register_delegated_identity,
    renew_delegated_identity,
    revoke_delegated_identity,
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
from cip.modules.source_governance.infrastructure.models import SourceRecord
from cip.shared.persistence.metadata import get_metadata
from cip.shared.persistence.session import create_database_engine, create_session_factory

NOW = datetime(2026, 8, 16, 21, 0, tzinfo=UTC)
TENANT = uuid4()
SECRET = "vault://cip/provider/login"
SESSION = "vault://cip/provider/session"


class _Resolver:
    def __init__(self, available: set[str]) -> None:
        self.available = available
        self.seen: list[str] = []

    def is_available(self, reference: SecretReference) -> bool:
        self.seen.append(reference.redacted)
        return reference.value in self.available


def _factory():
    engine = create_database_engine("sqlite+pysqlite:///:memory:")
    get_metadata().create_all(engine)
    factory = create_session_factory(engine)
    with factory() as session:
        session.add(
            SourceRecord(
                id="provider-browser",
                name="Provider Browser",
                base_url="https://example.com/",
                status="enabled",
                source_type="browser",
                owner="tests",
                terms_url=None,
                licence="controlled fixture",
                allowed_data_categories=[],
                prohibited_data_categories=[],
                rate_limit_per_minute=None,
                retention_days=None,
                attribution_required=False,
                raw_content_storage=False,
                human_review_required=False,
                authorization_status="approved",
                authorization_document_reference="AUTH-L15-1",
                authorization_reviewed_at=NOW,
                authorization_expires_at=None,
                approved_hosts=["example.com"],
                approved_path_prefixes=["/"],
                approved_purposes=["authorized-provider-research"],
                approved_http_methods=["GET"],
                automated_collection_allowed=True,
                raw_storage_allowed=False,
            )
        )
        session.commit()
    return factory


def _identity(
    *,
    tenant_id=TENANT,
    owner_kind: DelegatedOwnerKind = DelegatedOwnerKind.USER,
    owner_subject_id: str = "user-123",
) -> DelegatedBrowserIdentity:
    account = SourceAccount(
        source_id="provider-browser",
        external_reference="provider-account-1",
        auth_mode=SourceAccountAuthMode.INTERACTIVE_SESSION,
        status=SourceAccountStatus.PENDING_VERIFICATION,
        authorization_document_reference="AUTH-L15-1",
        approved_purposes=frozenset({"authorized-provider-research"}),
        created_at=NOW,
        expires_at=NOW + timedelta(days=30),
    )
    return DelegatedBrowserIdentity(
        account=account,
        tenant_id=tenant_id,
        owner_kind=owner_kind,
        owner_subject_id=owner_subject_id,
        purpose="authorized-provider-research",
        approved_scopes=frozenset({"profile.read", "company.read"}),
        created_at=NOW,
    )


def _actor(
    *,
    tenant_id=TENANT,
    owner_kind: DelegatedOwnerKind = DelegatedOwnerKind.USER,
    owner_subject_id: str = "user-123",
) -> DelegatedOperatorContext:
    return DelegatedOperatorContext(tenant_id, owner_kind, owner_subject_id)


def _request(**changes: object) -> DelegatedExecutionRequest:
    values: dict[str, object] = {
        "tenant_id": TENANT,
        "owner_kind": DelegatedOwnerKind.USER,
        "owner_subject_id": "user-123",
        "source_id": "provider-browser",
        "purpose": "authorized-provider-research",
        "required_scopes": frozenset({"profile.read"}),
        "require_secret_reference": True,
        "require_session_reference": True,
    }
    values.update(changes)
    return DelegatedExecutionRequest(**values)  # type: ignore[arg-type]


def _register_and_authorize(session):
    identity = _identity()
    actor = _actor()
    register_delegated_identity(session, identity, actor=actor, now=NOW)
    authorize_delegated_identity(
        session,
        identity.id,
        actor=actor,
        reviewed_at=NOW + timedelta(minutes=1),
    )
    return identity, actor


def test_register_read_and_list_return_reference_safe_views() -> None:
    factory = _factory()
    identity = _identity()
    actor = _actor()
    with factory() as session:
        view = register_delegated_identity(session, identity, actor=actor, now=NOW)
        session.commit()
        loaded = get_delegated_identity(session, identity.id, actor=actor)
        listed = list_delegated_identities(session, actor=actor)

    assert view == loaded == listed[0]
    assert view.has_secret_reference is False
    assert view.has_session_reference is False
    serialized = asdict(view)
    assert "secret_reference" not in serialized
    assert "session_reference" not in serialized


def test_operator_reads_are_tenant_and_owner_isolated() -> None:
    factory = _factory()
    identity = _identity()
    with factory() as session:
        register_delegated_identity(session, identity, actor=_actor(), now=NOW)
        session.commit()
        assert list_delegated_identities(session, actor=_actor(tenant_id=uuid4())) == ()
        with pytest.raises(DelegatedIdentityAccessDeniedError, match="owner mismatch"):
            get_delegated_identity(session, identity.id, actor=_actor(owner_subject_id="other"))


def test_lifecycle_validates_references_and_issues_redacted_grant() -> None:
    factory = _factory()
    resolver = _Resolver({SECRET, SESSION})
    with factory() as session:
        identity, actor = _register_and_authorize(session)
        secret_view = attach_delegated_secret_reference(
            session,
            identity.id,
            SECRET,
            actor=actor,
            resolver=resolver,
            now=NOW + timedelta(minutes=2),
        )
        session_view = attach_delegated_session_reference(
            session,
            identity.id,
            SESSION,
            actor=actor,
            resolver=resolver,
            now=NOW + timedelta(minutes=3),
            expires_at=NOW + timedelta(hours=1),
        )
        grant = issue_delegated_execution_grant(
            session,
            identity.id,
            _request(),
            resolver=resolver,
            now=NOW + timedelta(minutes=4),
        )
        session.commit()
        loaded = get_delegated_identity(session, identity.id, actor=actor)

    assert secret_view.reference_version == 1
    assert session_view.reference_version == 2
    assert loaded.last_used_at == NOW + timedelta(minutes=4)
    assert grant.secret_reference == SECRET
    assert grant.session_reference == SESSION
    rendered = repr(grant)
    assert SECRET not in rendered
    assert SESSION not in rendered
    assert "has_secret_reference=True" in rendered
    assert resolver.seen and set(resolver.seen) == {"vault://***"}


def test_unavailable_and_invalid_references_fail_before_persistence() -> None:
    factory = _factory()
    resolver = _Resolver(set())
    with factory() as session:
        identity, actor = _register_and_authorize(session)
        with pytest.raises(DelegatedReferenceUnavailableError, match="unavailable"):
            attach_delegated_secret_reference(
                session,
                identity.id,
                SECRET,
                actor=actor,
                resolver=resolver,
                now=NOW + timedelta(minutes=2),
            )
        with pytest.raises(ValueError, match="scheme"):
            attach_delegated_session_reference(
                session,
                identity.id,
                "https://not-a-secret-reference.example/session",
                actor=actor,
                resolver=resolver,
                now=NOW + timedelta(minutes=3),
            )
        view = get_delegated_identity(session, identity.id, actor=actor)
        assert view.has_secret_reference is False
        assert view.has_session_reference is False


def test_execution_grant_checks_scope_and_reference_availability() -> None:
    factory = _factory()
    resolver = _Resolver({SECRET, SESSION})
    with factory() as session:
        identity, actor = _register_and_authorize(session)
        attach_delegated_secret_reference(
            session,
            identity.id,
            SECRET,
            actor=actor,
            resolver=resolver,
            now=NOW + timedelta(minutes=2),
        )
        attach_delegated_session_reference(
            session,
            identity.id,
            SESSION,
            actor=actor,
            resolver=resolver,
            now=NOW + timedelta(minutes=3),
        )
        with pytest.raises(DelegatedIdentityAccessDeniedError, match="tenant_mismatch"):
            issue_delegated_execution_grant(
                session,
                identity.id,
                _request(tenant_id=uuid4()),
                resolver=resolver,
                now=NOW + timedelta(minutes=4),
            )
        with pytest.raises(DelegatedIdentityAccessDeniedError, match="scope_mismatch"):
            issue_delegated_execution_grant(
                session,
                identity.id,
                _request(required_scopes=frozenset({"admin.write"})),
                resolver=resolver,
                now=NOW + timedelta(minutes=4),
            )
        unavailable = _Resolver({SECRET})
        with pytest.raises(DelegatedReferenceUnavailableError, match="unavailable"):
            issue_delegated_execution_grant(
                session,
                identity.id,
                _request(),
                resolver=unavailable,
                now=NOW + timedelta(minutes=4),
            )


def test_renew_revoke_delete_and_audit_are_terminal_and_reference_safe() -> None:
    factory = _factory()
    resolver = _Resolver({SECRET, SESSION})
    with factory() as session:
        identity, actor = _register_and_authorize(session)
        attach_delegated_secret_reference(
            session,
            identity.id,
            SECRET,
            actor=actor,
            resolver=resolver,
            now=NOW + timedelta(minutes=2),
        )
        attach_delegated_session_reference(
            session,
            identity.id,
            SESSION,
            actor=actor,
            resolver=resolver,
            now=NOW + timedelta(minutes=3),
        )
        renewed = renew_delegated_identity(
            session,
            identity.id,
            actor=actor,
            expires_at=NOW + timedelta(days=60),
            now=NOW + timedelta(days=20),
        )
        assert renewed.renewed_at == NOW + timedelta(days=20)
        revoked = revoke_delegated_identity(
            session,
            identity.id,
            actor=actor,
            now=NOW + timedelta(days=21),
        )
        assert revoked.status is SourceAccountStatus.REVOKED
        with pytest.raises(DelegatedIdentityAccessDeniedError, match="revoked"):
            issue_delegated_execution_grant(
                session,
                identity.id,
                _request(),
                resolver=resolver,
                now=NOW + timedelta(days=21, minutes=1),
            )
        deleted = delete_delegated_identity(
            session,
            identity.id,
            actor=actor,
            now=NOW + timedelta(days=22),
        )
        assert deleted.deleted_at is not None
        assert deleted.has_secret_reference is False
        assert deleted.has_session_reference is False
        audit = list_delegated_identity_audit(session, identity.id, actor=actor)
        session.commit()

    assert [event.event_type for event in audit] == [
        DelegatedIdentityAuditEvent.REGISTERED,
        DelegatedIdentityAuditEvent.AUTHORIZED,
        DelegatedIdentityAuditEvent.SECRET_REFERENCE_UPDATED,
        DelegatedIdentityAuditEvent.SESSION_REFERENCE_UPDATED,
        DelegatedIdentityAuditEvent.RENEWED,
        DelegatedIdentityAuditEvent.REVOKED,
        DelegatedIdentityAuditEvent.DELETED,
    ]
    rendered = repr(audit)
    assert SECRET not in rendered
    assert SESSION not in rendered


def test_missing_identity_and_duplicate_registration_fail_closed() -> None:
    factory = _factory()
    identity = _identity()
    actor = _actor()
    with factory() as session:
        with pytest.raises(DelegatedIdentityNotFoundError):
            get_delegated_identity(session, uuid4(), actor=actor)
        register_delegated_identity(session, identity, actor=actor, now=NOW)
        with pytest.raises(ValueError, match="already exists"):
            register_delegated_identity(session, identity, actor=actor, now=NOW)


def test_service_principal_owner_is_supported_without_cross_owner_reuse() -> None:
    factory = _factory()
    identity = _identity(
        owner_kind=DelegatedOwnerKind.SERVICE_PRINCIPAL,
        owner_subject_id="spn-cip-worker",
    )
    actor = _actor(
        owner_kind=DelegatedOwnerKind.SERVICE_PRINCIPAL,
        owner_subject_id="spn-cip-worker",
    )
    with factory() as session:
        view = register_delegated_identity(session, identity, actor=actor, now=NOW)
        assert view.owner_kind is DelegatedOwnerKind.SERVICE_PRINCIPAL
        with pytest.raises(DelegatedIdentityAccessDeniedError):
            get_delegated_identity(session, identity.id, actor=_actor())
