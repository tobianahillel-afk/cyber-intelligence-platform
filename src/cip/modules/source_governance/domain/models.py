from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from urllib.parse import urlparse

from cip.shared.kernel.time import require_aware_utc


class SourceStatus(StrEnum):
    DRAFT = "draft"
    PENDING_REVIEW = "pending_review"
    CONDITIONAL = "conditional"
    ENABLED = "enabled"
    PAUSED = "paused"
    QUARANTINED = "quarantined"
    EXPIRED = "expired"
    REVOKED = "revoked"
    BLOCKED = "blocked"


class SourceType(StrEnum):
    API = "api"
    FEED = "feed"
    STATIC_HTTP = "static_http"
    BROWSER = "browser"
    SEARCH_PROVIDER = "search_provider"
    BULK_FILE = "bulk_file"
    MANUAL_IMPORT = "manual_import"
    WEBHOOK = "webhook"
    LICENSED_DATASET = "licensed_dataset"


class DataCategory(StrEnum):
    ORGANIZATION_METADATA = "organization_metadata"
    PROFESSIONAL_CONTACT = "professional_contact"
    PUBLIC_INCIDENT_METADATA = "public_incident_metadata"
    VULNERABILITY_METADATA = "vulnerability_metadata"
    KNOWN_EXPLOITED_STATUS = "known_exploited_status"
    TECHNOLOGY_OBSERVATION = "technology_observation"
    PUBLIC_TENDER = "public_tender"
    CONTRACT_AWARD = "contract_award"
    PUBLIC_JOB_POSTING = "public_job_posting"
    PUBLIC_RESULT_METADATA = "public_result_metadata"
    OFFICIAL_DOCUMENT_DISCOVERY = "official_document_discovery"
    PUBLIC_SECURITY_CONTACT_DISCOVERY = "public_security_contact_discovery"
    CREDENTIAL = "credential"
    VICTIM_FILE = "victim_file"
    PRIVATE_COMMUNICATION = "private_communication"
    PRIVATE_PERSONAL_DATA = "private_personal_data"
    RESTRICTED_CONTENT = "restricted_content"


class AuthorizationStatus(StrEnum):
    MISSING = "missing"
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    EXPIRED = "expired"
    REVOKED = "revoked"


class DecisionReason(StrEnum):
    ALLOWED = "allowed"
    SOURCE_NOT_ENABLED = "source_not_enabled"
    SOURCE_BLOCKED = "source_blocked"
    AUTHORIZATION_MISSING = "authorization_missing"
    AUTHORIZATION_NOT_APPROVED = "authorization_not_approved"
    AUTHORIZATION_EXPIRED = "authorization_expired"
    CATEGORY_NOT_ALLOWED = "category_not_allowed"
    CATEGORY_PROHIBITED = "category_prohibited"
    AUTOMATION_NOT_ALLOWED = "automation_not_allowed"
    RAW_STORAGE_NOT_ALLOWED = "raw_storage_not_allowed"
    HUMAN_REVIEW_REQUIRED = "human_review_required"
    RATE_LIMIT_EXHAUSTED = "rate_limit_exhausted"
    HOST_NOT_ALLOWED = "host_not_allowed"
    PATH_NOT_ALLOWED = "path_not_allowed"


@dataclass(frozen=True, slots=True)
class SourceAuthorization:
    status: AuthorizationStatus
    document_reference: str | None = None
    reviewed_at: datetime | None = None
    expires_at: datetime | None = None
    approved_hosts: frozenset[str] = field(default_factory=frozenset)
    approved_path_prefixes: tuple[str, ...] = ()
    approved_purposes: frozenset[str] = field(default_factory=frozenset)
    automated_collection_allowed: bool = False
    raw_storage_allowed: bool = False

    def __post_init__(self) -> None:
        if self.reviewed_at is not None:
            object.__setattr__(
                self,
                "reviewed_at",
                require_aware_utc(self.reviewed_at, field_name="reviewed_at"),
            )
        if self.expires_at is not None:
            object.__setattr__(
                self,
                "expires_at",
                require_aware_utc(self.expires_at, field_name="expires_at"),
            )
        if self.status is AuthorizationStatus.APPROVED and not self.document_reference:
            raise ValueError("approved authorization requires a document reference")


@dataclass(frozen=True, slots=True)
class SourceRuntimeState:
    remaining_requests: int | None = None
    paused_reason: str | None = None
    last_success_at: datetime | None = None

    def __post_init__(self) -> None:
        if self.remaining_requests is not None and self.remaining_requests < 0:
            raise ValueError("remaining_requests cannot be negative")
        if self.last_success_at is not None:
            object.__setattr__(
                self,
                "last_success_at",
                require_aware_utc(self.last_success_at, field_name="last_success_at"),
            )


@dataclass(frozen=True, slots=True)
class CollectionRequest:
    data_category: DataCategory
    target_url: str
    purpose: str
    automated: bool = True
    store_raw_content: bool = False
    human_review_completed: bool = False


@dataclass(frozen=True, slots=True)
class CollectionDecision:
    allowed: bool
    reason: DecisionReason
    requires_human_review: bool = False


