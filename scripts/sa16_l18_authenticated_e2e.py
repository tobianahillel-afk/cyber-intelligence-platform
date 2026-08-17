from __future__ import annotations

import os
import secrets
import tempfile
import threading
from datetime import UTC, datetime, timedelta
from http import HTTPStatus
from http.server import ThreadingHTTPServer
from pathlib import Path
from uuid import uuid4

import sa16_l16_authorized_login_live as l16_fixture
from sqlalchemy import select

from cip.adapters.sources.public_web.delegated_authenticated_evidence import (
    build_delegated_authenticated_evidence,
)
from cip.adapters.sources.public_web.delegated_login_orchestrator import (
    establish_delegated_provider_session,
    reuse_delegated_provider_session,
    revoke_delegated_provider_session,
)
from cip.modules.collection_orchestration.infrastructure.repository_completion import (
    insert_observations,
)
from cip.modules.provider_onboarding.application.secrets import (
    LocalSecretReferenceResolver,
    LocalSecretValueResolver,
)
from cip.modules.provider_onboarding.infrastructure.browser_login_registry import (
    load_provider_login_profiles,
)
from cip.modules.raw_observations.infrastructure.models import RawObservationRecord
from cip.modules.source_governance.application.delegated_identity_contracts import (
    DelegatedIdentityAccessDeniedError,
)
from cip.modules.source_governance.application.delegated_identity_service import (
    delete_delegated_identity,
)
from cip.modules.source_governance.infrastructure.delegated_identity_models import (
    DelegatedBrowserIdentityRecord,
)
from cip.modules.source_governance.infrastructure.local_session_material import (
    LocalFileSessionMaterialStore,
)
from cip.shared.persistence.metadata import get_metadata
from cip.shared.persistence.session import create_database_engine, create_session_factory

_STRUCTURED_SECRET = "l18-structured-secret-never-persist"


class _L18Handler(l16_fixture._Handler):
    def _private_page(self) -> None:
        cookies = self.headers.get("Cookie", "")
        if f"sid={l16_fixture._SESSION_COOKIE}" not in cookies:
            self._send(
                HTTPStatus.SEE_OTHER,
                "login",
                headers={"Location": "/login"},
            )
            return
        l16_fixture._FixtureState.private_hits += 1
        body = f"""<html><head><link rel='icon' href='data:,'>
<meta property='og:title' content='Authorized L18 evidence'>
<script type='application/json'>{{
  "name":"Authorized L18 portal",
  "provider":"CIP controlled provider",
  "sessionToken":"{_STRUCTURED_SECRET}",
  "password":"{_STRUCTURED_SECRET}"
}}</script></head><body>
<div id='authenticated'>authorized</div>
<main id='evidence'>governed authenticated evidence</main>
</body></html>"""
        self._send(HTTPStatus.OK, body)


