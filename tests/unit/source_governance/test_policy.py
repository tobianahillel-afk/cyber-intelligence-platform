from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from cip.modules.source_governance.domain.models import (
    AuthorizationStatus,
    CollectionRequest,
    DataCategory,
    DecisionReason,
    SourceAuthorization,
    SourcePolicy,
    SourceRuntimeState,
    SourceStatus,
    SourceType,
)

NOW = datetime(2026, 8, 3, 16, 0, tzinfo=UTC)


def enabled_policy(**changes: object) -> SourcePolicy:
    values: dict[str, object] = {
        "id": "official-api",
        "name": "Official API",
        "base_url": "https://api.example.org",
        "status": SourceStatus.ENABLED,
        "source_type": SourceType.API,
        "owner": "Example Authority",
        "terms_url": "https://example.org/terms",
        "allowed_data_categories": frozenset({DataCategory.PUBLIC_INCIDENT_METADATA}),
        "prohibited_data_categories": frozenset({DataCategory.CREDENTIAL}),
        "rate_limit_per_minute": 30,
        "retention_days": 90,
        "raw_content_storage": True,
        "human_review_required": False,
    }
    values.update(changes)
    return SourcePolicy(**values)  # type: ignore[arg-type]


def approved_authorization(**changes: object) -> SourceAuthorization:
    values: dict[str, object] = {
        "status": AuthorizationStatus.APPROVED,
        "document_reference": "AUTH-2026-001",
        "reviewed_at": NOW - timedelta(days=1),
        "expires_at": NOW + timedelta(days=30),
        "approved_hosts": frozenset({"api.example.org"}),
        "approved_path_prefixes": ("/v1/",),
        "approved_purposes": frozenset({"cyber-opportunity-research"}),
        "automated_collection_allowed": True,
        "raw_storage_allowed": True,
    }
    values.update(changes)
    return SourceAuthorization(**values)  # type: ignore[arg-type]


def collection_request(**changes: object) -> CollectionRequest:
    values: dict[str, object] = {
        "data_category": DataCategory.PUBLIC_INCIDENT_METADATA,
        "target_url": "https://api.example.org/v1/incidents",
        "purpose": "cyber-opportunity-research",
        "automated": True,
        "store_raw_content": False,
        "human_review_completed": False,
    }
    values.update(changes)
    return CollectionRequest(**values)  # type: ignore[arg-type]


def evaluate(
    policy: SourcePolicy | None = None,
    authorization: SourceAuthorization | None = None,
    request: CollectionRequest | None = None,
    runtime: SourceRuntimeState | None = None,
):
    return (policy or enabled_policy()).evaluate(
        request or collection_request(),
        authorization or approved_authorization(),
        runtime or SourceRuntimeState(remaining_requests=10),
        now=NOW,
    )


def test_approved_request_is_allowed() -> None:
    decision = evaluate()

    assert decision.allowed is True
    assert decision.reason is DecisionReason.ALLOWED
    assert decision.requires_human_review is False


@pytest.mark.parametrize(
    ("status", "expected_reason"),
    [
        (SourceStatus.BLOCKED, DecisionReason.SOURCE_BLOCKED),
        (SourceStatus.DRAFT, DecisionReason.SOURCE_NOT_ENABLED),
        (SourceStatus.PENDING_REVIEW, DecisionReason.SOURCE_NOT_ENABLED),
        (SourceStatus.CONDITIONAL, DecisionReason.SOURCE_NOT_ENABLED),
        (SourceStatus.PAUSED, DecisionReason.SOURCE_NOT_ENABLED),
        (SourceStatus.QUARANTINED, DecisionReason.SOURCE_NOT_ENABLED),
        (SourceStatus.EXPIRED, DecisionReason.SOURCE_NOT_ENABLED),
        (SourceStatus.REVOKED, DecisionReason.SOURCE_NOT_ENABLED),
    ],
)
def test_non_enabled_sources_are_denied(
    status: SourceStatus,
    expected_reason: DecisionReason,
) -> None:
    allowed_categories = (
        frozenset()
        if status is SourceStatus.BLOCKED
        else frozenset({DataCategory.PUBLIC_INCIDENT_METADATA})
    )
    policy = enabled_policy(status=status, allowed_data_categories=allowed_categories)

    assert evaluate(policy=policy).reason is expected_reason