@dataclass(frozen=True, slots=True)
class SourcePolicy:
    id: str
    name: str
    base_url: str
    status: SourceStatus
    source_type: SourceType
    owner: str
    allowed_data_categories: frozenset[DataCategory] = field(default_factory=frozenset)
    prohibited_data_categories: frozenset[DataCategory] = field(default_factory=frozenset)
    terms_url: str | None = None
    licence: str | None = None
    rate_limit_per_minute: int | None = None
    retention_days: int | None = None
    attribution_required: bool = False
    raw_content_storage: bool = False
    human_review_required: bool = True

    def __post_init__(self) -> None:
        if not self.id or not self.name or not self.owner:
            raise ValueError("source id, name, and owner are required")
        if not _is_http_url(self.base_url):
            raise ValueError("base_url must use http or https")
        if self.terms_url is not None and not _is_http_url(self.terms_url):
            raise ValueError("terms_url must use http or https")
        if self.allowed_data_categories & self.prohibited_data_categories:
            raise ValueError("data categories cannot be both allowed and prohibited")
        if self.status is SourceStatus.BLOCKED and self.allowed_data_categories:
            raise ValueError("blocked sources cannot declare allowed data categories")
        if self.rate_limit_per_minute is not None and self.rate_limit_per_minute < 1:
            raise ValueError("rate_limit_per_minute must be positive")
        if self.retention_days is not None and self.retention_days < 1:
            raise ValueError("retention_days must be positive")
        non_runnable = {
            SourceStatus.DRAFT,
            SourceStatus.PENDING_REVIEW,
            SourceStatus.QUARANTINED,
            SourceStatus.BLOCKED,
        }
        if self.source_type is not SourceType.MANUAL_IMPORT and self.status not in non_runnable:
            if self.terms_url is None and self.licence is None:
                raise ValueError("runnable automated sources require terms or a documented licence")

    def evaluate(
        self,
        request: CollectionRequest,
        authorization: SourceAuthorization,
        runtime: SourceRuntimeState,
        *,
        now: datetime,
    ) -> CollectionDecision:
        current_time = require_aware_utc(now, field_name="now")
        if self.status is SourceStatus.BLOCKED:
            return CollectionDecision(False, DecisionReason.SOURCE_BLOCKED)
        if self.status is not SourceStatus.ENABLED:
            return CollectionDecision(False, DecisionReason.SOURCE_NOT_ENABLED)
        if request.data_category in self.prohibited_data_categories:
            return CollectionDecision(False, DecisionReason.CATEGORY_PROHIBITED)
        if request.data_category not in self.allowed_data_categories:
            return CollectionDecision(False, DecisionReason.CATEGORY_NOT_ALLOWED)
        authorization_decision = _evaluate_authorization(authorization, current_time)
        if authorization_decision is not None:
            return authorization_decision
        if request.automated and not authorization.automated_collection_allowed:
            return CollectionDecision(False, DecisionReason.AUTOMATION_NOT_ALLOWED)
        if request.store_raw_content:
            if not self.raw_content_storage or not authorization.raw_storage_allowed:
                return CollectionDecision(False, DecisionReason.RAW_STORAGE_NOT_ALLOWED)
        if self.human_review_required and not request.human_review_completed:
            return CollectionDecision(
                False,
                DecisionReason.HUMAN_REVIEW_REQUIRED,
                requires_human_review=True,
            )
        if runtime.remaining_requests == 0:
            return CollectionDecision(False, DecisionReason.RATE_LIMIT_EXHAUSTED)
        if request.purpose not in authorization.approved_purposes:
            return CollectionDecision(False, DecisionReason.AUTHORIZATION_NOT_APPROVED)
        if not _url_is_authorized(
            request.target_url,
            authorization.approved_hosts,
            authorization.approved_path_prefixes,
        ):
            return _url_denial(request.target_url, authorization)
        return CollectionDecision(True, DecisionReason.ALLOWED)


def _evaluate_authorization(
    authorization: SourceAuthorization,
    now: datetime,
) -> CollectionDecision | None:
    if authorization.status is AuthorizationStatus.MISSING:
        return CollectionDecision(False, DecisionReason.AUTHORIZATION_MISSING)
    if authorization.status is AuthorizationStatus.EXPIRED:
        return CollectionDecision(False, DecisionReason.AUTHORIZATION_EXPIRED)
    if authorization.status is not AuthorizationStatus.APPROVED:
        return CollectionDecision(False, DecisionReason.AUTHORIZATION_NOT_APPROVED)
    if authorization.expires_at is not None and authorization.expires_at <= now:
        return CollectionDecision(False, DecisionReason.AUTHORIZATION_EXPIRED)
    return None


def _url_denial(
    target_url: str,
    authorization: SourceAuthorization,
) -> CollectionDecision:
    parsed = urlparse(target_url)
    if parsed.hostname not in authorization.approved_hosts:
        return CollectionDecision(False, DecisionReason.HOST_NOT_ALLOWED)
    return CollectionDecision(False, DecisionReason.PATH_NOT_ALLOWED)


def _url_is_authorized(
    target_url: str,
    approved_hosts: frozenset[str],
    approved_path_prefixes: tuple[str, ...],
) -> bool:
    parsed = urlparse(target_url)
    if parsed.scheme not in {"http", "https"} or parsed.hostname not in approved_hosts:
        return False
    return any(parsed.path.startswith(prefix) for prefix in approved_path_prefixes)


def _is_http_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.hostname)
