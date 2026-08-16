from __future__ import annotations

import os
import tempfile
import threading
from datetime import UTC, datetime, timedelta
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs
from uuid import uuid4

from cip.adapters.sources.public_web.delegated_login_orchestrator import (
    establish_delegated_provider_session,
    reuse_delegated_provider_session,
    revoke_delegated_provider_session,
)
from cip.adapters.sources.public_web.delegated_login_runtime import (
    ProviderLoginChallengeError,
)
from cip.modules.provider_onboarding.application.secrets import (
    LocalSecretReferenceResolver,
    LocalSecretValueResolver,
)
from cip.modules.provider_onboarding.domain.browser_login import ProviderLoginChallenge
from cip.modules.provider_onboarding.infrastructure.browser_login_registry import (
    load_provider_login_profiles,
)
from cip.modules.source_governance.application.delegated_identity_contracts import (
    DelegatedIdentityAccessDeniedError,
    DelegatedOperatorContext,
)
from cip.modules.source_governance.application.delegated_identity_service import (
    attach_delegated_secret_reference,
    authorize_delegated_identity,
    delete_delegated_identity,
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
from cip.modules.source_governance.domain.models import (
    AuthorizationStatus,
    DataCategory,
    HttpMethod,
    SourceAuthorization,
    SourcePolicy,
    SourceStatus,
    SourceType,
)
from cip.modules.source_governance.infrastructure.delegated_identity_models import (
    DelegatedBrowserIdentityRecord,
)
from cip.modules.source_governance.infrastructure.local_session_material import (
    LocalFileSessionMaterialStore,
)
from cip.modules.source_governance.infrastructure.models import SourceRecord
from cip.modules.source_governance.infrastructure.registry import SourceRegistryEntry
from cip.shared.persistence.metadata import get_metadata
from cip.shared.persistence.session import create_database_engine, create_session_factory

_SOURCE_ID = "sa16-l16-controlled-provider"
_PURPOSE = "sa16-l16-authorized-login-proof"
_SECRET_REFERENCE = "env://CIP_L16_CONTROLLED_SECRET"
_PROFILE_PATH = Path("tests/fixtures/sa16_l16_login_profiles.yml")
_PORT = 18776
_SESSION_COOKIE = "sa16-l16-controlled-session"


class _FixtureState:
    login_submissions = 0
    private_hits = 0
    logout_hits = 0
    challenge_mode = False


class _Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def do_GET(self) -> None:
        path = self.path.split("?", 1)[0]
        if path == "/login":
            self._login_page()
            return
        if path == "/private":
            self._private_page()
            return
        if path == "/logout":
            _FixtureState.logout_hits += 1
            self._send(
                HTTPStatus.OK,
                "<html><body id='logged-out'>logged out</body></html>",
                headers={
                    "Set-Cookie": "sid=; Max-Age=0; Path=/; HttpOnly; SameSite=Strict"
                },
            )
            return
        self._send(HTTPStatus.NOT_FOUND, "not found")

    def do_POST(self) -> None:
        if self.path.split("?", 1)[0] != "/login":
            self._send(HTTPStatus.NOT_FOUND, "not found")
            return
        _FixtureState.login_submissions += 1
        length = int(self.headers.get("Content-Length", "0"))
        payload = self.rfile.read(length).decode("utf-8")
        values = parse_qs(payload, keep_blank_values=True)
        expected = os.environ.get("CIP_L16_CONTROLLED_SECRET", "")
        username = values.get("username", [""])[0]
        password = values.get("password", [""])[0]
        if username != "controlled-user" or password != expected:
            self._send(HTTPStatus.UNAUTHORIZED, "authentication failed")
            return
        self._send(
            HTTPStatus.SEE_OTHER,
            "authenticated",
            headers={
                "Location": "/private",
                "Set-Cookie": (
                    f"sid={_SESSION_COOKIE}; Path=/; HttpOnly; SameSite=Strict"
                ),
            },
        )

    def log_message(self, _format: str, *args: object) -> None:
        return

    def _login_page(self) -> None:
        challenge = "<div id='mfa'>MFA required</div>" if _FixtureState.challenge_mode else ""
        body = (
            "<html><head><link rel='icon' href='data:,'></head><body>"
            f"{challenge}"
            "<form method='post' action='/login'>"
            "<input id='username' name='username' type='text'>"
            "<input id='password' name='password' type='password'>"
            "<button type='submit'>Login</button>"
            "</form></body></html>"
        )
        self._send(HTTPStatus.OK, body)

    def _private_page(self) -> None:
        cookies = self.headers.get("Cookie", "")
        if f"sid={_SESSION_COOKIE}" not in cookies:
            self._send(HTTPStatus.SEE_OTHER, "login", headers={"Location": "/login"})
            return
        _FixtureState.private_hits += 1
        self._send(
            HTTPStatus.OK,
            "<html><head><link rel='icon' href='data:,'></head>"
            "<body><div id='authenticated'>authorized</div></body></html>",
        )

    def _send(
        self,
        status: HTTPStatus,
        body: str,
        *,
        headers: dict[str, str] | None = None,
    ) -> None:
        payload = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Connection", "close")
        for name, value in (headers or {}).items():
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(payload)


def _source(now: datetime) -> SourceRecord:
    return SourceRecord(
        id=_SOURCE_ID,
        name="SA16 L16 controlled provider",
        base_url=f"http://127.0.0.1:{_PORT}/",
        status="enabled",
        source_type="browser",
        owner="CIP controlled live validation",
        terms_url=None,
        licence="Repository-owned controlled L16 fixture",
        allowed_data_categories=[DataCategory.OFFICIAL_DOCUMENT_DISCOVERY.value],
        prohibited_data_categories=[],
        rate_limit_per_minute=None,
        retention_days=None,
        attribution_required=False,
        raw_content_storage=False,
        human_review_required=False,
        authorization_status="approved",
        authorization_document_reference="SA16-L16-CONTROLLED-AUTH",
        authorization_reviewed_at=now,
        authorization_expires_at=None,
        approved_hosts=["127.0.0.1"],
        approved_path_prefixes=["/"],
        approved_purposes=[_PURPOSE],
        approved_http_methods=["GET", "POST"],
        automated_collection_allowed=True,
        raw_storage_allowed=False,
    )


def _entry(now: datetime) -> SourceRegistryEntry:
    policy = SourcePolicy(
        id=_SOURCE_ID,
        name="SA16 L16 controlled provider",
        base_url=f"http://127.0.0.1:{_PORT}/",
        status=SourceStatus.ENABLED,
        source_type=SourceType.BROWSER,
        owner="CIP controlled live validation",
        licence="Repository-owned controlled L16 fixture",
        allowed_data_categories=frozenset(
            {DataCategory.OFFICIAL_DOCUMENT_DISCOVERY}
        ),
        human_review_required=False,
    )
    authorization = SourceAuthorization(
        status=AuthorizationStatus.APPROVED,
        document_reference="SA16-L16-CONTROLLED-AUTH",
        reviewed_at=now,
        approved_hosts=frozenset({"127.0.0.1"}),
        approved_path_prefixes=("/",),
        approved_purposes=frozenset({_PURPOSE}),
        approved_http_methods=frozenset({HttpMethod.GET, HttpMethod.POST}),
        automated_collection_allowed=True,
    )
    return SourceRegistryEntry(policy, authorization, {})


def _identity(
    now: datetime,
    tenant_id,
    external_reference: str,
) -> DelegatedBrowserIdentity:
    account = SourceAccount(
        source_id=_SOURCE_ID,
        external_reference=external_reference,
        auth_mode=SourceAccountAuthMode.INTERACTIVE_SESSION,
        status=SourceAccountStatus.PENDING_VERIFICATION,
        authorization_document_reference="SA16-L16-CONTROLLED-AUTH",
        approved_purposes=frozenset({_PURPOSE}),
        created_at=now,
        expires_at=now + timedelta(days=30),
    )
    return DelegatedBrowserIdentity(
        account=account,
        tenant_id=tenant_id,
        owner_kind=DelegatedOwnerKind.SERVICE_PRINCIPAL,
        owner_subject_id="sa16-l16-controlled-worker",
        purpose=_PURPOSE,
        approved_scopes=frozenset({"authenticated-page.read"}),
        created_at=now,
    )


def _actor(tenant_id) -> DelegatedOperatorContext:
    return DelegatedOperatorContext(
        tenant_id=tenant_id,
        owner_kind=DelegatedOwnerKind.SERVICE_PRINCIPAL,
        owner_subject_id="sa16-l16-controlled-worker",
    )


def _request(tenant_id) -> DelegatedExecutionRequest:
    return DelegatedExecutionRequest(
        tenant_id=tenant_id,
        owner_kind=DelegatedOwnerKind.SERVICE_PRINCIPAL,
        owner_subject_id="sa16-l16-controlled-worker",
        source_id=_SOURCE_ID,
        purpose=_PURPOSE,
        required_scopes=frozenset({"authenticated-page.read"}),
    )


def _prepare_identity(session, identity: DelegatedBrowserIdentity, actor, resolver) -> None:
    register_delegated_identity(session, identity, actor=actor, now=identity.created_at)
    authorize_delegated_identity(
        session,
        identity.id,
        actor=actor,
        reviewed_at=identity.created_at + timedelta(seconds=1),
    )
    attach_delegated_secret_reference(
        session,
        identity.id,
        _SECRET_REFERENCE,
        actor=actor,
        resolver=resolver,
        now=identity.created_at + timedelta(seconds=2),
    )


def _require_environment() -> None:
    value = os.environ.get("CIP_L16_CONTROLLED_SECRET")
    if value is None or not value.strip():
        raise RuntimeError("controlled L16 secret reference is unavailable")


def main() -> None:
    _require_environment()
    _FixtureState.login_submissions = 0
    _FixtureState.private_hits = 0
    _FixtureState.logout_hits = 0
    _FixtureState.challenge_mode = False
    now = datetime.now(UTC)
    tenant_id = uuid4()
    actor = _actor(tenant_id)
    request = _request(tenant_id)
    profile = load_provider_login_profiles(_PROFILE_PATH)[0]
    entry = _entry(now)
    reference_resolver = LocalSecretReferenceResolver()
    value_resolver = LocalSecretValueResolver()
    engine = create_database_engine("sqlite+pysqlite:///:memory:")
    get_metadata().create_all(engine)
    factory = create_session_factory(engine)
    server = ThreadingHTTPServer(("127.0.0.1", _PORT), _Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with tempfile.TemporaryDirectory(prefix="cip-l16-session-") as root:
            store = LocalFileSessionMaterialStore(Path(root))
            with factory() as session:
                session.add(_source(now))
                session.flush()
                identity = _identity(now, tenant_id, "controlled-user")
                _prepare_identity(session, identity, actor, reference_resolver)
                established = establish_delegated_provider_session(
                    session,
                    identity.id,
                    request,
                    entry,
                    profile,
                    secret_reference_resolver=reference_resolver,
                    secret_value_resolver=value_resolver,
                    session_store=store,
                    now=now + timedelta(seconds=3),
                )
                if not established.session_established or _FixtureState.login_submissions != 1:
                    raise RuntimeError("controlled provider session was not established once")
                session_reference = store.reference_for(identity.id)
                if not store.is_available(session_reference):
                    raise RuntimeError("controlled session material was not persisted")
                record = session.get(DelegatedBrowserIdentityRecord, identity.id)
                if record is None or record.session_reference != session_reference.value:
                    raise RuntimeError("delegated session reference metadata is missing")
                if _SESSION_COOKIE in repr(record) or _SESSION_COOKIE in repr(established):
                    raise RuntimeError("raw session material leaked into ordinary representations")
                reused = reuse_delegated_provider_session(
                    session,
                    identity.id,
                    request,
                    entry,
                    profile,
                    session_store=store,
                    now=now + timedelta(seconds=4),
                )
                if not reused.session_reused or _FixtureState.login_submissions != 1:
                    raise RuntimeError("second job did not reuse the governed session")
                revoked = revoke_delegated_provider_session(
                    session,
                    identity.id,
                    request,
                    entry,
                    profile,
                    session_store=store,
                    now=now + timedelta(seconds=5),
                )
                if not revoked.local_revoked or not revoked.remote_logout_completed:
                    raise RuntimeError("controlled session revocation did not complete")
                if store.is_available(session_reference):
                    raise RuntimeError("revocation retained local session material")
                try:
                    reuse_delegated_provider_session(
                        session,
                        identity.id,
                        request,
                        entry,
                        profile,
                        session_store=store,
                        now=now + timedelta(seconds=6),
                    )
                except DelegatedIdentityAccessDeniedError:
                    pass
                else:
                    raise RuntimeError("revoked identity reused a browser session")
                delete_delegated_identity(
                    session,
                    identity.id,
                    actor=actor,
                    now=now + timedelta(seconds=7),
                )

                challenged = _identity(
                    now + timedelta(seconds=10),
                    tenant_id,
                    "controlled-user",
                )
                _prepare_identity(session, challenged, actor, reference_resolver)
                _FixtureState.challenge_mode = True
                submissions_before = _FixtureState.login_submissions
                try:
                    establish_delegated_provider_session(
                        session,
                        challenged.id,
                        request,
                        entry,
                        profile,
                        secret_reference_resolver=reference_resolver,
                        secret_value_resolver=value_resolver,
                        session_store=store,
                        now=now + timedelta(seconds=13),
                    )
                except ProviderLoginChallengeError as exc:
                    if exc.challenge is not ProviderLoginChallenge.MFA:
                        raise RuntimeError(
                            "unexpected controlled challenge classification"
                        ) from exc
                else:
                    raise RuntimeError("controlled MFA challenge was not stopped")
                if _FixtureState.login_submissions != submissions_before:
                    raise RuntimeError("MFA challenge triggered a credential submission")
                revoke_delegated_identity(
                    session,
                    challenged.id,
                    actor=actor,
                    now=now + timedelta(seconds=14),
                )
                delete_delegated_identity(
                    session,
                    challenged.id,
                    actor=actor,
                    now=now + timedelta(seconds=15),
                )
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

    print(
        "SA-16 L16 controlled login validation passed: "
        f"login_submissions={_FixtureState.login_submissions} "
        f"private_hits={_FixtureState.private_hits} "
        f"logout_hits={_FixtureState.logout_hits} "
        "session_reuse=1 local_revoke=1 remote_logout=1 "
        "revoked_reuse_denied=1 mfa_hard_stop=1 mfa_post_attempts=0",
        flush=True,
    )


if __name__ == "__main__":
    main()