def test_overlapping_categories_are_rejected() -> None:
    with pytest.raises(ValueError, match="both allowed and prohibited"):
        enabled_policy(
            allowed_data_categories=frozenset({DataCategory.CREDENTIAL}),
            prohibited_data_categories=frozenset({DataCategory.CREDENTIAL}),
        )


def test_prohibited_category_is_denied() -> None:
    request = collection_request(data_category=DataCategory.CREDENTIAL)

    assert evaluate(request=request).reason is DecisionReason.CATEGORY_PROHIBITED


def test_unlisted_category_is_denied() -> None:
    request = collection_request(data_category=DataCategory.PUBLIC_TENDER)

    assert evaluate(request=request).reason is DecisionReason.CATEGORY_NOT_ALLOWED


@pytest.mark.parametrize(
    ("status", "expected_reason"),
    [
        (AuthorizationStatus.MISSING, DecisionReason.AUTHORIZATION_MISSING),
        (AuthorizationStatus.PENDING_REVIEW, DecisionReason.AUTHORIZATION_NOT_APPROVED),
        (AuthorizationStatus.REVOKED, DecisionReason.AUTHORIZATION_NOT_APPROVED),
        (AuthorizationStatus.EXPIRED, DecisionReason.AUTHORIZATION_EXPIRED),
    ],
)
def test_authorization_state_is_enforced(
    status: AuthorizationStatus,
    expected_reason: DecisionReason,
) -> None:
    authorization = SourceAuthorization(status=status)

    assert evaluate(authorization=authorization).reason is expected_reason


def test_authorization_expiry_timestamp_is_enforced() -> None:
    authorization = approved_authorization(expires_at=NOW)

    assert evaluate(authorization=authorization).reason is DecisionReason.AUTHORIZATION_EXPIRED


def test_automation_requires_explicit_permission() -> None:
    authorization = approved_authorization(automated_collection_allowed=False)

    assert evaluate(authorization=authorization).reason is DecisionReason.AUTOMATION_NOT_ALLOWED


def test_manual_request_does_not_require_automation_permission() -> None:
    authorization = approved_authorization(automated_collection_allowed=False)
    request = collection_request(automated=False)

    assert evaluate(authorization=authorization, request=request).allowed is True


@pytest.mark.parametrize(
    ("policy_allows", "authorization_allows"),
    [(False, True), (True, False), (False, False)],
)
def test_raw_storage_requires_both_permissions(
    policy_allows: bool,
    authorization_allows: bool,
) -> None:
    policy = enabled_policy(raw_content_storage=policy_allows)
    authorization = approved_authorization(raw_storage_allowed=authorization_allows)
    request = collection_request(store_raw_content=True)

    assert (
        evaluate(policy=policy, authorization=authorization, request=request).reason
        is DecisionReason.RAW_STORAGE_NOT_ALLOWED
    )


def test_raw_storage_is_allowed_when_both_permissions_exist() -> None:
    request = collection_request(store_raw_content=True)

    assert evaluate(request=request).allowed is True


def test_human_review_is_a_real_gate() -> None:
    policy = enabled_policy(human_review_required=True)

    decision = evaluate(policy=policy)

    assert decision.reason is DecisionReason.HUMAN_REVIEW_REQUIRED
    assert decision.requires_human_review is True


def test_completed_human_review_allows_progress() -> None:
    policy = enabled_policy(human_review_required=True)
    request = collection_request(human_review_completed=True)

    assert evaluate(policy=policy, request=request).allowed is True


def test_runtime_quota_is_enforced() -> None:
    runtime = SourceRuntimeState(remaining_requests=0)

    assert evaluate(runtime=runtime).reason is DecisionReason.RATE_LIMIT_EXHAUSTED


def test_purpose_is_enforced() -> None:
    request = collection_request(purpose="unapproved-purpose")

    assert evaluate(request=request).reason is DecisionReason.AUTHORIZATION_NOT_APPROVED


