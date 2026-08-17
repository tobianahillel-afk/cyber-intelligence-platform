from __future__ import annotations

import tempfile
import threading
from datetime import UTC, datetime, timedelta
from http import HTTPStatus
from pathlib import Path
from uuid import uuid4

import httpx
from playwright.sync_api import sync_playwright
from sa16_l17_controlled_oauth_fixture import (
    ACCESS_TOKEN,
    AUTH_CODE,
    BASE,
    FixtureState,
    create_server,
    reset_fixture,
)
from sa16_l17_live_domain_setup import (
    PROFILE_PATH,
    PURPOSE,
    checkpoint_context,
    collection_job,
    delegated_identity,
    execution_request,
    operator_context,
    source_entry,
    source_record,
)
from sqlalchemy import select

from cip.adapters.sources.public_web.collection_policy import authorize_public_web_url
from cip.adapters.sources.public_web.federated_checkpoint_flow import (
    FederatedCheckpointCompletion,
    FederatedCheckpointStart,
    begin_delegated_federated_checkpoint,
    complete_delegated_federated_checkpoint,
    resolve_federated_token_for_job,
)
from cip.modules.collection_orchestration.application.ports import AdapterCollectionBatch
from cip.modules.collection_orchestration.domain.models import JobStatus
from cip.modules.collection_orchestration.infrastructure.models import (
    CollectionHumanCheckpointEventRecord,
    CollectionHumanCheckpointRecord,
    CollectionJobRecord,
)
from cip.modules.collection_orchestration.infrastructure.repository import (
    claim_next_job,
    complete_job,
    enqueue_job,
    pause_claimed_job_for_human,
    resume_human_checkpoint,
)
from cip.modules.provider_onboarding.application.secrets import LocalSecretReferenceResolver
from cip.modules.provider_onboarding.infrastructure.browser_login_registry import (
    load_provider_federated_auth_profiles,
)
from cip.modules.provider_onboarding.infrastructure.local_federated_material import (
    LocalFederatedContinuationMaterialStore,
)
from cip.modules.source_governance.application.delegated_identity_contracts import (
    DelegatedIdentityAccessDeniedError,
)
from cip.modules.source_governance.application.delegated_identity_service import (
    authorize_delegated_identity,
    delete_delegated_identity,
    register_delegated_identity,
    revoke_delegated_identity,
)
from cip.modules.source_governance.domain.models import HttpMethod
from cip.modules.source_governance.infrastructure.delegated_identity_models import (
    DelegatedBrowserIdentityRecord,
)
from cip.shared.persistence.metadata import get_metadata
from cip.shared.persistence.session import create_database_engine, create_session_factory


def _approve_in_browser(authorization_url: str) -> str:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(authorization_url, wait_until="domcontentloaded")
        page.locator("#approve").click()
        page.wait_for_selector("#oauth-complete")
        callback_url = page.url
        browser.close()
    return callback_url


def _assert_fixture_counts() -> None:
    if (
        FixtureState.approvals != 1
        or FixtureState.token_posts != 1
        or FixtureState.private_hits != 1
        or not FixtureState.code_consumed
    ):
        raise RuntimeError("controlled OAuth fixture counters are inconsistent")