def main() -> None:
    os.environ[l16_fixture._SECRET_ENV] = secrets.token_urlsafe(32)
    _reset_fixture_state()
    now = datetime.now(UTC)
    tenant_id = uuid4()
    actor = l16_fixture._actor(tenant_id)
    request = l16_fixture._request(tenant_id)
    profile = load_provider_login_profiles(l16_fixture._PROFILE_PATH)[0]
    entry = l16_fixture._entry(now)
    reference_resolver = LocalSecretReferenceResolver()
    value_resolver = LocalSecretValueResolver()
    engine = create_database_engine("sqlite+pysqlite:///:memory:")
    get_metadata().create_all(engine)
    factory = create_session_factory(engine)
    server = ThreadingHTTPServer(("127.0.0.1", l16_fixture._PORT), _L18Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with tempfile.TemporaryDirectory(prefix="cip-l18-session-") as root:
            store = LocalFileSessionMaterialStore(Path(root))
            with factory() as session:
                session.add(l16_fixture._source(now))
                session.flush()
                identity = l16_fixture._identity(now, tenant_id, "controlled-user")
                l16_fixture._prepare_identity(session, identity, actor, reference_resolver)
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
                _verify_established(session, store, identity.id, established)
                first_evidence = build_delegated_authenticated_evidence(
                    established,
                    collection_job_id=uuid4(),
                    collected_at=now + timedelta(seconds=3),
                    retention_until=now + timedelta(days=1),
                )
                if not first_evidence.structured_extracted:
                    raise RuntimeError("L18 authenticated structured extraction was empty")
                _assert_no_secret_repr(first_evidence)
                if insert_observations(session, (first_evidence.observation,)) != 1:
                    raise RuntimeError("L18 authenticated evidence was not persisted")
                _verify_observation_record(session, identity.id)

                reused = reuse_delegated_provider_session(
                    session,
                    identity.id,
                    request,
                    entry,
                    profile,
                    session_store=store,
                    now=now + timedelta(seconds=4),
                )
                if not reused.session_reused or l16_fixture._FixtureState.login_submissions != 1:
                    raise RuntimeError("L18 authenticated path did not reuse the governed session")
                replay = build_delegated_authenticated_evidence(
                    reused,
                    collection_job_id=uuid4(),
                    collected_at=now + timedelta(seconds=4),
                    retention_until=now + timedelta(days=1),
                )
                if insert_observations(session, (replay.observation,)) != 0:
                    raise RuntimeError("L18 authenticated replay bypassed observation deduplication")

                session_reference = store.reference_for(identity.id)
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
                    raise RuntimeError("L18 authenticated session revocation did not complete")
                if store.is_available(session_reference):
                    raise RuntimeError("L18 revocation retained session secret material")
                _assert_revoked_reuse_denied(
                    session,
                    identity.id,
                    request,
                    entry,
                    profile,
                    store,
                    now + timedelta(seconds=6),
                )
                delete_delegated_identity(
                    session,
                    identity.id,
                    actor=actor,
                    now=now + timedelta(seconds=7),
                )
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
        os.environ.pop(l16_fixture._SECRET_ENV, None)

    print(
        "SA-16 L18 authenticated composite passed: tenant_service_principal=1 "
        "delegated_identity=1 secret_reference=1 governed_login=1 rendered_structured=1 "
        "raw_observation=1 raw_body_retained=0 session_reuse=1 replay_dedup=1 "
        "remote_logout=1 local_revoke=1 revoked_reuse_denied=1 secret_leaks=0",
        flush=True,
    )


def _reset_fixture_state() -> None:
    l16_fixture._FixtureState.login_submissions = 0
    l16_fixture._FixtureState.private_hits = 0
    l16_fixture._FixtureState.logout_hits = 0
    l16_fixture._FixtureState.challenge_mode = False


def _verify_established(session, store, identity_id, established) -> None:
    if not established.session_established or l16_fixture._FixtureState.login_submissions != 1:
        raise RuntimeError("L18 governed provider login was not established exactly once")
    reference = store.reference_for(identity_id)
    if not store.is_available(reference):
        raise RuntimeError("L18 governed session material was not stored")
    record = session.get(DelegatedBrowserIdentityRecord, identity_id)
    if record is None or record.session_reference != reference.value:
        raise RuntimeError("L18 delegated session reference metadata is missing")
    if l16_fixture._SESSION_COOKIE in repr(record) or l16_fixture._SESSION_COOKIE in repr(established):
        raise RuntimeError("L18 raw session material leaked into ordinary representations")


def _assert_no_secret_repr(evidence) -> None:
    rendered = repr(evidence)
    if _STRUCTURED_SECRET in rendered or l16_fixture._SESSION_COOKIE in rendered:
        raise RuntimeError("L18 authenticated evidence representation leaked secret material")


def _verify_observation_record(session, identity_id) -> None:
    record = session.scalar(select(RawObservationRecord))
    if record is None or record.source_record_type != "authenticated_web_page":
        raise RuntimeError("L18 canonical authenticated observation is missing")
    if str(identity_id) not in (record.source_record_key or ""):
        raise RuntimeError("L18 authenticated observation lost delegated identity provenance")
    if record.payload_reference is not None:
        raise RuntimeError("L18 authenticated observation retained raw page content")
    serialized = str(record.__dict__)
    if _STRUCTURED_SECRET in serialized or l16_fixture._SESSION_COOKIE in serialized:
        raise RuntimeError("L18 authenticated database record leaked secret material")


def _assert_revoked_reuse_denied(session, identity_id, request, entry, profile, store, now) -> None:
    try:
        reuse_delegated_provider_session(
            session,
            identity_id,
            request,
            entry,
            profile,
            session_store=store,
            now=now,
        )
    except DelegatedIdentityAccessDeniedError:
        return
    raise RuntimeError("L18 revoked identity reused a governed browser session")


if __name__ == "__main__":
    main()
