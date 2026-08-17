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
)
from cip.modules.provider_onboarding.application.federated_material import (
    FederatedContinuationMaterialStore,
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
PURPOSE = "authorized-research"
TOKEN = "controlled-human-resume-token"


class MemoryStore(FederatedContinuationMaterialStore):
    def __init__(self) -> None:
        self.values: dict[str, str] = {}

    def reference_for(self, delegated_identity_id: UUID, checkpoint_id: UUID) -> SecretReference:
        return SecretReference(
            "file-secret:///run/secrets/"
            f"material-{delegated_identity_id}-{checkpoint_id}.json"
        )

    def is_available(self, reference: SecretReference) -> bool:
        return reference.value in self.values

    def resolve(self, reference: SecretReference) -> str:
        return self.values[reference.value]

    def write(self, reference: SecretReference, value: str) -> None:
        self.values[reference.value] = value

    def delete(self, reference: SecretReference) -> None:
        self.values.pop(reference.value, None)


class AvailableResolver:
    def is_available(self, reference: SecretReference) -> bool:
        del reference
        return True


def _entry(source_id: str = "provider") -> SourceRegistryEntry:
    return SourceRegistryEntry(
        SourcePolicy(
            id=source_id,
            name="Provider",
            base_url="https://provider.example/",
            status=SourceStatus.ENABLED,
            source_type=SourceType.BROWSER,
            owner="tests",
            licence="controlled",
            allowed_data_categories=frozenset(
                {DataCategory.OFFICIAL_DOCUMENT_DISCOVERY}
            ),
            human_review_required=False,
        ),
        SourceAuthorization(
            status=AuthorizationStatus.APPROVED,
            document_reference="AUTH-L17",
            reviewed_at=NOW,
            approved_hosts=frozenset({"provider.example", "127.0.0.1"}),
            approved_path_prefixes=("/",),
            approved_purposes=frozenset({PURPOSE}),
            approved_http_methods=frozenset({HttpMethod.GET, HttpMethod.POST}),
            automated_collection_allowed=True,
        ),
        {},
    )


def _profile(*, flow_type: ProviderFederatedAuthFlow | None = None) -> ProviderFederatedAuthProfile:
    flow_type = flow_type or ProviderFederatedAuthFlow.OAUTH2_AUTHORIZATION_CODE_PKCE
    if flow_type is ProviderFederatedAuthFlow.BROWSER_SSO:
        return ProviderFederatedAuthProfile(
            id="profile",
            source_id="provider",
            flow=flow_type,
            authorization_url="https://provider.example/sso/start",
            redirect_uri="https://provider.example/sso/complete",
            allowed_transitions=(
                ProviderLoginTransitionRule(
                    host="provider.example",
                    path_prefix="/sso",
                    methods=frozenset({ProviderLoginHttpMethod.GET}),
                ),
            ),
            review_reference="AUTH-L17",
            reviewed_at=NOW,
        )
    return ProviderFederatedAuthProfile(
        id="profile",
        source_id="provider",
        flow=flow_type,
        authorization_url="https://provider.example/oauth/authorize",
        redirect_uri="http://127.0.0.1/oauth/callback",
        client_id="client",
        token_url="https://provider.example/oauth/token",
        scopes=("read",),
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
    )


def _context(*, adapter_id: str = "adapter", job_id: UUID = JOB_ID) -> FederatedCheckpointContext:
    return FederatedCheckpointContext(
        delegated_identity_id=IDENTITY_ID,
        collection_job_id=job_id,
        adapter_id=adapter_id,
        execution_request=DelegatedExecutionRequest(
            tenant_id=TENANT_ID,
            owner_kind=DelegatedOwnerKind.SERVICE_PRINCIPAL,
            owner_subject_id="worker",
            source_id="provider",
            purpose=PURPOSE,
            required_scopes=frozenset({"read"}),
        ),
    )


def _patch_grant(
    monkeypatch: pytest.MonkeyPatch,
    *,
    session_reference: str | None = None,
) -> None:
    monkeypatch.setattr(
        flow,
        "issue_delegated_execution_grant",
        lambda *args, **kwargs: DelegatedIdentityExecutionGrant(
            identity_id=IDENTITY_ID,
            source_id="provider",
            tenant_id=TENANT_ID,
            purpose=PURPOSE,
            approved_scopes=("read",),
            session_reference=session_reference,
        ),
    )


def _start(monkeypatch: pytest.MonkeyPatch, store: MemoryStore):
    _patch_grant(monkeypatch)
    tokens = iter(("s" * 48, "v" * 64))
    return begin_delegated_federated_checkpoint(
        object(),
        _context(),
        _entry(),
        _profile(),
        identity_reference_resolver=AvailableResolver(),
        material_store=store,
        now=NOW,
        token_factory=lambda: next(tokens),
        resume_token_factory=lambda: TOKEN,
        checkpoint_id_factory=lambda: CHECKPOINT_ID,
    )


def test_context_and_completion_validate_operator_inputs() -> None:
    with pytest.raises(ValueError, match="adapter_id"):
        _context(adapter_id=" ")
    with pytest.raises(ValueError, match="callback_url"):
        FederatedCheckpointCompletion(
            checkpoint_id=CHECKPOINT_ID,
            callback_url=" ",
            correlation_token=TOKEN,
            actor_reference="user:approver",
            completed_at=NOW,
        )
    with pytest.raises(ValueError, match="actor_reference"):
        FederatedCheckpointCompletion(
            checkpoint_id=CHECKPOINT_ID,
            callback_url="http://127.0.0.1/oauth/callback",
            correlation_token=TOKEN,
            actor_reference=" ",
            completed_at=NOW,
        )
    with pytest.raises(ValueError, match="correlation token"):
        FederatedCheckpointCompletion(
            checkpoint_id=CHECKPOINT_ID,
            callback_url="http://127.0.0.1/oauth/callback",
            correlation_token="short",
            actor_reference="user:approver",
            completed_at=NOW,
        )


def test_begin_rejects_source_mismatch_and_non_pkce_profile(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_grant(monkeypatch)
    with pytest.raises(ValueError, match="source binding"):
        begin_delegated_federated_checkpoint(
            object(),
            _context(),
            _entry("other"),
            _profile(),
            identity_reference_resolver=AvailableResolver(),
            material_store=MemoryStore(),
            now=NOW,
        )
    with pytest.raises(ValueError, match="not executable"):
        begin_delegated_federated_checkpoint(
            object(),
            _context(),
            _entry(),
            _profile(flow_type=ProviderFederatedAuthFlow.BROWSER_SSO),
            identity_reference_resolver=AvailableResolver(),
            material_store=MemoryStore(),
            now=NOW,
        )


def test_complete_rejects_unexpected_resumed_job_before_session_attach(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = MemoryStore()
    started = _start(monkeypatch, store)
    reference = store.reference_for(IDENTITY_ID, CHECKPOINT_ID)
    bundle = FederatedContinuationBundle.from_secret_json(store.resolve(reference))
    attached: list[bool] = []
    monkeypatch.setattr(
        flow,
        "attach_delegated_session_reference",
        lambda *args, **kwargs: attached.append(True),
    )
    response = httpx.Response(
        200,
        headers={"Content-Type": "application/json"},
        json={"access_token": "opaque", "scope": "read"},
    )
    callback = (
        "http://127.0.0.1/oauth/callback?code=code&state="
        + bundle.authorization.state
    )
    with (
        httpx.Client(transport=httpx.MockTransport(lambda _request: response)) as client,
        pytest.raises(RuntimeError, match="unexpected collection job"),
    ):
        complete_delegated_federated_checkpoint(
            object(),
            _context(),
            _entry(),
            _profile(),
            FederatedCheckpointCompletion(
                checkpoint_id=CHECKPOINT_ID,
                callback_url=callback,
                correlation_token=started.correlation_token,
                actor_reference="user:approver",
                completed_at=NOW,
            ),
            identity_reference_resolver=AvailableResolver(),
            material_store=store,
            client=client,
            resume_checkpoint=lambda _session, _request: UUID(
                "50000000-0000-4000-8000-000000000005"
            ),
        )
    assert not attached


def test_resolve_requires_session_reference_and_ready_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = MemoryStore()
    _start(monkeypatch, store)
    _patch_grant(monkeypatch, session_reference=None)
    with pytest.raises(RuntimeError, match="session reference"):
        resolve_federated_token_for_job(
            object(),
            _context(),
            _profile(),
            material_store=store,
            now=NOW,
        )

    reference = store.reference_for(IDENTITY_ID, CHECKPOINT_ID)
    _patch_grant(monkeypatch, session_reference=reference.value)
    with pytest.raises(ValueError, match="ready token"):
        resolve_federated_token_for_job(
            object(),
            _context(),
            _profile(),
            material_store=store,
            now=NOW,
        )
