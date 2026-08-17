from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

import httpx
import pytest

from cip.adapters.sources.public_web import federated_checkpoint_flow as flow
from cip.adapters.sources.public_web.federated_checkpoint_flow import (
    FederatedCheckpointCompletion,
    FederatedCheckpointContext,
    begin_delegated_federated_checkpoint,
    complete_delegated_federated_checkpoint,
    resolve_federated_token_for_job,
)
from cip.adapters.sources.public_web.federated_continuation import (
    FederatedContinuationBundle,
    FederatedContinuationState,
)
from cip.adapters.sources.public_web.federated_token_runtime import FederatedTokenMaterial
from cip.modules.collection_orchestration.domain.human_checkpoints import (
    HumanCheckpointKind,
    HumanCheckpointResumeRequest,
)
from cip.modules.provider_onboarding.domain.browser_login import (
    ProviderLoginHttpMethod,
    ProviderLoginTransitionRule,
)
from cip.modules.provider_onboarding.domain.federated_auth import (
    ProviderFederatedAuthFlow,
    ProviderFederatedAuthProfile,
)
from cip.modules.provider_onboarding.domain.models import SecretReference
from cip.modules.source_governance.application.delegated_identity_contracts import (
    DelegatedIdentityAccessDeniedError,
    DelegatedIdentityExecutionGrant,
)
from cip.modules.source_governance.domain.delegated_browser_identity import (
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
from cip.modules.source_governance.infrastructure.registry import SourceRegistryEntry

NOW = datetime(2026, 8, 17, 10, 0, tzinfo=UTC)
TENANT_ID = UUID("10000000-0000-4000-8000-000000000001")
IDENTITY_ID = UUID("20000000-0000-4000-8000-000000000002")
JOB_ID = UUID("30000000-0000-4000-8000-000000000003")
CHECKPOINT_ID = UUID("40000000-0000-4000-8000-000000000004")
SOURCE_ID = "provider"
PROFILE_ID = "provider-oauth"
PURPOSE = "authenticated-provider-research"
RESUME_TOKEN = "controlled-human-resume-token-0001"


class MemoryMaterialStore:
    def __init__(self) -> None:
        self.values: dict[str, str] = {}

    def reference_for(
        self,
        delegated_identity_id: UUID,
        checkpoint_id: UUID,
    ) -> SecretReference:
        return SecretReference(
            "file-secret:///run/secrets/"
            f"federated-{delegated_identity_id}-{checkpoint_id}.json"
        )

    def is_available(self, reference: SecretReference) -> bool:
        return reference.value in self.values

    def resolve(self, reference: SecretReference) -> str:
        try:
            return self.values[reference.value]
        except KeyError as exc:
            raise RuntimeError("material unavailable") from exc

    def write(self, reference: SecretReference, value: str) -> None:
        self.values[reference.value] = value

    def delete(self, reference: SecretReference) -> None:
        self.values.pop(reference.value, None)


class AlwaysAvailableResolver:
    def is_available(self, reference: SecretReference) -> bool:
        del reference
        return True


def _entry() -> SourceRegistryEntry:
    policy = SourcePolicy(
        id=SOURCE_ID,
        name="Controlled provider",
        base_url="https://provider.example/",
        status=SourceStatus.ENABLED,
        source_type=SourceType.BROWSER,
        owner="tests",
        licence="controlled",
        allowed_data_categories=frozenset(
            {DataCategory.OFFICIAL_DOCUMENT_DISCOVERY}
        ),
        human_review_required=False,
    )
    authorization = SourceAuthorization(
        status=AuthorizationStatus.APPROVED,
        document_reference="AUTH-L17",
        reviewed_at=NOW,
        approved_hosts=frozenset({"provider.example", "127.0.0.1"}),
        approved_path_prefixes=("/",),
        approved_purposes=frozenset({PURPOSE}),
        approved_http_methods=frozenset({HttpMethod.GET, HttpMethod.POST}),
        automated_collection_allowed=True,
    )
    return SourceRegistryEntry(policy, authorization, {})


def _profile() -> ProviderFederatedAuthProfile:
    return ProviderFederatedAuthProfile(
        id=PROFILE_ID,
        source_id=SOURCE_ID,
        flow=ProviderFederatedAuthFlow.OAUTH2_AUTHORIZATION_CODE_PKCE,
        authorization_url="https://provider.example/oauth/authorize",
        redirect_uri="http://127.0.0.1/oauth/callback",
        client_id="controlled-client",
        token_url="https://provider.example/oauth/token",
        scopes=("authenticated-page.read", "profile.read"),
        allowed_transitions=(
            ProviderLoginTransitionRule(
                host="provider.example",
                path_prefix="/oauth/authorize",
                methods=frozenset({ProviderLoginHttpMethod.GET}),
            ),
            ProviderLoginTransitionRule(
                host="provider.example",
                path_prefix="/oauth/token",
                methods=frozenset({ProviderLoginHttpMethod.POST}),
            ),
            ProviderLoginTransitionRule(
                host="127.0.0.1",
                path_prefix="/oauth/callback",
                methods=frozenset({ProviderLoginHttpMethod.GET}),
            ),
        ),
        review_reference="AUTH-L17",
        reviewed_at=NOW,
        material_ttl_seconds=900,
    )


def _context(*, job_id: UUID = JOB_ID) -> FederatedCheckpointContext:
    return FederatedCheckpointContext(
        delegated_identity_id=IDENTITY_ID,
        collection_job_id=job_id,
        adapter_id="controlled-oauth-adapter",
        execution_request=DelegatedExecutionRequest(
            tenant_id=TENANT_ID,
            owner_kind=DelegatedOwnerKind.SERVICE_PRINCIPAL,
            owner_subject_id="l17-worker",
            source_id=SOURCE_ID,
            purpose=PURPOSE,
            required_scopes=frozenset({"authenticated-page.read"}),
        ),
    )


def _grant(*, session_reference: str | None = None) -> DelegatedIdentityExecutionGrant:
    return DelegatedIdentityExecutionGrant(
        identity_id=IDENTITY_ID,
        source_id=SOURCE_ID,
        tenant_id=TENANT_ID,
        purpose=PURPOSE,
        approved_scopes=("authenticated-page.read", "profile.read"),
        session_reference=session_reference,
    )


def _patch_grant(
    monkeypatch: pytest.MonkeyPatch,
    *,
    session_reference: str | None = None,
    captured: list[DelegatedExecutionRequest] | None = None,
) -> None:
    def fake_grant(session, identity_id, request, *, resolver, now):
        del session, resolver, now
        assert identity_id == IDENTITY_ID
        if captured is not None:
            captured.append(request)
        return _grant(session_reference=session_reference)

    monkeypatch.setattr(flow, "issue_delegated_execution_grant", fake_grant)


def _start(
    monkeypatch: pytest.MonkeyPatch,
    store: MemoryMaterialStore,
):
    _patch_grant(monkeypatch)
    tokens = iter(("s" * 48, "v" * 64))
    return begin_delegated_federated_checkpoint(
        object(),
        _context(),
        _entry(),
        _profile(),
        identity_reference_resolver=AlwaysAvailableResolver(),
        material_store=store,
        now=NOW,
        token_factory=lambda: next(tokens),
        resume_token_factory=lambda: RESUME_TOKEN,
        checkpoint_id_factory=lambda: CHECKPOINT_ID,
    )


def _callback(bundle: FederatedContinuationBundle) -> str:
    return (
        "http://127.0.0.1/oauth/callback?code=authorization-code&state="
        f"{bundle.authorization.state}"
    )


def _token_transport(counter: list[int]) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        counter.append(1)
        assert request.method == "POST"
        return httpx.Response(
            200,
            headers={"Content-Type": "application/json"},
            json={
                "access_token": "opaque-access-token",
                "token_type": "Bearer",
                "scope": "authenticated-page.read profile.read",
                "expires_in": 3600,
            },
        )

    return httpx.MockTransport(handler)


def test_begin_creates_secret_backed_checkpoint_without_raw_resume_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = MemoryMaterialStore()
    captured: list[DelegatedExecutionRequest] = []
    _patch_grant(monkeypatch, captured=captured)
    tokens = iter(("s" * 48, "v" * 64))

    started = begin_delegated_federated_checkpoint(
        object(),
        _context(),
        _entry(),
        _profile(),
        identity_reference_resolver=AlwaysAvailableResolver(),
        material_store=store,
        now=NOW,
        token_factory=lambda: next(tokens),
        resume_token_factory=lambda: RESUME_TOKEN,
        checkpoint_id_factory=lambda: CHECKPOINT_ID,
    )

    checkpoint = started.checkpoint
    assert checkpoint.id == CHECKPOINT_ID
    assert checkpoint.kind is HumanCheckpointKind.OAUTH_CONSENT
    assert checkpoint.binding.job_id == JOB_ID
    assert checkpoint.binding.delegated_identity_id == IDENTITY_ID
    assert checkpoint.expires_at.timestamp() - NOW.timestamp() == 900
    assert checkpoint.session_reference is not None
    assert RESUME_TOKEN not in checkpoint.correlation_digest
    assert RESUME_TOKEN not in repr(started)
    assert "s" * 48 not in repr(started)
    assert captured[0].required_scopes == frozenset(
        {"authenticated-page.read", "profile.read"}
    )

    reference = store.reference_for(IDENTITY_ID, CHECKPOINT_ID)
    bundle = FederatedContinuationBundle.from_secret_json(store.resolve(reference))
    assert bundle.state is FederatedContinuationState.AUTHORIZATION_PENDING
    assert bundle.job_id == JOB_ID
    assert bundle.delegated_identity_id == IDENTITY_ID


def test_complete_exchanges_once_resumes_then_attaches_session(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = MemoryMaterialStore()
    started = _start(monkeypatch, store)
    reference = store.reference_for(IDENTITY_ID, CHECKPOINT_ID)
    bundle = FederatedContinuationBundle.from_secret_json(store.resolve(reference))
    events: list[str] = []
    attached: dict[str, object] = {}
    _patch_grant(monkeypatch)

    def fake_resume(session, request: HumanCheckpointResumeRequest) -> UUID:
        del session
        events.append("resume")
        assert request.checkpoint_id == CHECKPOINT_ID
        assert request.binding.job_id == JOB_ID
        assert request.correlation_token == RESUME_TOKEN
        return JOB_ID

    def fake_attach(session, identity_id, reference_value, **kwargs):
        del session
        events.append("attach")
        attached.update(
            identity_id=identity_id,
            reference=reference_value,
            expires_at=kwargs["expires_at"],
        )
        return object()

    monkeypatch.setattr(flow, "attach_delegated_session_reference", fake_attach)
    posts: list[int] = []
    completion = FederatedCheckpointCompletion(
        checkpoint_id=CHECKPOINT_ID,
        callback_url=_callback(bundle),
        correlation_token=started.correlation_token,
        actor_reference="user:controlled-approver",
        completed_at=NOW,
    )
    with httpx.Client(transport=_token_transport(posts)) as client:
        result = complete_delegated_federated_checkpoint(
            object(),
            _context(),
            _entry(),
            _profile(),
            completion,
            identity_reference_resolver=AlwaysAvailableResolver(),
            material_store=store,
            client=client,
            resume_checkpoint=fake_resume,
        )

    assert posts == [1]
    assert events == ["resume", "attach"]
    assert result.job_id == JOB_ID
    assert not result.token_exchange_reused
    assert attached["identity_id"] == IDENTITY_ID
    assert attached["reference"] == reference.value
    persisted = FederatedContinuationBundle.from_secret_json(store.resolve(reference))
    assert persisted.state is FederatedContinuationState.TOKEN_READY
    assert persisted.token is not None
    assert "opaque-access-token" not in repr(result)


def test_token_ready_replay_does_not_exchange_consumed_code_again(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = MemoryMaterialStore()
    started = _start(monkeypatch, store)
    reference = store.reference_for(IDENTITY_ID, CHECKPOINT_ID)
    bundle = FederatedContinuationBundle.from_secret_json(store.resolve(reference))
    _patch_grant(monkeypatch)
    monkeypatch.setattr(
        flow,
        "attach_delegated_session_reference",
        lambda *args, **kwargs: object(),
    )
    completion = FederatedCheckpointCompletion(
        checkpoint_id=CHECKPOINT_ID,
        callback_url=_callback(bundle),
        correlation_token=started.correlation_token,
        actor_reference="user:controlled-approver",
        completed_at=NOW,
    )
    posts: list[int] = []

    def fail_resume(session, request):
        del session, request
        raise RuntimeError("database transaction failed after provider exchange")

    with (
        httpx.Client(transport=_token_transport(posts)) as client,
        pytest.raises(RuntimeError, match="database transaction failed"),
    ):
        complete_delegated_federated_checkpoint(
            object(),
            _context(),
            _entry(),
            _profile(),
            completion,
            identity_reference_resolver=AlwaysAvailableResolver(),
            material_store=store,
            client=client,
            resume_checkpoint=fail_resume,
        )
    assert posts == [1]
    persisted = FederatedContinuationBundle.from_secret_json(store.resolve(reference))
    assert persisted.state is FederatedContinuationState.TOKEN_READY

    def forbidden_transport(request: httpx.Request) -> httpx.Response:
        raise AssertionError(f"token endpoint was replayed: {request.url}")

    with httpx.Client(transport=httpx.MockTransport(forbidden_transport)) as client:
        replayed = complete_delegated_federated_checkpoint(
            object(),
            _context(),
            _entry(),
            _profile(),
            completion,
            identity_reference_resolver=AlwaysAvailableResolver(),
            material_store=store,
            client=client,
            resume_checkpoint=lambda _session, _request: JOB_ID,
        )
    assert replayed.token_exchange_reused
    assert replayed.job_id == JOB_ID


def test_revoked_identity_stops_completion_before_network_or_resume(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = MemoryMaterialStore()

    def denied(*args, **kwargs):
        del args, kwargs
        raise DelegatedIdentityAccessDeniedError("revoked")

    monkeypatch.setattr(flow, "issue_delegated_execution_grant", denied)
    resumed: list[bool] = []

    def transport(request: httpx.Request) -> httpx.Response:
        raise AssertionError(f"network request after revoked identity: {request.url}")

    completion = FederatedCheckpointCompletion(
        checkpoint_id=CHECKPOINT_ID,
        callback_url="http://127.0.0.1/oauth/callback?code=x&state=y",
        correlation_token=RESUME_TOKEN,
        actor_reference="user:controlled-approver",
        completed_at=NOW,
    )
    with (
        httpx.Client(transport=httpx.MockTransport(transport)) as client,
        pytest.raises(DelegatedIdentityAccessDeniedError, match="revoked"),
    ):
        complete_delegated_federated_checkpoint(
            object(),
            _context(),
            _entry(),
            _profile(),
            completion,
            identity_reference_resolver=AlwaysAvailableResolver(),
            material_store=store,
            client=client,
            resume_checkpoint=lambda _session, _request: resumed.append(True) or JOB_ID,
        )
    assert not resumed


def test_resolve_token_is_bound_to_same_job_and_ready_bundle(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = MemoryMaterialStore()
    _start(monkeypatch, store)
    reference = store.reference_for(IDENTITY_ID, CHECKPOINT_ID)
    pending = FederatedContinuationBundle.from_secret_json(store.resolve(reference))
    ready = pending.with_token(
        FederatedTokenMaterial(
            access_token="opaque-access-token",
            scopes=("authenticated-page.read", "profile.read"),
        )
    )
    store.write(reference, ready.to_secret_json())
    _patch_grant(monkeypatch, session_reference=reference.value)

    token = resolve_federated_token_for_job(
        object(),
        _context(),
        _profile(),
        material_store=store,
        now=NOW,
    )
    assert token.access_token == "opaque-access-token"
    assert "opaque-access-token" not in repr(token)

    with pytest.raises(ValueError, match="binding mismatch"):
        resolve_federated_token_for_job(
            object(),
            _context(job_id=UUID("50000000-0000-4000-8000-000000000005")),
            _profile(),
            material_store=store,
            now=NOW,
        )
