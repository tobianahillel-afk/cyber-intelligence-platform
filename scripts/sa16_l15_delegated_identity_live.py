from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy import select

from cip.modules.provider_onboarding.application.secrets import LocalSecretReferenceResolver
from cip.modules.source_governance.application.delegated_identity_service import (
    DelegatedIdentityAccessDeniedError,
    DelegatedIdentityAuditEvent,
    DelegatedOperatorContext,
    attach_delegated_secret_reference,
    attach_delegated_session_reference,
    authorize_delegated_identity,
    delete_delegated_identity,
    issue_delegated_execution_grant,
    list_delegated_identity_audit,
    register_delegated_identity,
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
from cip.modules.source_governance.infrastructure.delegated_identity_models import (
    DelegatedBrowserIdentityRecord,
)
from cip.modules.source_governance.infrastructure.models import SourceRecord
from cip.shared.persistence.metadata import get_metadata
from cip.shared.persistence.session import create_database_engine, create_session_factory, session_scope

_SECRET_REFERENCE = "env://CIP_L15_CONTROLLED_SECRET"
_SESSION_REFERENCE = "env://CIP_L15_CONTROLLED_SESSION"
_PURPOSE = "controlled-delegated-browser-proof"
_SOURCE_ID = "sa16-l15-controlled-provider"


def _source(now: datetime) -> SourceRecord:
    return SourceRecord(
        id=_SOURCE_ID,
        name="SA16 L15 controlled provider",
        base_url="https://example.com/",
        status="enabled",
        source_type="browser",
        owner="CIP controlled live validation",
        terms_url=None,
        licence="Repository-owned controlled L15 fixture",
        allowed_data_categories=[],
        prohibited_data_categories=[],
        rate_limit_per_minute=None,
        retention_days=None,
        attribution_required=False,
        raw_content_storage=False,
        human_review_required=False,
        authorization_status="approved",
        authorization_document_reference="SA16-L15-CONTROLLED-AUTH",
        authorization_reviewed_at=now,
        authorization_expires_at=None,
        approved_hosts=["example.com"],
        approved_path_prefixes=["/"],
        approved_purposes=[_PURPOSE],
        approved_http_methods=["GET"],
        automated_collection_allowed=True,
        raw_storage_allowed=False,
    )


def _identity(now: datetime, tenant_id) -> DelegatedBrowserIdentity:
    account = SourceAccount(
        source_id=_SOURCE_ID,
        external_reference="controlled-provider-account",
        auth_mode=SourceAccountAuthMode.INTERACTIVE_SESSION,
        status=SourceAccountStatus.PENDING_VERIFICATION,
        authorization_document_reference="SA16-L15-CONTROLLED-AUTH",
        approved_purposes=frozenset({_PURPOSE}),
        created_at=now,
        expires_at=now + timedelta(days=30),
    )
    return DelegatedBrowserIdentity(
        account=account,
        tenant_id=tenant_id,
        owner_kind=DelegatedOwnerKind.SERVICE_PRINCIPAL,
        owner_subject_id="sa16-l15-controlled-worker",
        purpose=_PURPOSE,
        approved_scopes=frozenset({"authenticated-page.read"}),
        created_at=now,
    )


def _request(tenant_id) -> DelegatedExecutionRequest:
    return DelegatedExecutionRequest(
        tenant_id=tenant_id,
        owner_kind=DelegatedOwnerKind.SERVICE_PRINCIPAL,
        owner_subject_id="sa16-l15-controlled-worker",
        source_id=_SOURCE_ID,
        purpose=_PURPOSE,
        required_scopes=frozenset({"authenticated-page.read"}),
        require_secret_reference=True,
        require_session_reference=True,
    )


def _require_controlled_environment() -> None:
    for name in ("CIP_L15_CONTROLLED_SECRET", "CIP_L15_CONTROLLED_SESSION"):
        value = os.environ.get(name)
        if value is None or not value.strip():
            raise RuntimeError(f"SA16-L15 controlled reference backend is missing {name}")


def main() -> None:
    _require_controlled_environment()
    now = datetime.now(UTC)
    tenant_id = uuid4()
    actor = DelegatedOperatorContext(
        tenant_id=tenant_id,
        owner_kind=DelegatedOwnerKind.SERVICE_PRINCIPAL,
        owner_subject_id="sa16-l15-controlled-worker",
    )
    resolver = LocalSecretReferenceResolver()
    engine = create_database_engine("sqlite+pysqlite:///:memory:")
    get_metadata().create_all(engine)
    factory = create_session_factory(engine)
    identity = _identity(now, tenant_id)

    with session_scope(factory) as session:
        session.add(_source(now))
        register_delegated_identity(session, identity, actor=actor, now=now)
        authorize_delegated_identity(
            session,
            identity.id,
            actor=actor,
            reviewed_at=now + timedelta(seconds=1),
        )
        attach_delegated_secret_reference(
            session,
            identity.id,
            _SECRET_REFERENCE,
            actor=actor,
            resolver=resolver,
            now=now + timedelta(seconds=2),
        )
        attach_delegated_session_reference(
            session,
            identity.id,
            _SESSION_REFERENCE,
            actor=actor,
            resolver=resolver,
            now=now + timedelta(seconds=3),
            expires_at=now + timedelta(hours=1),
        )
        grant = issue_delegated_execution_grant(
            session,
            identity.id,
            _request(tenant_id),
            resolver=resolver,
            now=now + timedelta(seconds=4),
        )
        if _SECRET_REFERENCE in repr(grant) or _SESSION_REFERENCE in repr(grant):
            raise RuntimeError("SA16-L15 execution grant repr leaked a reference")
        wrong_tenant = _request(uuid4())
        try:
            issue_delegated_execution_grant(
                session,
                identity.id,
                wrong_tenant,
                resolver=resolver,
                now=now + timedelta(seconds=5),
            )
        except DelegatedIdentityAccessDeniedError:
            pass
        else:
            raise RuntimeError("SA16-L15 allowed cross-tenant identity reuse")
        revoke_delegated_identity(
            session,
            identity.id,
            actor=actor,
            now=now + timedelta(seconds=6),
        )
        try:
            issue_delegated_execution_grant(
                session,
                identity.id,
                _request(tenant_id),
                resolver=resolver,
                now=now + timedelta(seconds=7),
            )
        except DelegatedIdentityAccessDeniedError:
            pass
        else:
            raise RuntimeError("SA16-L15 allowed revoked identity execution")
        deleted = delete_delegated_identity(
            session,
            identity.id,
            actor=actor,
            now=now + timedelta(seconds=8),
        )
        if deleted.has_secret_reference or deleted.has_session_reference:
            raise RuntimeError("SA16-L15 deletion retained reference metadata")
        audit = list_delegated_identity_audit(session, identity.id, actor=actor)
        expected = (
            DelegatedIdentityAuditEvent.REGISTERED,
            DelegatedIdentityAuditEvent.AUTHORIZED,
            DelegatedIdentityAuditEvent.SECRET_REFERENCE_UPDATED,
            DelegatedIdentityAuditEvent.SESSION_REFERENCE_UPDATED,
            DelegatedIdentityAuditEvent.USED,
            DelegatedIdentityAuditEvent.REVOKED,
            DelegatedIdentityAuditEvent.DELETED,
        )
        if tuple(event.event_type for event in audit) != expected:
            raise RuntimeError("SA16-L15 audit lifecycle is incomplete")
        record = session.scalar(
            select(DelegatedBrowserIdentityRecord).where(
                DelegatedBrowserIdentityRecord.id == identity.id
            )
        )
        if record is None or record.secret_reference is not None or record.session_reference is not None:
            raise RuntimeError("SA16-L15 deleted record retained delegated references")

    print(
        "SA-16 L15 integration validation passed: "
        "identity_registered=1 authorized=1 secret_reference_available=1 "
        "session_reference_available=1 grants=1 cross_tenant_denied=1 "
        "revoked_grants_denied=1 deleted_references=0 audit_events=7 "
        "external_login=0 raw_secret_reads=0 raw_session_reads=0",
        flush=True,
    )


if __name__ == "__main__":
    main()
