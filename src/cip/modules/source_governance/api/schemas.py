from __future__ import annotations

from datetime import datetime

from pydantic import AnyHttpUrl, BaseModel, Field

from cip.modules.source_governance.domain.models import (
    AuthorizationStatus,
    CollectionDecision,
    CollectionRequest,
    DataCategory,
    SourceAuthorization,
    SourcePolicy,
    SourceRuntimeState,
    SourceStatus,
    SourceType,
)


class SourcePolicyInput(BaseModel):
    id: str = Field(pattern=r"^[a-z0-9][a-z0-9_-]{2,63}$")
    name: str = Field(min_length=1, max_length=200)
    base_url: AnyHttpUrl
    status: SourceStatus
    source_type: SourceType
    owner: str = Field(min_length=1, max_length=200)
    terms_url: AnyHttpUrl | None = None
    licence: str | None = Field(default=None, max_length=200)
    allowed_data_categories: set[DataCategory] = Field(default_factory=set)
    prohibited_data_categories: set[DataCategory] = Field(default_factory=set)
    rate_limit_per_minute: int | None = Field(default=None, ge=1)
    retention_days: int | None = Field(default=None, ge=1)
    attribution_required: bool = False
    raw_content_storage: bool = False
    human_review_required: bool = True

    def to_domain(self) -> SourcePolicy:
        return SourcePolicy(
            id=self.id,
            name=self.name,
            base_url=str(self.base_url),
            status=self.status,
            source_type=self.source_type,
            owner=self.owner,
            terms_url=str(self.terms_url) if self.terms_url else None,
            licence=self.licence,
            allowed_data_categories=frozenset(self.allowed_data_categories),
            prohibited_data_categories=frozenset(self.prohibited_data_categories),
            rate_limit_per_minute=self.rate_limit_per_minute,
            retention_days=self.retention_days,
            attribution_required=self.attribution_required,
            raw_content_storage=self.raw_content_storage,
            human_review_required=self.human_review_required,
        )


class SourceAuthorizationInput(BaseModel):
    status: AuthorizationStatus
    document_reference: str | None = Field(default=None, max_length=500)
    reviewed_at: datetime | None = None
    expires_at: datetime | None = None
    approved_hosts: set[str] = Field(default_factory=set)
    approved_path_prefixes: list[str] = Field(default_factory=list)
    approved_purposes: set[str] = Field(default_factory=set)
    automated_collection_allowed: bool = False
    raw_storage_allowed: bool = False

    def to_domain(self) -> SourceAuthorization:
        return SourceAuthorization(
            status=self.status,
            document_reference=self.document_reference,
            reviewed_at=self.reviewed_at,
            expires_at=self.expires_at,
            approved_hosts=frozenset(self.approved_hosts),
            approved_path_prefixes=tuple(self.approved_path_prefixes),
            approved_purposes=frozenset(self.approved_purposes),
            automated_collection_allowed=self.automated_collection_allowed,
            raw_storage_allowed=self.raw_storage_allowed,
        )


class SourceRuntimeInput(BaseModel):
    remaining_requests: int | None = Field(default=None, ge=0)
    paused_reason: str | None = Field(default=None, max_length=1_000)
    last_success_at: datetime | None = None

    def to_domain(self) -> SourceRuntimeState:
        return SourceRuntimeState(
            remaining_requests=self.remaining_requests,
            paused_reason=self.paused_reason,
            last_success_at=self.last_success_at,
        )


class CollectionRequestInput(BaseModel):
    data_category: DataCategory
    target_url: AnyHttpUrl
    purpose: str = Field(min_length=1, max_length=200)
    automated: bool = True
    store_raw_content: bool = False
    human_review_completed: bool = False

    def to_domain(self) -> CollectionRequest:
        return CollectionRequest(
            data_category=self.data_category,
            target_url=str(self.target_url),
            purpose=self.purpose,
            automated=self.automated,
            store_raw_content=self.store_raw_content,
            human_review_completed=self.human_review_completed,
        )


class SourceEvaluationInput(BaseModel):
    policy: SourcePolicyInput
    authorization: SourceAuthorizationInput
    runtime: SourceRuntimeInput = Field(default_factory=SourceRuntimeInput)
    request: CollectionRequestInput
    now: datetime


class CollectionDecisionOutput(BaseModel):
    allowed: bool
    reason: str
    requires_human_review: bool

    @classmethod
    def from_domain(cls, decision: CollectionDecision) -> CollectionDecisionOutput:
        return cls(
            allowed=decision.allowed,
            reason=decision.reason.value,
            requires_human_review=decision.requires_human_review,
        )