def main() -> None:
    reset_fixture()
    now = datetime.now(UTC)
    tenant_id = uuid4()
    actor = operator_context(tenant_id)
    request = execution_request(tenant_id)
    profile = load_provider_federated_auth_profiles(PROFILE_PATH)[0]
    entry = source_entry(now)
    resolver = LocalSecretReferenceResolver()
    server = create_server()
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with tempfile.TemporaryDirectory(prefix="cip-l17-") as root:
            root_path = Path(root)
            engine = create_database_engine(
                f"sqlite+pysqlite:///{root_path / 'l17.sqlite'}"
            )
            get_metadata().create_all(engine)
            factory = create_session_factory(engine)
            store = LocalFederatedContinuationMaterialStore(root_path / "secrets")
            identity = delegated_identity(now, tenant_id)

            with factory.begin() as session:
                session.add(source_record(now))
                session.flush()
                register_delegated_identity(
                    session,
                    identity,
                    actor=actor,
                    now=now,
                )
                authorize_delegated_identity(
                    session,
                    identity.id,
                    actor=actor,
                    reviewed_at=now + timedelta(seconds=1),
                )
                if not enqueue_job(session, collection_job(now + timedelta(seconds=2))):
                    raise RuntimeError("controlled L17 job was not enqueued")

            with factory.begin() as session:
                claimed = claim_next_job(
                    session,
                    worker_id="l17-worker-before-checkpoint",
                    now=now + timedelta(seconds=2),
                )
                if claimed is None:
                    raise RuntimeError("controlled L17 job was not claimed")
                original_attempt = claimed.attempt
                started: FederatedCheckpointStart = begin_delegated_federated_checkpoint(
                    session,
                    checkpoint_context(identity.id, claimed.id, request),
                    entry,
                    profile,
                    identity_reference_resolver=resolver,
                    material_store=store,
                    now=now + timedelta(seconds=3),
                )
                pause_claimed_job_for_human(
                    session,
                    claimed,
                    started.checkpoint,
                    now=now + timedelta(seconds=3),
                )
                job_id = claimed.id

            callback_url = _approve_in_browser(started.authorization_url)
            with factory.begin() as session, httpx.Client() as client:
                completion = complete_delegated_federated_checkpoint(
                    session,
                    checkpoint_context(identity.id, job_id, request),
                    entry,
                    profile,
                    FederatedCheckpointCompletion(
                        checkpoint_id=started.checkpoint.id,
                        callback_url=callback_url,
                        correlation_token=started.correlation_token,
                        actor_reference="user:controlled-oauth-approver",
                        completed_at=now + timedelta(seconds=5),
                    ),
                    identity_reference_resolver=resolver,
                    material_store=store,
                    client=client,
                    resume_checkpoint=resume_human_checkpoint,
                )
                if completion.job_id != job_id:
                    raise RuntimeError("OAuth completion changed the collection job id")

            with factory.begin() as session, httpx.Client() as client:
                resumed = claim_next_job(
                    session,
                    worker_id="l17-worker-after-restart",
                    now=now + timedelta(seconds=6),
                )
                if resumed is None or resumed.id != job_id:
                    raise RuntimeError("same L17 job was not reclaimed after restart")
                if resumed.attempt != original_attempt:
                    raise RuntimeError("human resume consumed a retry attempt")
                context = checkpoint_context(identity.id, resumed.id, request)
                token = resolve_federated_token_for_job(
                    session,
                    context,
                    profile,
                    material_store=store,
                    now=now + timedelta(seconds=6),
                )
                private_url = f"{BASE}/private"
                authorize_public_web_url(
                    entry,
                    private_url,
                    now=now + timedelta(seconds=6),
                    http_method=HttpMethod.GET,
                    purpose=PURPOSE,
                )
                response = client.get(
                    private_url,
                    headers={"Authorization": f"Bearer {token.access_token}"},
                    follow_redirects=False,
                )
                if response.status_code != HTTPStatus.OK:
                    raise RuntimeError("controlled authenticated retrieval failed")
                complete_job(
                    session,
                    resumed,
                    AdapterCollectionBatch(
                        observations=(),
                        checkpoint_payload={"oauth_completed": True},
                        not_modified=True,
                    ),
                    now=now + timedelta(seconds=7),
                )

            reference = store.reference_for(identity.id, started.checkpoint.id)
            secret_payload = store.resolve(reference)
            with factory.begin() as session:
                checkpoint = session.get(
                    CollectionHumanCheckpointRecord,
                    started.checkpoint.id,
                )
                job = session.get(CollectionJobRecord, job_id)
                identity_record = session.get(DelegatedBrowserIdentityRecord, identity.id)
                events = session.scalars(
                    select(CollectionHumanCheckpointEventRecord).where(
                        CollectionHumanCheckpointEventRecord.checkpoint_id
                        == started.checkpoint.id
                    )
                ).all()
                if checkpoint is None or checkpoint.state != "completed":
                    raise RuntimeError("durable human checkpoint did not complete")
                if job is None or job.status != JobStatus.NOT_MODIFIED.value:
                    raise RuntimeError("resumed L17 job did not reach terminal success")
                if identity_record is None or identity_record.session_reference != reference.value:
                    raise RuntimeError("federated session reference metadata is missing")
                event_state = [
                    (event.event_type, event.actor_reference, event.reason)
                    for event in events
                ]
                public_state = repr(
                    (
                        checkpoint.correlation_digest,
                        checkpoint.session_reference,
                        event_state,
                        identity_record.session_reference,
                    )
                )
                for secret in (started.correlation_token, ACCESS_TOKEN, AUTH_CODE):
                    if secret in public_state:
                        raise RuntimeError("secret leaked into durable/audit representation")
                if ACCESS_TOKEN not in secret_payload:
                    raise RuntimeError("token-ready material was not retained securely")
                revoke_delegated_identity(
                    session,
                    identity.id,
                    actor=actor,
                    now=now + timedelta(seconds=8),
                )
                try:
                    resolve_federated_token_for_job(
                        session,
                        checkpoint_context(identity.id, job_id, request),
                        profile,
                        material_store=store,
                        now=now + timedelta(seconds=9),
                    )
                except DelegatedIdentityAccessDeniedError:
                    pass
                else:
                    raise RuntimeError("revoked identity still resolved federated token")
                store.delete(reference)
                delete_delegated_identity(
                    session,
                    identity.id,
                    actor=actor,
                    now=now + timedelta(seconds=10),
                )
            if store.is_available(reference):
                raise RuntimeError("deleted federated material remained available")
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

    _assert_fixture_counts()
    print(
        "SA-16 L17 controlled OAuth checkpoint validation passed: "
        f"approvals={FixtureState.approvals} token_posts={FixtureState.token_posts} "
        f"private_hits={FixtureState.private_hits} same_job_resume=1 "
        "retry_attempt_preserved=1 restart_resume=1 pkce_verified=1 "
        "revoked_access_denied=1 secret_leaks=0",
        flush=True,
    )


if __name__ == "__main__":
    main()