def test_host_allowlist_is_enforced() -> None:
    request = collection_request(target_url="https://other.example.org/v1/incidents")

    assert evaluate(request=request).reason is DecisionReason.HOST_NOT_ALLOWED


def test_path_allowlist_is_enforced() -> None:
    request = collection_request(target_url="https://api.example.org/admin/incidents")

    assert evaluate(request=request).reason is DecisionReason.PATH_NOT_ALLOWED


def test_invalid_target_scheme_is_denied() -> None:
    request = collection_request(target_url="ftp://api.example.org/v1/incidents")

    assert evaluate(request=request).reason is DecisionReason.PATH_NOT_ALLOWED


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"id": ""}, "source id, name, and owner"),
        ({"name": ""}, "source id, name, and owner"),
        ({"owner": ""}, "source id, name, and owner"),
        ({"base_url": "ftp://example.org"}, "base_url"),
        ({"terms_url": "not-a-url"}, "terms_url"),
        ({"rate_limit_per_minute": 0}, "rate_limit_per_minute"),
        ({"retention_days": 0}, "retention_days"),
    ],
)
def test_policy_validation(changes: dict[str, object], message: str) -> None:
    with pytest.raises(ValueError, match=message):
        enabled_policy(**changes)


def test_blocked_source_cannot_allow_categories() -> None:
    with pytest.raises(ValueError, match="blocked sources"):
        enabled_policy(status=SourceStatus.BLOCKED)


def test_runnable_automated_source_requires_terms_or_licence() -> None:
    with pytest.raises(ValueError, match="runnable automated"):
        enabled_policy(terms_url=None, licence=None)


@pytest.mark.parametrize(
    "status",
    [
        SourceStatus.DRAFT,
        SourceStatus.PENDING_REVIEW,
        SourceStatus.QUARANTINED,
        SourceStatus.BLOCKED,
    ],
)
def test_non_runnable_source_can_be_recorded_without_terms(status: SourceStatus) -> None:
    policy = enabled_policy(
        status=status,
        terms_url=None,
        licence=None,
        allowed_data_categories=(
            frozenset() if status is SourceStatus.BLOCKED else frozenset({DataCategory.PUBLIC_TENDER})
        ),
    )

    assert policy.status is status


def test_manual_import_does_not_require_terms() -> None:
    policy = enabled_policy(source_type=SourceType.MANUAL_IMPORT, terms_url=None, licence=None)

    assert policy.source_type is SourceType.MANUAL_IMPORT


def test_approved_authorization_requires_document() -> None:
    with pytest.raises(ValueError, match="document reference"):
        SourceAuthorization(status=AuthorizationStatus.APPROVED)


def test_authorization_rejects_naive_timestamps() -> None:
    with pytest.raises(ValueError, match="reviewed_at must be timezone-aware"):
        SourceAuthorization(
            status=AuthorizationStatus.PENDING_REVIEW,
            reviewed_at=datetime(2026, 8, 3, 16, 0),
        )


def test_authorization_normalizes_expiry_timestamp() -> None:
    authorization = approved_authorization()

    assert authorization.reviewed_at is not None
    assert authorization.expires_at is not None
    assert authorization.expires_at.tzinfo is UTC


def test_runtime_rejects_negative_quota() -> None:
    with pytest.raises(ValueError, match="cannot be negative"):
        SourceRuntimeState(remaining_requests=-1)


def test_runtime_rejects_naive_timestamp() -> None:
    with pytest.raises(ValueError, match="last_success_at must be timezone-aware"):
        SourceRuntimeState(last_success_at=datetime(2026, 8, 3, 16, 0))


def test_runtime_normalizes_timestamp() -> None:
    runtime = SourceRuntimeState(last_success_at=NOW)

    assert runtime.last_success_at == NOW


def test_evaluation_rejects_naive_now() -> None:
    with pytest.raises(ValueError, match="now must be timezone-aware"):
        enabled_policy().evaluate(
            collection_request(),
            approved_authorization(),
            SourceRuntimeState(),
            now=datetime(2026, 8, 3, 16, 0),
        )
