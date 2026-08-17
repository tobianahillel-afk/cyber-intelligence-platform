from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from uuid import UUID

from cip.adapters.sources.public_web.federated_checkpoint_flow import (
    FederatedCheckpointContext,
)
from cip.modules.collection_orchestration.domain.models import CollectionJob
from cip.modules.source_governance.application.delegated_identity_contracts import (
    DelegatedOperatorContext,
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
from cip.modules.source_governance.infrastructure.models import SourceRecord
from cip.modules.source_governance.infrastructure.registry import SourceRegistryEntry
from sa16_l17_controlled_oauth_fixture import BASE

SOURCE_ID = "sa16-l17-controlled-provider"
ADAPTER_ID = "sa16-l17-controlled-oauth"
PURPOSE = "sa16-l17-authorized-oauth-proof"
PROFILE_PATH = Path("tests/fixtures/sa16_l17_federated_auth_profiles.yml")
_OWNER_SUBJECT = "sa16-l17-controlled-worker"
_AUTH_REFERENCE = "SA16-L17-CONTROLLED-OAUTH"


def source_record(now: datetime) -> SourceRecord:
    return SourceRecord(
        id=SOURCE_ID,
        name="SA16 L17 controlled OAuth provider",
        base_url=f"{BASE}/",
        status="enabled",
        source_type="browser",
        owner="CIP controlled live validation",
        terms_url=None,
        licence="Repository-owned controlled L17 fixture",
        allowed_data_categories=[DataCategory.OFFICIAL_DOCUMENT_DISCOVERY.value],
        prohibited_data_categories=[],
        rate_limit_per_minute=None,
        retention_days=None,
        attribution_required=False,
        raw_content_storage=False,
        human_review_required=False,
        authorization_status="approved",
        authorization_document_reference=_AUTH_REFERENCE,
        authorization_reviewed_at=now,
        authorization_expires_at=None,
        approved_hosts=["127.0.0.1"],
        approved_path_prefixes=["/"],
        approved_purposes=[PURPOSE],
        approved_http_methods=["GET", "POST"],
        automated_collection_allowed=True,
        raw_storage_allowed=False,
    )


def source_entry(now: datetime) -> SourceRegistryEntry:
    policy = SourcePolicy(
        id=SOURCE_ID,
        name="SA16 L17 controlled OAuth provider",
        base_url=f"{BASE}/",
        status=SourceStatus.ENABLED,
        source_type=SourceType.BROWSER,
        owner="CIP controlled live validation",
        licence="Repository-owned controlled L17 fixture",
        allowed_data_categories=frozenset(
            {DataCategory.OFFICIAL_DOCUMENT_DISCOVERY}
        ),
        human_review_required=False,
    )
    authorization = SourceAuthorization(
        status=AuthorizationStatus.APPROVED,
        document_reference=_AUTH_REFERENCE,
        reviewed_at=now,
        approved_hosts=frozenset({"127.0.0.1"}),
        approved_path_prefixes=("/",),
        approved_purposes=frozenset({PURPOSE}),
        approved_http_methods=frozenset({HttpMethod.GET, HttpMethod.POST}),
        automated_collection_allowed=True,
    )
    return SourceRegistryEntry(policy, authorization, {})


def delegated_identity(now: datetime, tenant_id: UUID) -> DelegatedBrowserIdentity:
    account = SourceAccount(
        source_id=SOURCE_ID,
        external_reference="controlled-oauth-user",
        auth_mode=SourceAccountAuthMode.OAUTH,
        status=SourceAccountStatus.PENDING_VERIFICATION,
        authorization_document_reference=_AUTH_REFERENCE,
        approved_purposes=frozenset({PURPOSE}),
        created_at=now,
        expires_at=now + timedelta(days=30),
    )
    return DelegatedBrowserIdentity(
        account=account,
        tenant_id=tenant_id,
        owner_kind=DelegatedOwnerKind.SERVICE_PRINCIPAL,
        owner_subject_id=_OWNER_SUBJECT,
        purpose=PURPOSE,
        approved_scopes=frozenset({"read"}),
        created_at=now,
    )


def operator_context(tenant_id: UUID) -> DelegatedOperatorContext:
    return DelegatedOperatorContext(
        tenant_id=tenant_id,
        owner_kind=DelegatedOwnerKind.SERVICE_PRINCIPAL,
        owner_subject_id=_OWNER_SUBJECT,
    )


def execution_request(tenant_id: UUID) -> DelegatedExecutionRequest:
    return DelegatedExecutionRequest(
        tenant_id=tenant_id,
        owner_kind=DelegatedOwnerKind.SERVICE_PRINCIPAL,
        owner_subject_id=_OWNER_SUBJECT,
        source_id=SOURCE_ID,
        purpose=PURPOSE,
        required_scopes=frozenset({"read"}),
    )


def collection_job(now: datetime) -> CollectionJob:
    return CollectionJob(
        source_id=SOURCE_ID,
        adapter_id=ADAPTER_ID,
        scheduled_for=now,
        available_at=now,
        lease_seconds=120,
        max_attempts=4,
        base_delay_seconds=30,
        max_delay_seconds=900,
        circuit_failure_threshold=3,
        circuit_reset_seconds=900,
        created_at=now,
    )


def checkpoint_context(
    identity_id: UUID,
    job_id: UUID,
    request: DelegatedExecutionRequest,
) -> FederatedCheckpointContext:
    return FederatedCheckpointContext(
        delegated_identity_id=identity_id,
        collection_job_id=job_id,
        adapter_id=ADAPTER_ID,
        execution_request=request,
    )
